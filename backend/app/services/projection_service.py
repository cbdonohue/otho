from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import ProjectionRow
from app.domain import Player, Projection
from app.providers.projections.heuristic import HeuristicProjectionProvider


class ProjectionService:
    def __init__(
        self,
        session: AsyncSession,
        player_lookup,
        provider: HeuristicProjectionProvider | None = None,
    ) -> None:
        self.session = session
        self._player_lookup = player_lookup
        self.provider = provider or HeuristicProjectionProvider()

    async def get_projection(self, player_id: str, week: int, season: str) -> Projection | None:
        found = await self.get_projections([player_id], week, season)
        return found.get(player_id)

    async def get_projections(self, player_ids: list[str], week: int, season: str) -> dict[str, Projection]:
        if not player_ids:
            return {}
        unique_ids = list(dict.fromkeys(player_ids))
        rows = (
            (
                await self.session.execute(
                    select(ProjectionRow).where(
                        ProjectionRow.week == week,
                        ProjectionRow.season == season,
                        ProjectionRow.player_id.in_(unique_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        result = {
            r.player_id: Projection(
                player_id=r.player_id,
                week=r.week,
                season=r.season,
                points=r.points,
                floor=r.floor,
                ceiling=r.ceiling,
                source=r.source,
                position=r.position,
            )
            for r in rows
        }
        missing = [pid for pid in unique_ids if pid not in result]
        if not missing:
            return result
        players = await self._load_players(missing)
        generated = await self.provider.projections(players, week, season)
        result.update(generated)
        if generated:
            values = [
                {
                    "player_id": p.player_id,
                    "week": p.week,
                    "season": p.season,
                    "points": p.points,
                    "floor": p.floor,
                    "ceiling": p.ceiling,
                    "source": p.source,
                    "position": p.position,
                }
                for p in generated.values()
            ]
            from app.core.database import get_engine

            dialect = get_engine().dialect.name
            inserter = sqlite_insert if dialect == "sqlite" else pg_insert
            stmt = inserter(ProjectionRow).values(values).on_conflict_do_nothing(
                index_elements=["player_id", "week", "season"]
            )
            try:
                await self.session.execute(stmt)
                await self.session.flush()
            except Exception:
                # Heuristic projections still return even if persist races.
                pass
        return result

    async def _load_players(self, player_ids: list[str]) -> list[Player]:
        if hasattr(self._player_lookup, "get_players"):
            mapping = await self._player_lookup.get_players(player_ids)
            return list(mapping.values())
        return []
