from __future__ import annotations

from typing import Any


class StubStatsProvider:
    name = "stub"

    async def weekly_stats(self, player_id: str, week: int, season: str) -> dict[str, Any]:
        return {"player_id": player_id, "week": week, "season": season, "stats": {}}
