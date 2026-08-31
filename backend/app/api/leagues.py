from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cache, get_events, get_news, get_session
from app.core.cache import Cache
from app.core.events import EventBus
from app.services.demo import seed_demo_league
from app.services.league_service import LeagueService
from app.services.news_service import NewsService
from app.services.sync import SyncService

router = APIRouter(prefix="/api/leagues", tags=["leagues"])


class AddLeagueBody(BaseModel):
    league_id: str = Field(min_length=4)
    provider: str = "sleeper"


@router.get("")
async def list_leagues(session: AsyncSession = Depends(get_session)):
    leagues = await LeagueService(session).list_leagues()
    return {"leagues": [lg.model_dump() for lg in leagues]}


@router.post("/demo")
async def seed_demo(session: AsyncSession = Depends(get_session)):
    league_id = await seed_demo_league(session)
    league = await LeagueService(session).get_league(league_id)
    return {"league": league.model_dump()}


@router.post("")
async def add_league(
    body: AddLeagueBody,
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
    events: EventBus = Depends(get_events),
    news: NewsService = Depends(get_news),
):
    if body.provider != "sleeper":
        raise HTTPException(400, "Only the Sleeper provider is wired in v0.1")
    sync = SyncService(session, cache, events, news=news)
    try:
        await sync.full_sync(body.league_id)
    except Exception as exc:
        raise HTTPException(502, f"Sleeper sync failed: {exc}") from exc
    league = await LeagueService(session).get_league(body.league_id)
    return {"league": league.model_dump()}


@router.get("/{league_id}")
async def get_league(league_id: str, session: AsyncSession = Depends(get_session)):
    try:
        league = await LeagueService(session).get_league(league_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    users = await LeagueService(session).get_users(league_id)
    return {"league": league.model_dump(), "users": [u.model_dump() for u in users]}


@router.get("/{league_id}/rosters")
async def get_rosters(league_id: str, session: AsyncSession = Depends(get_session)):
    rosters = await LeagueService(session).get_rosters(league_id)
    return {"rosters": [r.model_dump() for r in rosters]}


@router.get("/{league_id}/matchups")
async def get_matchups(league_id: str, week: int | None = None, session: AsyncSession = Depends(get_session)):
    leagues = LeagueService(session)
    try:
        league = await leagues.get_league(league_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    matchups = await leagues.get_matchups(league_id, week or league.week or 1)
    return {"week": week or league.week, "matchups": [m.model_dump() for m in matchups]}


@router.get("/{league_id}/transactions")
async def get_transactions(league_id: str, week: int | None = None, session: AsyncSession = Depends(get_session)):
    txs = await LeagueService(session).get_transactions(league_id, week)
    return {"transactions": [t.model_dump(mode="json") for t in txs]}


@router.post("/{league_id}/sync")
async def sync_league(
    league_id: str,
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
    events: EventBus = Depends(get_events),
    news: NewsService = Depends(get_news),
):
    await SyncService(session, cache, events, news=news).full_sync(league_id)
    return {"ok": True, "league_id": league_id}
