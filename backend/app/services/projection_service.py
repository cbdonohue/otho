from __future__ import annotations

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
        result: dict[str, Projection] = {}
        missing: list[str] = []
        for pid in player_ids:
            row = await self.session.get(
                ProjectionRow, {"player_id": pid, "week": week, "season": season}
            )
            if row:
                result[pid] = Projection(
                    player_id=row.player_id,
                    week=row.week,
                    season=row.season,
                    points=row.points,
                    floor=row.floor,
                    ceiling=row.ceiling,
                    source=row.source,
                    position=row.position,
                )
            else:
                missing.append(pid)
        if missing:
            players = await self._load_players(missing)
            generated = await self.provider.projections(players, week, season)
            for pid, proj in generated.items():
                result[pid] = proj
                self.session.add(
                    ProjectionRow(
                        player_id=proj.player_id,
                        week=proj.week,
                        season=proj.season,
                        points=proj.points,
                        floor=proj.floor,
                        ceiling=proj.ceiling,
                        source=proj.source,
                        position=proj.position,
                    )
                )
            await self.session.flush()
        return result

    async def _load_players(self, player_ids: list[str]) -> list[Player]:
        if hasattr(self._player_lookup, "get_players"):
            mapping = await self._player_lookup.get_players(player_ids)
            return list(mapping.values())
        return []
