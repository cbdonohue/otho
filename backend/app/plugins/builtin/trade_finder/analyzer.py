from __future__ import annotations

from app.domain import Player, Projection, Roster
from app.plugins.builtin import proj_of
from app.plugins.builtin.roster_health.analyzer import positional_grades


def surplus_positions(grades: list[dict], threshold: str = "B+") -> list[str]:
    return [g["position"] for g in grades if g["grade"] in {"A+", "A", "B+"} and g["count"] >= 3]


def value_of(player_ids: list[str], projections: dict[str, Projection]) -> float:
    return round(sum(proj_of(projections, pid) for pid in player_ids), 2)


def fairness(give: float, receive: float) -> str:
    if receive - give >= 2.5:
        return "you win"
    if give - receive >= 2.5:
        return "you lose"
    return "even"
