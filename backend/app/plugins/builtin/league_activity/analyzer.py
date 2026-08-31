from __future__ import annotations

from app.domain import Transaction


def pulse(transactions: list[Transaction]) -> dict:
    counts = {"waiver": 0, "free_agent": 0, "trade": 0, "other": 0}
    for tx in transactions:
        key = tx.type if tx.type in counts else "other"
        counts[key] += 1
    heat = "quiet"
    total = len(transactions)
    if total >= 12:
        heat = "frantic"
    elif total >= 6:
        heat = "active"
    elif total >= 2:
        heat = "steady"
    return {"counts": counts, "heat": heat, "total": total}
