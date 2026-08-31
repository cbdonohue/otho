from __future__ import annotations

from typing import Any

from app.plugins.builtin import optimal_lineup, proj_of, starter_slots
from app.plugins.builtin.lineup.analyzer import start_sit_swaps
from app.plugins.builtin.lineup.models import LineupParams
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisPlugin,
    AnalysisResult,
    PluginMetadata,
    comparison,
    player_table,
    recommendation,
)


class LineupPlugin(AnalysisPlugin):
    metadata = PluginMetadata(
        id="lineup",
        name="Start / Sit",
        description="Recommend an optimal lineup versus current starters using projections.",
        version="0.1.0",
        category="lineup",
        icon="📋",
    )

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="get_roster",
                description="Return the current roster with projections and recommended starters.",
                parameters={"type": "object", "properties": {"roster_id": {"type": "integer"}}},
                plugin_id=self.metadata.id,
            ),
            AgentTool(
                name="compare_players",
                description="Compare two players by projection, injury, and slot fit.",
                parameters={
                    "type": "object",
                    "properties": {
                        "player_a": {"type": "string"},
                        "player_b": {"type": "string"},
                    },
                    "required": ["player_a", "player_b"],
                },
                plugin_id=self.metadata.id,
            ),
        ]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = LineupParams.model_validate(params or {})
        tool = (params or {}).get("tool")
        if tool == "compare_players" and parsed.player_a and parsed.player_b:
            return await self._compare(context, parsed.player_a, parsed.player_b)

        roster_id = parsed.roster_id or context.roster_id
        week = parsed.week or context.week
        league = await context.league_service.get_league(context.league_id)
        rosters = await context.league_service.get_rosters(context.league_id)
        roster = next(r for r in rosters if r.roster_id == (roster_id or rosters[0].roster_id))
        slots = starter_slots(league.roster_positions)
        players = await context.player_service.get_players(roster.players)
        projections = await context.projection_service.get_projections(roster.players, week, context.season)
        ordered = [players[pid] for pid in roster.players if pid in players]
        optimal = optimal_lineup(slots, ordered, projections)
        swaps = start_sit_swaps(roster.starters, optimal, projections, players)
        opt_total = round(sum(pts for _, _, pts in optimal), 2)
        cur_total = round(sum(proj_of(projections, pid) for pid in roster.starters if pid != "0"), 2)

        widgets: list[dict] = []
        for swap in swaps[:4]:
            widgets.append(
                recommendation(
                    f"Start {swap['start_name']}",
                    f"Sit {swap['sit_name']} · projected advantage +{swap['delta']:.1f} points",
                    severity="high" if swap["delta"] >= 3 else "medium",
                    confidence=min(0.92, 0.55 + swap["delta"] / 20),
                    column="actions",
                )
            )
        if not swaps:
            widgets.append(
                recommendation(
                    "Lineup looks correct",
                    f"Current starters project {cur_total:.1f}; optimal is {opt_total:.1f}.",
                    severity="low",
                    confidence=0.7,
                    column="actions",
                )
            )
        widgets.append(
            player_table(
                ["slot", "optimal", "proj", "current"],
                [
                    {
                        "slot": slot,
                        "optimal": player.display_name,
                        "proj": pts,
                        "current": (
                            players[roster.starters[i]].display_name
                            if i < len(roster.starters) and roster.starters[i] in players
                            else "—"
                        ),
                    }
                    for i, (slot, player, pts) in enumerate(optimal)
                ],
                title="Optimal vs current",
            )
        )
        delta = round(opt_total - cur_total, 2)
        summary = (
            f"Optimal lineup projects {opt_total:.1f} vs current {cur_total:.1f} "
            f"({'+' if delta >= 0 else ''}{delta:.1f}). {len(swaps)} swap(s) recommended."
        )
        return AnalysisResult(
            title="Start / Sit",
            summary=summary,
            data={
                "optimal_total": opt_total,
                "current_total": cur_total,
                "swaps": swaps,
                "optimal": [
                    {"slot": s, "player_id": p.player_id, "name": p.display_name, "projection": pts}
                    for s, p, pts in optimal
                ],
                "roster_id": roster.roster_id,
            },
            widgets=widgets,
        )

    async def _compare(self, context: AnalysisContext, a_id: str, b_id: str) -> AnalysisResult:
        players = await context.player_service.get_players([a_id, b_id])
        a = players.get(a_id)
        b = players.get(b_id)
        if not a or not b:
            return AnalysisResult(title="Compare", summary="One or both players were not found.", data={})
        projections = await context.projection_service.get_projections([a_id, b_id], context.week, context.season)
        ap, bp = proj_of(projections, a_id), proj_of(projections, b_id)
        winner = a if ap >= bp else b
        delta = abs(ap - bp)
        return AnalysisResult(
            title=f"{a.display_name} vs {b.display_name}",
            summary=f"{winner.display_name} projects {max(ap, bp):.1f} vs {min(ap, bp):.1f} ({delta:.1f} edge).",
            data={"a": {"id": a_id, "name": a.display_name, "proj": ap}, "b": {"id": b_id, "name": b.display_name, "proj": bp}},
            widgets=[
                comparison(
                    {"name": a.display_name, "projection": ap, "injury": a.injury_status, "team": a.team},
                    {"name": b.display_name, "projection": bp, "injury": b.injury_status, "team": b.team},
                    title="Player comparison",
                ),
                recommendation(
                    f"Prefer {winner.display_name}",
                    f"Projected edge {delta:.1f} points this week.",
                    severity="medium" if delta < 3 else "high",
                    confidence=min(0.9, 0.5 + delta / 12),
                ),
            ],
        )


PLUGIN = LineupPlugin
