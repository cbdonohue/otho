"""Otho API gateway — FastAPI entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ask, dashboard, health, leagues, players, plugins, websocket
from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.database import init_db
from app.core.events import get_event_bus
from app.core.scheduler import Scheduler
from app.plugins.manager import PluginManager
from app.providers.news.stub import StubNewsProvider
from app.services.ask import AskOtho
from app.services.news_service import NewsService

logger = logging.getLogger("otho")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    await init_db()
    cache = get_cache()
    events = get_event_bus()
    news = NewsService(StubNewsProvider())
    manager = PluginManager(events)
    manager.load_builtins()
    manager.load_entry_points()
    await manager.startup()
    events.subscribe("*", websocket.hub.broadcast)
    app.state.settings = settings
    app.state.cache = cache
    app.state.events = events
    app.state.plugins = manager
    app.state.news = news
    app.state.ask = AskOtho(manager, settings)
    app.state.nfl_state = {"week": 1, "season": "2025", "season_type": "regular"}
    try:
        from app.providers.sleeper.provider import SleeperProvider

        app.state.nfl_state = await SleeperProvider().get_nfl_state()
    except Exception:
        logger.warning("could not fetch NFL state on boot; using defaults")
    scheduler = Scheduler(app, settings)
    app.state.scheduler = scheduler
    if settings.default_league_id:
        from app.core.database import get_session_factory
        from app.services.sync import SyncService

        async with get_session_factory()() as session:
            try:
                await SyncService(session, cache, events, news=news).full_sync(settings.default_league_id)
            except Exception:
                logger.exception("default league sync failed")
    scheduler.start()
    yield
    await scheduler.stop()
    await manager.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Otho", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(leagues.router)
    app.include_router(plugins.router)
    app.include_router(dashboard.router)
    app.include_router(ask.router)
    app.include_router(players.router)
    app.include_router(websocket.router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
