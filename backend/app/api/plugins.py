from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_cache, get_events, get_news
from app.core.models import PluginResultRow
from app.services.context_factory import build_context
from app.services.league_service import LeagueService

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class AnalyzeBody(BaseModel):
    roster_id: int | None = None
    week: int | None = None
    iterations: int | None = None
    params: dict = Field(default_factory=dict)


@router.get("")
async def list_plugins(request: Request):
    manager = request.app.state.plugins
    return {
        "plugins": [
            {
                "id": p.metadata.id,
                "name": p.metadata.name,
                "description": p.metadata.description,
                "version": p.metadata.version,
                "category": p.metadata.category,
                "icon": p.metadata.icon,
                "tools": [t.name for t in p.tools()],
                "subscriptions": list(getattr(p, "subscriptions", []) or []),
            }
            for p in manager.all()
        ]
    }


@router.get("/{plugin_id}")
async def get_plugin(plugin_id: str, request: Request):
    try:
        plugin = request.app.state.plugins.get(plugin_id)
    except KeyError as exc:
        raise HTTPException(404, f"unknown plugin {plugin_id}") from exc
    meta = plugin.metadata
    return {
        "id": meta.id,
        "name": meta.name,
        "description": meta.description,
        "version": meta.version,
        "category": meta.category,
        "icon": meta.icon,
        "tools": [t.openai_schema() for t in plugin.tools()],
        "subscriptions": list(getattr(plugin, "subscriptions", []) or []),
    }


@router.post("/{plugin_id}/analyze")
async def analyze_plugin(
    plugin_id: str,
    body: AnalyzeBody,
    request: Request,
    league_id: str,
    session: AsyncSession = Depends(get_session),
    cache=Depends(get_cache),
    events=Depends(get_events),
    news=Depends(get_news),
):
    manager = request.app.state.plugins
    try:
        manager.get(plugin_id)
    except KeyError as exc:
        raise HTTPException(404, f"unknown plugin {plugin_id}") from exc
    try:
        league = await LeagueService(session).get_league(league_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    week = body.week or league.week or 1
    params = dict(body.params)
    if body.roster_id is not None:
        params["roster_id"] = body.roster_id
    if body.week is not None:
        params["week"] = body.week
    if body.iterations is not None:
        params["iterations"] = body.iterations
    ctx = build_context(
        session=session,
        cache=cache,
        events=events,
        league_id=league_id,
        roster_id=body.roster_id,
        week=week,
        season=league.season,
        nfl_state=request.app.state.nfl_state,
        news=news,
    )
    result = await manager.analyze(plugin_id, ctx, params)
    session.add(
        PluginResultRow(
            plugin_id=plugin_id,
            league_id=league_id,
            roster_id=body.roster_id,
            week=week,
            title=result.title,
            summary=result.summary,
            data=result.data,
            widgets=result.widgets,
        )
    )
    await session.commit()
    return result.to_dict()
