from __future__ import annotations

from app.domain import Player, Projection
from app.plugins.builtin import optimal_lineup, proj_of, starter_slots


def start_sit_swaps(
    current_starters: list[str],
    optimal: list[tuple[str, Player, float]],
    projections: dict[str, Projection],
    players: dict[str, Player],
) -> list[dict]:
    current_set = [pid for pid in current_starters if pid and pid != "0"]
    optimal_ids = [p.player_id for _, p, _ in optimal if p.player_id != "empty"]
    sit = [pid for pid in current_set if pid not in optimal_ids]
    start = [pid for pid in optimal_ids if pid not in current_set]
    swaps = []
    used = set()
    for out_id in sit:
        out_player = players.get(out_id)
        out_pts = proj_of(projections, out_id)
        best = None
        for in_id in start:
            if in_id in used:
                continue
            in_player = players.get(in_id)
            in_pts = proj_of(projections, in_id)
            if not in_player or not out_player:
                continue
            delta = in_pts - out_pts
            if best is None or delta > best["delta"]:
                best = {
                    "sit_id": out_id,
                    "sit_name": out_player.display_name,
                    "sit_pos": out_player.position,
                    "sit_proj": out_pts,
                    "start_id": in_id,
                    "start_name": in_player.display_name,
                    "start_pos": in_player.position,
                    "start_proj": in_pts,
                    "delta": round(delta, 2),
                }
        if best and best["delta"] > 0.4:
            used.add(best["start_id"])
            swaps.append(best)
    return swaps
