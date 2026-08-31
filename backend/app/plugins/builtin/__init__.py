from __future__ import annotations

from app.domain import Player, Projection

FLEX_ELIGIBLE = {"RB", "WR", "TE"}
SUPERFLEX_ELIGIBLE = {"QB", "RB", "WR", "TE"}
IDP = {"DL", "LB", "DB", "IDP"}


def slot_eligible(slot: str, position: str | None) -> bool:
    pos = (position or "").upper()
    slot = slot.upper()
    if slot in {"BN", "IR", "TAXI"}:
        return False
    if slot == pos:
        return True
    if slot in {"FLEX", "WRRB_FLEX", "REC_FLEX"} and pos in FLEX_ELIGIBLE:
        return True
    if slot == "SUPER_FLEX" and pos in SUPERFLEX_ELIGIBLE:
        return True
    if slot == "IDP_FLEX" and pos in IDP:
        return True
    return False


def starter_slots(roster_positions: list[str]) -> list[str]:
    return [p for p in roster_positions if p not in {"BN", "IR", "TAXI"}]


def optimal_lineup(
    slots: list[str],
    players: list[Player],
    projections: dict[str, Projection],
) -> list[tuple[str, Player, float]]:
    """Greedy: for each slot, pick highest remaining eligible projection."""
    remaining = list(players)
    filled: list[tuple[str, Player, float]] = []
    for slot in slots:
        best_i = -1
        best_pts = -1.0
        for i, player in enumerate(remaining):
            if not slot_eligible(slot, player.position):
                continue
            pts = projections.get(player.player_id)
            value = pts.points if pts else 0.0
            if player.is_out:
                value = 0.0
            if value > best_pts:
                best_pts = value
                best_i = i
        if best_i >= 0:
            player = remaining.pop(best_i)
            filled.append((slot, player, best_pts))
        else:
            filled.append((slot, Player(player_id="empty", full_name="Empty"), 0.0))
    return filled


def grade_from_score(score: float) -> str:
    if score >= 18:
        return "A+"
    if score >= 15:
        return "A"
    if score >= 13:
        return "B+"
    if score >= 11:
        return "B"
    if score >= 9:
        return "C+"
    if score >= 7:
        return "C"
    if score >= 5:
        return "D"
    return "F"


def proj_of(projections: dict[str, Projection], player_id: str) -> float:
    p = projections.get(player_id)
    return p.points if p else 0.0
