from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cache, get_events, get_news, get_session
from app.services.ask import AskOtho
from app.services.context_factory import build_context
from app.services.league_service import LeagueService

router = APIRouter(prefix="/api/ask", tags=["ask"])


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    league_id: str
    roster_id: int | None = None
    week: int | None = None


@router.post("")
async def ask_otho(
    body: AskBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
    cache=Depends(get_cache),
    events=Depends(get_events),
    news=Depends(get_news),
):
    try:
        league = await LeagueService(session).get_league(body.league_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    week = body.week or league.week or 1
    ctx = build_context(
        session=session,
        cache=cache,
        events=events,
        league_id=body.league_id,
        roster_id=body.roster_id,
        week=week,
        season=league.season,
        nfl_state=request.app.state.nfl_state,
        news=news,
    )
    engine: AskOtho = request.app.state.ask
    return await engine.ask(body.question, ctx)
