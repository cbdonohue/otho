from __future__ import annotations

from typing import Any

from app.plugins.builtin.opponent_scout.analyzer import likely_needs
from app.plugins.builtin.opponent_scout.models import ScoutParams
from app.plugins.builtin.roster_health.analyzer import positional_grades
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisPlugin,
    AnalysisResult,
    PluginMetadata,
    alert,
    ranking,
    recommendation,
)


class OpponentScoutPlugin(AnalysisPlugin):
    metadata = PluginMetadata(
        id="opponent_scout",
        name="Opponent Scout",
        description="Opponent strengths, weak positions, and likely waiver needs.",
        version="0.1.0",
        category="matchup",
        icon="🔭",
    )

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="scout_opponent",
                description="Scout this week's opponent: strengths, holes, and waiver competition.",
                parameters={"type": "object", "properties": {"roster_id": {"type": "integer"}}},
                plugin_id=self.metadata.id,
            )
        ]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = ScoutParams.model_validate(params or {})
        roster_id = parsed.roster_id or context.roster_id
        week = parsed.week or context.week
        rosters = {r.roster_id: r for r in await context.league_service.get_rosters(context.league_id)}
        me = rosters[roster_id or next(iter(rosters))]
        matchups = await context.league_service.get_matchups(context.league_id, week)
        opp = None
        for m in matchups:
            if m.home.roster_id == me.roster_id and m.away:
                opp = rosters.get(m.away.roster_id)
            elif m.away and m.away.roster_id == me.roster_id:
                opp = rosters.get(m.home.roster_id)
        if not opp:
            return AnalysisResult(
                title="Opponent Scout",
                summary="Bye week — no opponent to scout.",
                data={"bye": True},
                widgets=[alert("Bye week", "No opponent this week.", severity="info")],
            )
        players = await context.player_service.get_players(opp.players)
        projections = await context.projection_service.get_projections(opp.players, week, context.season)
        grades = positional_grades(players, opp.players, projections)
        needs = likely_needs(grades)
        strengths = [g for g in grades if g["grade"] in {"A+", "A", "B+"}]
        widgets = [
            ranking(
                [
                    {
                        "rank": i + 1,
                        "label": g["position"],
                        "value": g["starter_projection"],
                        "meta": g["grade"],
                    }
                    for i, g in enumerate(sorted(grades, key=lambda x: -x["score"]))
                ],
                title=f"{opp.owner_name or opp.roster_id} positions",
            )
        ]
        if needs:
            widgets.append(
                recommendation(
                    f"{opp.owner_name} likely hunting {', '.join(needs)}",
                    "Expect waiver competition at those positions.",
                    severity="medium",
                    confidence=0.66,
                    column="watch",
                )
            )
        if strengths:
            top = strengths[0]
            widgets.append(
                alert(
                    f"Their {top['position']} is a problem",
                    f"Starter projects {top['starter_projection']:.1f} ({top['grade']}). Don't fade that slot blindly.",
                    severity="warning",
                    column="watch",
                )
            )
        return AnalysisResult(
            title=f"Scout: {opp.owner_name or opp.roster_id}",
            summary=(
                f"{opp.owner_name} is {opp.record}. Strong: "
                f"{', '.join(s['position'] for s in strengths) or 'balanced'}. "
                f"Needs: {', '.join(needs) or 'none'}."
            ),
            data={"opponent_roster_id": opp.roster_id, "grades": grades, "needs": needs},
            widgets=widgets,
        )


PLUGIN = OpponentScoutPlugin
