from __future__ import annotations

from app.domain import Player, Roster
from app.plugins.builtin import proj_of
from app.plugins.builtin.roster_health.analyzer import positional_grades


def likely_needs(grades: list[dict]) -> list[str]:
    return [g["position"] for g in grades if g["grade"] in {"C", "C+", "D", "F"}]
