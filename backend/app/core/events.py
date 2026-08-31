"""In-process async event bus.

Designed so Redis Streams could replace the transport later without changing
the plugin API (`subscriptions` + `handle_event`).
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

logger = logging.getLogger("otho.events")

EventHandler = Callable[["Event"], Awaitable[None]]

LEAGUE_SYNCED = "league.synced"
ROSTER_UPDATED = "roster.updated"
MATCHUP_UPDATED = "matchup.updated"
TRANSACTION_CREATED = "transaction.created"
PLAYER_NEWS = "player.news"
PLAYER_INJURY = "player.injury"
PROJECTION_UPDATED = "projection.updated"
GAME_STARTED = "game.started"
GAME_COMPLETED = "game.completed"
WEEK_CHANGED = "week.changed"

ALL_EVENT_TYPES = (
    LEAGUE_SYNCED,
    ROSTER_UPDATED,
    MATCHUP_UPDATED,
    TRANSACTION_CREATED,
    PLAYER_NEWS,
    PLAYER_INJURY,
    PROJECTION_UPDATED,
    GAME_STARTED,
    GAME_COMPLETED,
    WEEK_CHANGED,
)


@dataclass(frozen=True)
class Event:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    league_id: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventBus(Protocol):
    async def publish(self, event: Event) -> None: ...
    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None: ...


class InProcessEventBus:
    """Fan-out to in-process subscribers. Optionally mirrors to Redis pub/sub."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] | None = None
        self._recent: list[Event] = []
        self._max_recent = 200

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: Event) -> None:
        self._recent.append(event)
        if len(self._recent) > self._max_recent:
            self._recent = self._recent[-self._max_recent :]
        handlers = list(self._handlers.get(event.type, []))
        handlers.extend(self._handlers.get("*", []))
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception("event handler failed type=%s", event.type)

    def recent(self, league_id: str | None = None, limit: int = 50) -> list[Event]:
        items = self._recent
        if league_id:
            items = [e for e in items if e.league_id == league_id]
        return items[-limit:]


_bus: InProcessEventBus | None = None


def get_event_bus() -> InProcessEventBus:
    global _bus
    if _bus is None:
        _bus = InProcessEventBus()
    return _bus


def reset_event_bus() -> None:
    global _bus
    _bus = None
