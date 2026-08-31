from __future__ import annotations

from app.domain import Player, Projection
from app.plugins.builtin import grade_from_score, proj_of


def positional_grades(
    players: dict[str, Player],
    roster_player_ids: list[str],
    projections: dict[str, Projection],
) -> list[dict]:
    buckets: dict[str, list[tuple[Player, float]]] = {}
    for pid in roster_player_ids:
        player = players.get(pid)
        if not player or not player.position:
            continue
        buckets.setdefault(player.position.upper(), []).append((player, proj_of(projections, pid)))
    grades = []
    for pos, items in sorted(buckets.items()):
        items.sort(key=lambda x: x[1], reverse=True)
        starter = items[0][1] if items else 0.0
        depth = items[1][1] if len(items) > 1 else 0.0
        score = starter + 0.45 * depth
        injured = [p.display_name for p, _ in items if p.injury_status]
        notes = f"Injured: {', '.join(injured)}" if injured else "Healthy depth" if depth > 6 else "Thin behind starter"
        grades.append(
            {
                "position": pos,
                "grade": grade_from_score(score if pos in {"RB", "WR"} else starter),
                "score": round(score, 2),
                "starter_projection": round(starter, 2),
                "depth_projection": round(depth, 2),
                "count": len(items),
                "notes": notes,
            }
        )
    return grades
