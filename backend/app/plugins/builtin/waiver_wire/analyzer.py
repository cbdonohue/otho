from __future__ import annotations

from app.domain import Player, Projection, Roster
from app.plugins.builtin import grade_from_score, proj_of


def positional_need(roster: Roster, players: dict[str, Player], projections: dict[str, Projection]) -> dict[str, float]:
    totals: dict[str, list[float]] = {"QB": [], "RB": [], "WR": [], "TE": [], "K": [], "DEF": []}
    for pid in roster.players:
        player = players.get(pid)
        if not player or not player.position:
            continue
        pos = player.position.upper()
        if pos not in totals:
            continue
        totals[pos].append(proj_of(projections, pid))
    need: dict[str, float] = {}
    typical = {"QB": 16.0, "RB": 22.0, "WR": 24.0, "TE": 8.0, "K": 8.0, "DEF": 8.0}
    for pos, values in totals.items():
        values.sort(reverse=True)
        top = sum(values[:2]) if pos in {"RB", "WR"} else (values[0] if values else 0.0)
        if not values:
            need[pos] = 1.85
        elif top >= typical[pos]:
            # Already strong — don't flood waivers with the same position.
            need[pos] = 0.35 if pos == "QB" else 0.65
        else:
            need[pos] = round(1.0 + gap / max(typical[pos], 1), 2)
    return need


def score_waiver(player: Player, proj: float, need: dict[str, float], trending_count: int = 0) -> float:
    pos_need = need.get((player.position or "").upper(), 1.0)
    trend = 1.0 + min(0.25, trending_count / 400)
    injury = 0.3 if player.injury_status else 1.0
    return round(proj * pos_need * trend * injury, 3)
