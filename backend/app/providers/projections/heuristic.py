"""Naive projections from player metadata. Enough for plugins to run without an external API."""

from __future__ import annotations

from app.domain import Player, Projection

BASE_POINTS = {
    "QB": 18.4,
    "RB": 12.2,
    "WR": 11.1,
    "TE": 7.8,
    "K": 8.1,
    "DEF": 7.6,
    "DL": 6.5,
    "LB": 8.0,
    "DB": 6.8,
}

RANK_MULT = (
    (30, 1.35),
    (80, 1.18),
    (150, 1.05),
    (250, 0.88),
    (400, 0.70),
    (800, 0.50),
)

INJURY_MULT = {
    "out": 0.0,
    "ir": 0.0,
    "pup": 0.0,
    "suspended": 0.0,
    "doubtful": 0.25,
    "questionable": 0.78,
    "cov": 0.4,
}


class HeuristicProjectionProvider:
    name = "otho.heuristic"

    async def projections(self, players: list[Player], week: int, season: str) -> dict[str, Projection]:
        return {p.player_id: self.project_one(p, week, season) for p in players}

    def project_one(self, player: Player, week: int, season: str) -> Projection:
        base = BASE_POINTS.get((player.position or "").upper(), 4.5)
        rank = player.search_rank if player.search_rank is not None else 9999
        mult = 0.32
        for ceiling, factor in RANK_MULT:
            if rank <= ceiling:
                mult = factor
                break
        if player.years_exp == 0 and rank > 80:
            mult *= 0.88
        if player.depth_chart_order and player.depth_chart_order > 1:
            mult *= 0.72 if player.depth_chart_order == 2 else 0.45
        if not player.team:
            mult *= 0.2
        inj = INJURY_MULT.get((player.injury_status or "").lower(), 1.0)
        points = round(max(0.0, base * mult * inj), 2)
        floor = round(points * 0.55, 2)
        ceiling = round(points * 1.55, 2)
        return Projection(
            player_id=player.player_id,
            week=week,
            season=season,
            points=points,
            floor=floor,
            ceiling=ceiling,
            source=self.name,
            position=player.position,
        )
