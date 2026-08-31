"""Adaptive polling scheduler. Intervals tighten on game day / live games."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.database import get_session_factory
from app.services.sync import SyncService

logger = logging.getLogger("otho.scheduler")

GAMEDAY_WEEKDAYS = {0, 3, 6}  # Mon, Thu, Sun


class Scheduler:
    def __init__(self, app, settings: Settings) -> None:
        self.app = app
        self.settings = settings
        self._tasks: list[asyncio.Task] = []
        self._stop = asyncio.Event()

    def start(self) -> None:
        if not self.settings.enable_scheduler:
            return
        self._tasks.append(asyncio.create_task(self._loop("players", self.settings.poll_players_s, self._players)))
        self._tasks.append(asyncio.create_task(self._loop("leagues", self.settings.poll_league_settings_s, self._leagues)))
        self._tasks.append(asyncio.create_task(self._loop("rosters", self.settings.poll_rosters_s, self._rosters)))
        self._tasks.append(asyncio.create_task(self._loop("transactions", self.settings.poll_transactions_s, self._transactions)))
        self._tasks.append(asyncio.create_task(self._matchup_loop()))
        self._tasks.append(asyncio.create_task(self._loop("trending", self.settings.poll_trending_s, self._trending)))

    async def stop(self) -> None:
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _loop(self, name: str, interval: int, fn) -> None:
        await asyncio.sleep(2)
        while not self._stop.is_set():
            try:
                await fn()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("scheduler job %s failed", name)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except TimeoutError:
                continue

    async def _matchup_loop(self) -> None:
        await asyncio.sleep(3)
        while not self._stop.is_set():
            try:
                interval = await self._matchups()
            except Exception:
                logger.exception("matchup poll failed")
                interval = self.settings.poll_matchups_off_s
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except TimeoutError:
                continue

    def _sync(self, session) -> SyncService:
        return SyncService(session, self.app.state.cache, self.app.state.events, news=self.app.state.news)

    async def _league_ids(self, session) -> list[str]:
        from sqlalchemy import select

        from app.core.models import LeagueRow

        rows = (await session.execute(select(LeagueRow.league_id))).scalars().all()
        return list(rows)

    async def _players(self) -> None:
        async with get_session_factory()() as session:
            await self._sync(session).sync_players()

    async def _leagues(self) -> None:
        async with get_session_factory()() as session:
            sync = self._sync(session)
            for lid in await self._league_ids(session):
                await sync.sync_league(lid)

    async def _rosters(self) -> None:
        await self._leagues()

    async def _transactions(self) -> None:
        async with get_session_factory()() as session:
            sync = self._sync(session)
            from app.services.league_service import LeagueService

            leagues = LeagueService(session)
            for lid in await self._league_ids(session):
                try:
                    league = await leagues.get_league(lid)
                    week = league.week or 1
                    await sync.sync_transactions(lid, week)
                except Exception:
                    logger.exception("tx sync %s", lid)

    async def _matchups(self) -> int:
        live = False
        gameday = datetime.now(UTC).weekday() in GAMEDAY_WEEKDAYS
        async with get_session_factory()() as session:
            sync = self._sync(session)
            from app.services.league_service import LeagueService

            leagues = LeagueService(session)
            for lid in await self._league_ids(session):
                league = await leagues.get_league(lid)
                week = league.week or 1
                await sync.sync_matchups(lid, week)
                matchups = await leagues.get_matchups(lid, week)
                if any((m.home.points or 0) > 0 for m in matchups):
                    live = True
        if live:
            return self.settings.poll_matchups_live_s
        if gameday:
            return self.settings.poll_matchups_gameday_s
        return self.settings.poll_matchups_off_s

    async def _trending(self) -> None:
        async with get_session_factory()() as session:
            await self._sync(session).sync_trending()
