"""Sleeper as a FantasyDataProvider. Mapping happens only via mapper.py."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.domain import League, LeagueUser, Matchup, Player, Roster, Transaction
from app.providers.sleeper.client import SleeperClient
from app.providers.sleeper import mapper


class SleeperProvider:
    name = "sleeper"

    def __init__(self, client: SleeperClient | None = None) -> None:
        settings = get_settings()
        self.client = client or SleeperClient(base_url=settings.sleeper_base_url)

    async def get_nfl_state(self) -> dict[str, Any]:
        return await self.client.nfl_state()

    async def get_players(self) -> dict[str, Player]:
        raw = await self.client.players_nfl()
        return mapper.map_players(raw)

    async def get_league(self, league_id: str) -> League:
        raw = await self.client.league(league_id)
        league = mapper.map_league(raw)
        state = await self.get_nfl_state()
        league.week = int(state.get("display_week") or state.get("week") or 1)
        return league

    async def get_users(self, league_id: str) -> list[LeagueUser]:
        raw = await self.client.league_users(league_id)
        return [mapper.map_user(u, league_id) for u in raw]

    async def get_rosters(self, league_id: str) -> list[Roster]:
        users = {u.user_id: u.display_name for u in await self.get_users(league_id)}
        raw = await self.client.league_rosters(league_id)
        rosters = []
        for row in raw:
            owner_id = str(row["owner_id"]) if row.get("owner_id") else None
            name = users.get(owner_id or "")
            rosters.append(mapper.map_roster(row, league_id, owner_name=name))
        return rosters

    async def get_matchups(self, league_id: str, week: int) -> list[Matchup]:
        raw = await self.client.league_matchups(league_id, week)
        names: dict[int, str] = {}
        try:
            for roster in await self.get_rosters(league_id):
                names[roster.roster_id] = roster.owner_name or roster.team_name or str(roster.roster_id)
        except Exception:
            names = {}
        return mapper.map_matchup_sides(raw, league_id, week, roster_names=names)

    async def get_transactions(self, league_id: str, week: int) -> list[Transaction]:
        raw = await self.client.league_transactions(league_id, week)
        return [mapper.map_transaction(row, league_id) for row in raw or []]

    async def get_trending(self, kind: str = "add") -> list[dict[str, Any]]:
        return await self.client.trending(kind=kind)
