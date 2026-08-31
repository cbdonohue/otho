from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cache, get_events, get_news, get_session
from app.services.context_factory import build_context
from app.services.league_service import LeagueService
from app.services.player_service import PlayerService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

HOME_PLUGINS = ("matchup", "lineup", "waiver_wire", "roster_health", "injury_watch", "opponent_scout")


def _column_for(widget: dict) -> str:
    if widget.get("column"):
        return widget["column"]
    wtype = widget.get("type")
    if wtype == "recommendation" and widget.get("severity") == "high":
        return "actions"
    if wtype in {"recommendation"}:
        return "opportunities"
    return "watch"


@router.get("/{league_id}")
async def dashboard(
    league_id: str,
    request: Request,
    roster_id: int | None = None,
    week: int | None = None,
    session: AsyncSession = Depends(get_session),
    cache=Depends(get_cache),
    events=Depends(get_events),
    news=Depends(get_news),
):
    leagues = LeagueService(session)
    try:
        league = await leagues.get_league(league_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    rosters = await leagues.get_rosters(league_id)
    if not rosters:
        raise HTTPException(404, "no rosters synced")
    roster = next((r for r in rosters if r.roster_id == roster_id), rosters[0])
    use_week = week or league.week or 1
    matchups = await leagues.get_matchups(league_id, use_week)
    ctx = build_context(
        session=session,
        cache=cache,
        events=events,
        league_id=league_id,
        roster_id=roster.roster_id,
        week=use_week,
        season=league.season,
        nfl_state=request.app.state.nfl_state,
        news=news,
    )
    manager = request.app.state.plugins
    plugin_payloads = []
    columns = {"actions": [], "opportunities": [], "watch": []}
    for plugin_id in HOME_PLUGINS:
        try:
            result = await manager.analyze(plugin_id, ctx, {"roster_id": roster.roster_id, "week": use_week})
        except Exception as exc:
            plugin_payloads.append({"plugin_id": plugin_id, "error": str(exc)})
            continue
        plugin_payloads.append(result.to_dict())
        for widget in result.widgets:
            columns[_column_for(widget)].append({**widget, "plugin_id": plugin_id})

    pairing = next(
        (
            m
            for m in matchups
            if m.home.roster_id == roster.roster_id or (m.away and m.away.roster_id == roster.roster_id)
        ),
        None,
    )
    starter_ids = [pid for pid in roster.starters if pid and pid != "0"]
    players = await PlayerService(session).get_players(starter_ids)
    from app.services.projection_service import ProjectionService

    projections = await ProjectionService(session, PlayerService(session)).get_projections(
        starter_ids, use_week, league.season
    )
    starters = []
    for pid in starter_ids:
        player = players.get(pid)
        proj = projections.get(pid)
        starters.append(
            {
                "player_id": pid,
                "name": player.display_name if player else pid,
                "position": player.position if player else None,
                "team": player.team if player else None,
                "projection": proj.points if proj else 0,
                "injury": player.injury_status if player else None,
            }
        )
    names = {r.roster_id: r.owner_name or r.team_name or str(r.roster_id) for r in rosters}
    hero = None
    if pairing:
        you_side = pairing.home if pairing.home.roster_id == roster.roster_id else pairing.away
        opp_side = pairing.away if pairing.home.roster_id == roster.roster_id else pairing.home
        hero = {
            "you": {
                "roster_id": roster.roster_id,
                "name": names.get(roster.roster_id),
                "record": roster.record,
                "points": you_side.points if you_side else 0,
            },
            "opponent": {
                "roster_id": opp_side.roster_id if opp_side else None,
                "name": names.get(opp_side.roster_id) if opp_side else "BYE",
                "record": next((r.record for r in rosters if opp_side and r.roster_id == opp_side.roster_id), ""),
                "points": opp_side.points if opp_side else 0,
            }
            if opp_side
            else None,
            "week": use_week,
        }
    matchup_result = next((p for p in plugin_payloads if p.get("plugin_id") == "matchup"), {})
    if hero and matchup_result.get("data"):
        hero["projected_you"] = matchup_result["data"].get("home", {}).get("mean")
        hero["projected_opp"] = matchup_result["data"].get("away", {}).get("mean")
        hero["win_probability"] = matchup_result["data"].get("win_probability")
    return {
        "league": league.model_dump(),
        "roster": roster.model_dump(),
        "rosters": [{"roster_id": r.roster_id, "name": names[r.roster_id], "record": r.record} for r in rosters],
        "week": use_week,
        "hero": hero,
        "starters": starters,
        "columns": columns,
        "plugins": plugin_payloads,
        "nfl_state": request.app.state.nfl_state,
    }


@router.get("/{league_id}/widgets")
async def dashboard_widgets(
    league_id: str,
    request: Request,
    roster_id: int | None = None,
    week: int | None = None,
    session: AsyncSession = Depends(get_session),
    cache=Depends(get_cache),
    events=Depends(get_events),
    news=Depends(get_news),
):
    data = await dashboard(
        league_id,
        request,
        roster_id=roster_id,
        week=week,
        session=session,
        cache=cache,
        events=events,
        news=news,
    )
    return {"widgets": data["columns"], "week": data["week"]}
