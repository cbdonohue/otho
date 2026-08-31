from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PlayerRow, RosterRow
from app.domain import Player, TrendingPlayer


class PlayerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._trending: list[TrendingPlayer] = []

    def set_trending(self, trending: list[TrendingPlayer]) -> None:
        self._trending = trending

    async def upsert_players(self, players: dict[str, Player]) -> None:
        # Full catalog replace — players are refreshed on the 24h poll.
        await self.session.execute(delete(PlayerRow))
        batch: list[PlayerRow] = []
        for player in players.values():
            batch.append(PlayerRow(**player.model_dump()))
            if len(batch) >= 500:
                self.session.add_all(batch)
                await self.session.flush()
                batch = []
        if batch:
            self.session.add_all(batch)
            await self.session.flush()

    async def get_player(self, player_id: str) -> Player | None:
        row = await self.session.get(PlayerRow, player_id)
        return self._to_domain(row) if row else None

    async def get_players(self, player_ids: list[str]) -> dict[str, Player]:
        if not player_ids:
            return {}
        rows = (
            (await self.session.execute(select(PlayerRow).where(PlayerRow.player_id.in_(player_ids))))
            .scalars()
            .all()
        )
        return {r.player_id: self._to_domain(r) for r in rows}

    async def search(self, query: str, limit: int = 20) -> list[Player]:
        q = f"%{query.lower()}%"
        rows = (
            (
                await self.session.execute(
                    select(PlayerRow)
                    .where(
                        or_(
                            PlayerRow.full_name.ilike(q),
                            PlayerRow.last_name.ilike(q),
                            PlayerRow.first_name.ilike(q),
                        )
                    )
                    .order_by(PlayerRow.search_rank.asc().nullslast())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]

    async def available(self, league_id: str, positions: list[str] | None = None) -> list[Player]:
        roster_rows = (
            (await self.session.execute(select(RosterRow).where(RosterRow.league_id == league_id)))
            .scalars()
            .all()
        )
        taken: set[str] = set()
        for row in roster_rows:
            taken.update(row.players or [])
        stmt = select(PlayerRow).where(PlayerRow.team.is_not(None))
        if positions:
            stmt = stmt.where(PlayerRow.position.in_(positions))
        stmt = stmt.order_by(PlayerRow.search_rank.asc().nullslast()).limit(400)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows if r.player_id not in taken]

    async def trending(self, kind: str = "add") -> list[TrendingPlayer]:
        return [t for t in self._trending if t.kind == kind] or self._trending

    @staticmethod
    def _to_domain(row: PlayerRow) -> Player:
        return Player(
            player_id=row.player_id,
            full_name=row.full_name,
            first_name=row.first_name,
            last_name=row.last_name,
            position=row.position,
            team=row.team,
            status=row.status,
            injury_status=row.injury_status,
            number=row.number,
            age=row.age,
            years_exp=row.years_exp,
            depth_chart_order=row.depth_chart_order,
            search_rank=row.search_rank,
            sport=row.sport,
        )
