"""Cache layer. Redis when configured, otherwise a process-local dict.

The plugin API only sees `Cache` methods — swapping Redis in later does not
change plugins.
"""

from __future__ import annotations

import json
import time
from typing import Any, Protocol

from app.core.config import get_settings


class Cache(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def acquire_lock(self, key: str, ttl: int = 30) -> bool: ...
    async def release_lock(self, key: str) -> None: ...


class InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._locks: dict[str, float] = {}

    def _expired(self, expires_at: float | None) -> bool:
        return expires_at is not None and expires_at < time.time()

    async def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if self._expired(expires_at):
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires = time.time() + ttl if ttl else None
        self._store[key] = (value, expires)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def acquire_lock(self, key: str, ttl: int = 30) -> bool:
        now = time.time()
        expires = self._locks.get(key)
        if expires and expires > now:
            return False
        self._locks[key] = now + ttl
        return True

    async def release_lock(self, key: str) -> None:
        self._locks.pop(key, None)


class RedisCache:
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._client = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        payload = json.dumps(value)
        if ttl:
            await self._client.set(key, payload, ex=ttl)
        else:
            await self._client.set(key, payload)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def acquire_lock(self, key: str, ttl: int = 30) -> bool:
        return bool(await self._client.set(f"lock:{key}", "1", nx=True, ex=ttl))

    async def release_lock(self, key: str) -> None:
        await self._client.delete(f"lock:{key}")


_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        settings = get_settings()
        if settings.has_redis:
            _cache = RedisCache(settings.redis_url)
        else:
            _cache = InMemoryCache()
    return _cache


def reset_cache() -> None:
    global _cache
    _cache = None
