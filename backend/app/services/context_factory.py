from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache
from app.core.events import EventBus
from app.plugins.sdk.context import AnalysisContext
from app.services.league_service import LeagueService
from app.services.news_service import NewsService
from app.services.player_service import PlayerService
from app.services.projection_service import ProjectionService


def build_context(
    *,
    session: AsyncSession,
    cache: Cache,
    events: EventBus,
    league_id: str,
    roster_id: int | None,
    week: int,
    season: str,
    nfl_state: dict | None = None,
    news: NewsService | None = None,
) -> AnalysisContext:
    league_service = LeagueService(session, nfl_state=nfl_state)
    player_service = PlayerService(session)
    projection_service = ProjectionService(session, player_service)
    news_service = news or NewsService()
    return AnalysisContext(
        league_id=league_id,
        roster_id=roster_id,
        week=week,
        season=season,
        league_service=league_service,
        player_service=player_service,
        projection_service=projection_service,
        news_service=news_service,
        cache=cache,
        events=events,
    )
