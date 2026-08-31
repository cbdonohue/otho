from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache
from app.core.config import Settings, get_settings
from app.core.database import get_session_factory
from app.core.events import EventBus
from app.services.news_service import NewsService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


def get_events(request: Request) -> EventBus:
    return request.app.state.events


def get_news(request: Request) -> NewsService:
    return request.app.state.news


def get_settings_dep() -> Settings:
    return get_settings()
