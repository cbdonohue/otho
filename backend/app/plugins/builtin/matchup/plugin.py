from __future__ import annotations

from typing import Any

from app.plugins.builtin.matchup.analyzer import simulate
from app.plugins.builtin.matchup.models import MatchupSimParams
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisPlugin,
    AnalysisResult,
    PluginMetadata,
    matchup_widget,
    metric,
    recommendation,
)


class MatchupSimulatorPlugin(AnalysisPlugin):
    metadata = PluginMetadata(
        id="matchup",
        name="Matchup Simulator",
        description="Monte Carlo matchup using projections and positional variance.",
        version="0.1.0",
        category="matchup",
        icon="⚔️",
    )

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="simulate_matchup",
                description="Simulate this week's matchup and return win probability plus projected scores.",
                parameters={
                    "type": "object",
                    "properties": {
                        "roster_id": {"type": "integer"},
                        "week": {"type": "integer"},
                        "iterations": {"type": "integer", "default": 4000},
                    },
                },
                plugin_id=self.metadata.id,
            )
        ]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = MatchupSimParams.model_validate(params or {})
        roster_id = parsed.roster_id or context.roster_id
        week = parsed.week or context.week
        league = await context.league_service.get_league(context.league_id)
        rosters = {r.roster_id: r for r in await context.league_service.get_rosters(context.league_id)}
        if roster_id is None:
            roster_id = next(iter(rosters))
        me = rosters[roster_id]
        matchups = await context.league_service.get_matchups(context.league_id, week)
        pairing = None
        for m in matchups:
            if m.home.roster_id == roster_id or (m.away and m.away.roster_id == roster_id):
                pairing = m
                break
        opp_id = None
        if pairing:
            if pairing.home.roster_id == roster_id:
                opp_id = pairing.away.roster_id if pairing.away else None
            else:
                opp_id = pairing.home.roster_id
        opp = rosters.get(opp_id) if opp_id else None

        my_ids = [pid for pid in me.starters if pid and pid != "0"]
        opp_ids = [pid for pid in (opp.starters if opp else []) if pid and pid != "0"]
        all_ids = my_ids + opp_ids
        players = await context.player_service.get_players(all_ids)
        projections = await context.projection_service.get_projections(all_ids, week, context.season)

        def pack(ids: list[str]):
            packed = []
            rows = []
            for pid in ids:
                player = players.get(pid)
                proj = projections.get(pid)
                if not player or not proj:
                    continue
                packed.append((player, proj))
                rows.append(
                    {
                        "player_id": pid,
                        "name": player.display_name,
                        "position": player.position,
                        "projection": proj.points,
                    }
                )
            return packed, rows

        home_pack, home_rows = pack(my_ids)
        away_pack, away_rows = pack(opp_ids)
        sim = simulate(home_pack, away_pack or home_pack, iterations=parsed.iterations)
        if not away_pack:
            sim["win_probability"] = 1.0
            sim["away"] = {"mean": 0, "p10": 0, "p90": 0}

        wp = sim["win_probability"]
        my_name = me.owner_name or me.team_name or f"Roster {me.roster_id}"
        opp_name = (opp.owner_name or opp.team_name or "BYE") if opp else "BYE"
        if wp >= 0.62:
            rec = recommendation(
                f"Lean {my_name}",
                f"Win probability {wp:.0%} — projected {sim['home']['mean']:.1f} to {sim['away']['mean']:.1f}",
                severity="low",
                confidence=min(0.95, 0.5 + abs(wp - 0.5)),
            )
        elif wp <= 0.38:
            rec = recommendation(
                f"Underdog vs {opp_name}",
                "Consider a boom/bust lineup if you need to swing the matchup.",
                severity="high",
                confidence=min(0.95, 0.5 + abs(wp - 0.5)),
            )
        else:
            rec = recommendation(
                "Coin-flip matchup",
                "Start your highest-floor lineup; small edges matter this week.",
                severity="medium",
                confidence=0.55,
            )

        widgets = [
            matchup_widget(
                home={
                    "roster_id": me.roster_id,
                    "name": my_name,
                    "projected": sim["home"]["mean"],
                    "record": me.record,
                },
                away={
                    "roster_id": opp.roster_id if opp else None,
                    "name": opp_name,
                    "projected": sim["away"]["mean"],
                    "record": opp.record if opp else "",
                },
                week=week,
                win_probability=wp,
            ),
            metric("Win probability", f"{wp:.0%}"),
            metric("Your projection", sim["home"]["mean"], hint=f"10-90: {sim['home']['p10']}-{sim['home']['p90']}"),
            metric("Opp projection", sim["away"]["mean"], hint=f"10-90: {sim['away']['p10']}-{sim['away']['p90']}"),
            rec,
        ]
        return AnalysisResult(
            title=f"{my_name} vs {opp_name}",
            summary=(
                f"Monte Carlo ({parsed.iterations:,} iters): {my_name} {sim['home']['mean']:.1f} – "
                f"{sim['away']['mean']:.1f} {opp_name}. Win probability {wp:.0%}."
            ),
            data={
                "win_probability": wp,
                "home": {**sim["home"], "roster_id": me.roster_id, "name": my_name, "starters": home_rows},
                "away": {**sim["away"], "roster_id": opp_id, "name": opp_name, "starters": away_rows},
                "iterations": parsed.iterations,
                "week": week,
            },
            widgets=widgets,
        )


PLUGIN = MatchupSimulatorPlugin
