"""Thin httpx wrapper around the public Sleeper API. No domain mapping here."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("otho.sleeper")

DEFAULT_BASE = "https://api.sleeper.app/v1"
# Stay well under Sleeper's ~1000 calls/minute guidance.
MIN_INTERVAL_S = 0.08


class SleeperClient:
    def __init__(self, base_url: str = DEFAULT_BASE, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str) -> Any:
        async with self._lock:
            wait = MIN_INTERVAL_S - (time.monotonic() - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
        url = path if path.startswith("/") else f"/{path}"
        logger.debug("GET %s%s", self.base_url, url)
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()

    async def nfl_state(self) -> dict[str, Any]:
        return await self._get("/state/nfl")

    async def players_nfl(self) -> dict[str, Any]:
        return await self._get("/players/nfl")

    async def league(self, league_id: str) -> dict[str, Any]:
        return await self._get(f"/league/{league_id}")

    async def league_rosters(self, league_id: str) -> list[dict[str, Any]]:
        return await self._get(f"/league/{league_id}/rosters")

    async def league_users(self, league_id: str) -> list[dict[str, Any]]:
        return await self._get(f"/league/{league_id}/users")

    async def league_matchups(self, league_id: str, week: int) -> list[dict[str, Any]]:
        return await self._get(f"/league/{league_id}/matchups/{week}")

    async def league_transactions(self, league_id: str, week: int) -> list[dict[str, Any]]:
        return await self._get(f"/league/{league_id}/transactions/{week}")

    async def traded_picks(self, league_id: str) -> list[dict[str, Any]]:
        return await self._get(f"/league/{league_id}/traded_picks")

    async def trending(self, kind: str = "add", sport: str = "nfl", lookback_hours: int = 24, limit: int = 25) -> list[dict[str, Any]]:
        return await self._get(
            f"/players/{sport}/trending/{kind}?lookback_hours={lookback_hours}&limit={limit}"
        )

    async def user(self, user_id: str) -> dict[str, Any]:
        return await self._get(f"/user/{user_id}")
