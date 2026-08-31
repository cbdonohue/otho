from __future__ import annotations

from typing import Any

from app.plugins.builtin import proj_of
from app.plugins.builtin.roster_health.analyzer import positional_grades
from app.plugins.builtin.trade_finder.analyzer import fairness, surplus_positions, value_of
from app.plugins.builtin.trade_finder.models import TradeParams
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisPlugin,
    AnalysisResult,
    PluginMetadata,
    comparison,
    ranking,
    recommendation,
)


class TradeFinderPlugin(AnalysisPlugin):
    metadata = PluginMetadata(
        id="trade_finder",
        name="Trade Finder",
        description="Find trade targets and grade proposed deals using weekly projection value.",
        version="0.1.0",
        category="trades",
        icon="🔄",
    )

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="find_trade_targets",
                description="Suggest 1-for-1 trades that fill a hole using surplus positions.",
                parameters={"type": "object", "properties": {"roster_id": {"type": "integer"}}},
                plugin_id=self.metadata.id,
            ),
            AgentTool(
                name="simulate_trade",
                description="Grade a proposed trade. Pass give and receive as lists of player_ids.",
                parameters={
                    "type": "object",
                    "properties": {
                        "give": {"type": "array", "items": {"type": "string"}},
                        "receive": {"type": "array", "items": {"type": "string"}},
                        "roster_id": {"type": "integer"},
                    },
                    "required": ["give", "receive"],
                },
                plugin_id=self.metadata.id,
            ),
        ]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = TradeParams.model_validate(params or {})
        tool = (params or {}).get("tool")
        if tool == "simulate_trade" or (parsed.give and parsed.receive):
            return await self._simulate(context, parsed)
        return await self._targets(context, parsed)

    async def _simulate(self, context: AnalysisContext, parsed: TradeParams) -> AnalysisResult:
        ids = list(parsed.give) + list(parsed.receive)
        players = await context.player_service.get_players(ids)
        projections = await context.projection_service.get_projections(ids, parsed.week or context.week, context.season)
        gv = value_of(parsed.give, projections)
        rv = value_of(parsed.receive, projections)
        verdict = fairness(gv, rv)
        give_names = ", ".join(players[i].display_name if i in players else i for i in parsed.give)
        recv_names = ", ".join(players[i].display_name if i in players else i for i in parsed.receive)
        return AnalysisResult(
            title="Trade grade",
            summary=f"Give {give_names} ({gv:.1f}) for {recv_names} ({rv:.1f}) — {verdict}.",
            data={"give_value": gv, "receive_value": rv, "verdict": verdict},
            widgets=[
                comparison(
                    {"name": "You give", "projection": gv, "players": give_names},
                    {"name": "You get", "projection": rv, "players": recv_names},
                ),
                recommendation(
                    f"Trade looks {verdict}",
                    f"Weekly projection delta {rv - gv:+.1f}.",
                    severity="low" if verdict == "you win" else "high" if verdict == "you lose" else "medium",
                    confidence=0.7,
                    column="opportunities",
                ),
            ],
        )

    async def _targets(self, context: AnalysisContext, parsed: TradeParams) -> AnalysisResult:
        roster_id = parsed.roster_id or context.roster_id
        week = parsed.week or context.week
        rosters = await context.league_service.get_rosters(context.league_id)
        me = next(r for r in rosters if r.roster_id == (roster_id or rosters[0].roster_id))
        my_players = await context.player_service.get_players(me.players)
        my_proj = await context.projection_service.get_projections(me.players, week, context.season)
        my_grades = positional_grades(my_players, me.players, my_proj)
        holes = [g["position"] for g in my_grades if g["grade"] in {"C", "C+", "D", "F"}]
        extra = surplus_positions(my_grades)
        ideas: list[dict] = []
        for other in rosters:
            if other.roster_id == me.roster_id:
                continue
            theirs = await context.player_service.get_players(other.players)
            tproj = await context.projection_service.get_projections(other.players, week, context.season)
            tgrades = positional_grades(theirs, other.players, tproj)
            their_holes = [g["position"] for g in tgrades if g["grade"] in {"C", "C+", "D", "F"}]
            # They want our surplus; we want their surplus at our hole.
            for pid, player in theirs.items():
                if player.position not in holes:
                    continue
                their_pts = proj_of(tproj, pid)
                for mid, mine in my_players.items():
                    if mine.position not in extra and mine.position not in their_holes:
                        continue
                    if mine.position == player.position:
                        continue
                    my_pts = proj_of(my_proj, mid)
                    if abs(my_pts - their_pts) > 4:
                        continue
                    ideas.append(
                        {
                            "give_id": mid,
                            "give": mine.display_name,
                            "receive_id": pid,
                            "receive": player.display_name,
                            "partner": other.owner_name or str(other.roster_id),
                            "delta": round(their_pts - my_pts, 2),
                        }
                    )
        ideas.sort(key=lambda x: -x["delta"])
        ideas = ideas[:8]
        widgets = []
        if ideas:
            top = ideas[0]
            widgets.append(
                recommendation(
                    f"Offer {top['give']} for {top['receive']}",
                    f"To {top['partner']} · weekly delta {top['delta']:+.1f}",
                    severity="medium",
                    confidence=0.6,
                    column="opportunities",
                )
            )
            widgets.append(
                ranking(
                    [
                        {
                            "rank": i + 1,
                            "label": f"{row['give']} → {row['receive']}",
                            "value": row["delta"],
                            "meta": row["partner"],
                        }
                        for i, row in enumerate(ideas[:6])
                    ],
                    title="Trade ideas",
                )
            )
        else:
            widgets.append(
                recommendation(
                    "No obvious 1-for-1 pops",
                    "Surplus and need don't line up cleanly. Try a 2-for-1.",
                    severity="low",
                    column="opportunities",
                )
            )
        return AnalysisResult(
            title="Trade Finder",
            summary=f"{len(ideas)} candidate 1-for-1 ideas. Holes: {', '.join(holes) or 'none'}.",
            data={"ideas": ideas, "holes": holes, "surplus": extra},
            widgets=widgets,
        )


PLUGIN = TradeFinderPlugin
