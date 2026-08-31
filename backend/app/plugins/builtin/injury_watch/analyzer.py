from __future__ import annotations

HIGH = {"out", "ir", "pup", "suspended"}
MED = {"doubtful", "questionable"}


def severity_for(status: str | None) -> str:
    s = (status or "").lower()
    if s in HIGH:
        return "high"
    if s in MED:
        return "medium"
    return "low"
