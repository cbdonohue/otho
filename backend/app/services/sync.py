"""Pull league state through the provider and persist normalized objects."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache
from app.core.events import (
    LEAGUE_SYNCED,
    MATCHUP_UPDATED,
    PLAYER_INJURY,
    ROSTER_UPDATED,
    TRANSACTION_CREATED,
    Event,
    EventBus,
)
from app.core.models import SnapshotRow
from app.domain import Player, Roster, TrendingPlayer
from app.providers.sleeper.provider import SleeperProvider
from app.services.league_service import LeagueService
from app.services.news_service import NewsService
from app.services.player_service import PlayerService

logger = logging.getLogger("otho.sync")


class SyncService:
    def __init__(
        self,
        session: AsyncSession,
        cache: Cache,
        events: EventBus,
        provider: SleeperProvider | None = None,
        news: NewsService | None = None,
    ) -> None:
        self.session = session
        self.cache = cache
        self.events = events
        self.provider = provider or SleeperProvider()
        self.leagues = LeagueService(session)
        self.players = PlayerService(session)
        self.news = news or NewsService()

    async def sync_players(self, force: bool = False) -> int:
        cached = await self.cache.get("players:nfl:synced")
        if cached and not force:
            return 0
        lock = await self.cache.acquire_lock("sync:players", ttl=120)
        if not lock:
            return 0
        try:
            mapping = await self.provider.get_players()
            await self.players.upsert_players(mapping)
            await self.session.commit()
            await self.cache.set("players:nfl:synced", True, ttl=24 * 3600)
            logger.info("synced %s nfl players", len(mapping))
            injured = [p for p in mapping.values() if p.injury_status]
            self.news.seed(injured)
            for player in injured[:50]:
                await self.events.publish(
                    Event(
                        type=PLAYER_INJURY,
                        payload={
                            "player_id": player.player_id,
                            "status": player.injury_status,
                            "name": player.display_name,
                        },
                    )
                )
            return len(mapping)
        finally:
            await self.cache.release_lock("sync:players")

    async def sync_league(self, league_id: str) -> None:
        league = await self.provider.get_league(league_id)
        users = await self.provider.get_users(league_id)
        rosters = await self.provider.get_rosters(league_id)
        owner_to_roster = {r.owner_id: r.roster_id for r in rosters if r.owner_id}
        for user in users:
            user.roster_id = owner_to_roster.get(user.user_id)
        await self.leagues.upsert_league(league)
        await self.leagues.replace_users(league_id, users)
        previous = {r.roster_id: r for r in await self._existing_rosters(league_id)}
        await self.leagues.upsert_rosters(league_id, rosters)
        self.session.add(
            SnapshotRow(
                league_id=league_id,
                kind="roster",
                week=league.week,
                payload={"rosters": [r.model_dump() for r in rosters], "at": datetime.now(UTC).isoformat()},
            )
        )
        await self.session.commit()
        await self.events.publish(
            Event(type=LEAGUE_SYNCED, league_id=league_id, payload={"name": league.name, "week": league.week})
        )
        for roster in rosters:
            old = previous.get(roster.roster_id)
            if old and old.players != roster.players:
                await self.events.publish(
                    Event(
                        type=ROSTER_UPDATED,
                        league_id=league_id,
                        payload={"roster_id": roster.roster_id, "players": roster.players},
                    )
                )

    async def sync_matchups(self, league_id: str, week: int) -> None:
        matchups = await self.provider.get_matchups(league_id, week)
        await self.leagues.replace_matchups(league_id, week, matchups)
        await self.session.commit()
        await self.events.publish(
            Event(
                type=MATCHUP_UPDATED,
                league_id=league_id,
                payload={"week": week, "count": len(matchups)},
            )
        )

    async def sync_transactions(self, league_id: str, week: int) -> None:
        txs = await self.provider.get_transactions(league_id, week)
        created = await self.leagues.upsert_transactions(txs)
        await self.session.commit()
        for tx in created:
            await self.events.publish(
                Event(
                    type=TRANSACTION_CREATED,
                    league_id=league_id,
                    payload=tx.model_dump(mode="json"),
                )
            )

    async def sync_trending(self) -> None:
        adds = await self.provider.get_trending("add")
        drops = await self.provider.get_trending("drop")
        trending = [
            TrendingPlayer(player_id=str(row.get("player_id")), count=int(row.get("count") or 0), kind="add")
            for row in adds
        ] + [
            TrendingPlayer(player_id=str(row.get("player_id")), count=int(row.get("count") or 0), kind="drop")
            for row in drops
        ]
        self.players.set_trending(trending)
        await self.cache.set("trending", [t.model_dump() for t in trending], ttl=600)

    async def full_sync(self, league_id: str) -> None:
        await self.sync_players()
        await self.sync_league(league_id)
        league = await self.leagues.get_league(league_id)
        week = league.week or 1
        await self.sync_matchups(league_id, week)
        for w in range(max(1, week - 2), week + 1):
            await self.sync_transactions(league_id, w)
        try:
            await self.sync_trending()
        except Exception:
            logger.warning("trending sync failed", exc_info=True)

    async def _existing_rosters(self, league_id: str) -> list[Roster]:
        try:
            return await self.leagues.get_rosters(league_id)
        except Exception:
            return []
