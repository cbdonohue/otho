from __future__ import annotations

from typing import Any

from app.plugins.builtin.waiver_wire.analyzer import positional_need, score_waiver
from app.plugins.builtin.waiver_wire.models import WaiverParams
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisPlugin,
    AnalysisResult,
    PluginMetadata,
    ranking,
    recommendation,
)


class WaiverWirePlugin(AnalysisPlugin):
    metadata = PluginMetadata(
        id="waiver_wire",
        name="Waiver Wire",
        description="Rank available players for this roster using projections and positional need.",
        version="0.1.0",
        category="waivers",
        icon="📡",
    )

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="rank_waivers",
                description="Rank the best available waiver-wire players for this roster.",
                parameters={
                    "type": "object",
                    "properties": {
                        "roster_id": {"type": "integer"},
                        "limit": {"type": "integer", "default": 12},
                        "position": {"type": "string"},
                    },
                },
                plugin_id=self.metadata.id,
            )
        ]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = WaiverParams.model_validate(params or {})
        roster_id = parsed.roster_id or context.roster_id
        week = parsed.week or context.week
        rosters = await context.league_service.get_rosters(context.league_id)
        roster = next(r for r in rosters if r.roster_id == (roster_id or rosters[0].roster_id))
        mine = await context.player_service.get_players(roster.players)
        mine_proj = await context.projection_service.get_projections(roster.players, week, context.season)
        need = positional_need(roster, mine, mine_proj)
        positions = [parsed.position] if parsed.position else None
        available = await context.player_service.available(context.league_id, positions)
        available = [p for p in available if p.position in {"QB", "RB", "WR", "TE", "K", "DEF"}][:120]
        avail_proj = await context.projection_service.get_projections(
            [p.player_id for p in available], week, context.season
        )
        trending = {t.player_id: t.count for t in await context.player_service.trending("add")}
        ranked = []
        for player in available:
            proj = avail_proj.get(player.player_id)
            pts = proj.points if proj else 0.0
            if pts < 4.5 and (player.position or "") not in {"K", "DEF"}:
                continue
            score = score_waiver(player, pts, need, trending.get(player.player_id, 0))
            ranked.append(
                {
                    "player_id": player.player_id,
                    "name": player.display_name,
                    "position": player.position,
                    "team": player.team,
                    "projection": pts,
                    "need": need.get((player.position or "").upper(), 1.0),
                    "score": score,
                    "injury": player.injury_status,
                }
            )
        ranked.sort(key=lambda r: r["score"], reverse=True)
        top = ranked[: parsed.limit]
        widgets = []
        if top:
            best = top[0]
            widgets.append(
                recommendation(
                    f"Claim {best['name']}",
                    f"{best['position']} · {best['projection']:.1f} proj · need x{best['need']}",
                    severity="high" if best["need"] >= 1.4 else "medium",
                    confidence=min(0.88, 0.5 + best["score"] / 40),
                    column="opportunities",
                )
            )
        widgets.append(
            ranking(
                [
                    {
                        "rank": i + 1,
                        "label": f"{row['name']} ({row['position']})",
                        "value": row["projection"],
                        "meta": row["team"],
                    }
                    for i, row in enumerate(top[:10])
                ],
                title="Waiver targets",
            )
        )
        names = ", ".join(r["name"] for r in top[:5]) or "none"
        return AnalysisResult(
            title="Waiver Wire",
            summary=f"Top available adds for {roster.owner_name or roster.roster_id}: {names}.",
            data={"targets": top, "need": need, "roster_id": roster.roster_id},
            widgets=widgets,
        )


PLUGIN = WaiverWirePlugin
