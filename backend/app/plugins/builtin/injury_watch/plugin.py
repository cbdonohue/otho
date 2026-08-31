from __future__ import annotations

from typing import Any

from app.core.events import PLAYER_INJURY, ROSTER_UPDATED, Event
from app.plugins.builtin.injury_watch.analyzer import severity_for
from app.plugins.builtin.injury_watch.models import InjuryParams
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisResult,
    BackgroundPlugin,
    PluginMetadata,
    alert,
    recommendation,
)


class InjuryWatchPlugin(BackgroundPlugin):
    """Background detector for injuries and roster changes."""

    metadata = PluginMetadata(
        id="injury_watch",
        name="Injury Watch",
        description="Watches injury and roster events; surfaces start/sit and waiver implications.",
        version="0.1.0",
        category="alerts",
        icon="🚑",
    )
    subscriptions = [PLAYER_INJURY, ROSTER_UPDATED]

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    async def handle_event(self, event: Event) -> None:
        self._events.append(
            {
                "type": event.type,
                "payload": event.payload,
                "league_id": event.league_id,
                "at": event.occurred_at.isoformat(),
            }
        )
        self._events = self._events[-100:]

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="injury_report",
                description="List injured players on this roster and suggested replacements.",
                parameters={"type": "object", "properties": {"roster_id": {"type": "integer"}}},
                plugin_id=self.metadata.id,
            )
        ]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = InjuryParams.model_validate(params or {})
        roster_id = parsed.roster_id or context.roster_id
        rosters = await context.league_service.get_rosters(context.league_id)
        roster = next(r for r in rosters if r.roster_id == (roster_id or rosters[0].roster_id))
        players = await context.player_service.get_players(roster.players)
        injured = [p for p in players.values() if p.injury_status]
        widgets = []
        for player in injured:
            sev = severity_for(player.injury_status)
            widgets.append(
                alert(
                    f"{player.display_name} — {player.injury_status}",
                    f"{player.position} {player.team or ''} · {'starter' if player.player_id in roster.starters else 'bench'}",
                    severity="error" if sev == "high" else "warning",
                    column="actions" if player.player_id in roster.starters else "watch",
                )
            )
            if player.player_id in roster.starters and sev == "high":
                widgets.append(
                    recommendation(
                        f"Do not start {player.display_name}",
                        "Listed out/IR. Swap in the next-best eligible player.",
                        severity="high",
                        confidence=0.95,
                        column="actions",
                    )
                )
        if not injured:
            widgets.append(alert("No injuries on this roster", "No designated injury flags.", severity="info"))
        return AnalysisResult(
            title="Injury Watch",
            summary=f"{len(injured)} injured player(s) on roster. Background events captured: {len(self._events)}.",
            data={
                "injured": [
                    {"player_id": p.player_id, "name": p.display_name, "status": p.injury_status, "position": p.position}
                    for p in injured
                ],
                "recent_events": self._events[-10:],
            },
            widgets=widgets,
        )


PLUGIN = InjuryWatchPlugin
