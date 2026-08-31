from __future__ import annotations

from typing import Any

from app.plugins.builtin.roster_health.analyzer import positional_grades
from app.plugins.builtin.roster_health.models import HealthParams
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisPlugin,
    AnalysisResult,
    PluginMetadata,
    alert,
    chart,
    recommendation,
)


class RosterHealthPlugin(AnalysisPlugin):
    metadata = PluginMetadata(
        id="roster_health",
        name="Roster Health",
        description="Positional grades and weakness detection for a roster.",
        version="0.1.0",
        category="roster",
        icon="❤️",
    )

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="find_roster_weaknesses",
                description="Grade each position and list the weakest spots on this roster.",
                parameters={"type": "object", "properties": {"roster_id": {"type": "integer"}}},
                plugin_id=self.metadata.id,
            )
        ]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = HealthParams.model_validate(params or {})
        roster_id = parsed.roster_id or context.roster_id
        week = parsed.week or context.week
        rosters = await context.league_service.get_rosters(context.league_id)
        roster = next(r for r in rosters if r.roster_id == (roster_id or rosters[0].roster_id))
        players = await context.player_service.get_players(roster.players)
        projections = await context.projection_service.get_projections(roster.players, week, context.season)
        grades = positional_grades(players, roster.players, projections)
        weak = [g for g in grades if g["grade"] in {"C", "C+", "D", "F"}]
        widgets = [
            chart(
                "bar",
                [g["position"] for g in grades],
                [{"name": "starter", "values": [g["starter_projection"] for g in grades]}],
                title="Positional projection",
            )
        ]
        for w in weak:
            widgets.append(
                recommendation(
                    f"Upgrade {w['position']}",
                    w["notes"] + f" · grade {w['grade']}",
                    severity="high" if w["grade"] in {"D", "F"} else "medium",
                    confidence=0.72,
                    column="watch",
                )
            )
        if not weak:
            widgets.append(alert("Balanced roster", "No glaring positional holes this week.", severity="info"))
        weakest = ", ".join(f"{g['position']} ({g['grade']})" for g in weak) or "none"
        return AnalysisResult(
            title="Roster Health",
            summary=f"{roster.owner_name or roster.roster_id} positional grades. Weak spots: {weakest}.",
            data={"grades": grades, "weak": weak, "roster_id": roster.roster_id},
            widgets=widgets,
        )


PLUGIN = RosterHealthPlugin
