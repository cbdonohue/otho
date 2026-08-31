from __future__ import annotations

from typing import Any

from app.plugins.builtin.playoff_odds.analyzer import simulate_standings
from app.plugins.builtin.playoff_odds.models import OddsParams
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisPlugin,
    AnalysisResult,
    PluginMetadata,
    metric,
    ranking,
    recommendation,
)


class PlayoffOddsPlugin(AnalysisPlugin):
    metadata = PluginMetadata(
        id="playoff_odds",
        name="Playoff Odds",
        description="Monte Carlo rest-of-season standings from current records and scoring pace.",
        version="0.1.0",
        category="playoffs",
        icon="🏆",
    )

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="calculate_playoff_odds",
                description="Estimate playoff probability for every team, highlighting this roster.",
                parameters={
                    "type": "object",
                    "properties": {
                        "roster_id": {"type": "integer"},
                        "iterations": {"type": "integer", "default": 2500},
                    },
                },
                plugin_id=self.metadata.id,
            )
        ]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = OddsParams.model_validate(params or {})
        league = await context.league_service.get_league(context.league_id)
        rosters = await context.league_service.get_rosters(context.league_id)
        week = context.week
        remaining = max(0, league.playoff_week_start - week)
        odds = simulate_standings(rosters, remaining, league.playoff_teams, parsed.iterations)
        names = {r.roster_id: r.owner_name or r.team_name or str(r.roster_id) for r in rosters}
        ranked = sorted(rosters, key=lambda r: odds[r.roster_id], reverse=True)
        roster_id = parsed.roster_id or context.roster_id or ranked[0].roster_id
        mine = odds.get(roster_id, 0.0)
        widgets = [
            metric("Your playoff odds", f"{mine:.0%}", hint=f"{remaining} weeks left"),
            ranking(
                [
                    {
                        "rank": i + 1,
                        "label": names[r.roster_id],
                        "value": odds[r.roster_id],
                        "meta": r.record,
                    }
                    for i, r in enumerate(ranked)
                ],
                title="Playoff probability",
            ),
        ]
        if mine >= 0.75:
            widgets.insert(
                0,
                recommendation(
                    "Lock in the seed",
                    "Don't sell future for a coin-flip this week unless you need a swing.",
                    severity="low",
                    confidence=mine,
                    column="watch",
                ),
            )
        elif mine <= 0.25:
            widgets.insert(
                0,
                recommendation(
                    "You need to gamble",
                    "Playoff odds are slim — target boom lineups and aggressive waivers.",
                    severity="high",
                    confidence=1 - mine,
                    column="actions",
                ),
            )
        return AnalysisResult(
            title="Playoff Odds",
            summary=f"{names.get(roster_id)} sits at {mine:.0%} with {remaining} week(s) until playoffs.",
            data={
                "odds": {str(k): v for k, v in odds.items()},
                "remaining": remaining,
                "playoff_teams": league.playoff_teams,
                "roster_id": roster_id,
            },
            widgets=widgets,
        )


PLUGIN = PlayoffOddsPlugin
