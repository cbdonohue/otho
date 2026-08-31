from __future__ import annotations

from typing import Any

from app.core.events import TRANSACTION_CREATED, Event
from app.plugins.builtin.league_activity.analyzer import pulse
from app.plugins.builtin.league_activity.models import ActivityParams
from app.plugins.sdk import (
    AgentTool,
    AnalysisContext,
    AnalysisPlugin,
    AnalysisResult,
    BackgroundPlugin,
    PluginMetadata,
    alert,
    timeline,
)


class LeagueActivityPlugin(BackgroundPlugin):
    metadata = PluginMetadata(
        id="league_activity",
        name="League Activity",
        description="Recent transactions pulse — waivers, adds, trades.",
        version="0.1.0",
        category="league",
        icon="⚡",
    )
    subscriptions = [TRANSACTION_CREATED]

    def __init__(self) -> None:
        self._alerts: list[dict[str, Any]] = []

    def tools(self) -> list[AgentTool]:
        return [
            AgentTool(
                name="league_pulse",
                description="Summarize recent league transactions and activity heat.",
                parameters={"type": "object", "properties": {"week": {"type": "integer"}}},
                plugin_id=self.metadata.id,
            )
        ]

    async def handle_event(self, event: Event) -> None:
        payload = event.payload or {}
        self._alerts.append(
            {
                "type": payload.get("type"),
                "week": payload.get("week"),
                "adds": payload.get("adds"),
                "league_id": event.league_id,
            }
        )
        self._alerts = self._alerts[-50:]

    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        parsed = ActivityParams.model_validate(params or {})
        week = parsed.week or context.week
        txs = await context.league_service.get_transactions(context.league_id, week)
        if not txs:
            txs = await context.league_service.get_transactions(context.league_id)
        stats = pulse(txs)
        events = []
        players_needed: set[str] = set()
        for tx in txs[: parsed.limit]:
            players_needed.update(tx.adds.keys())
            players_needed.update(tx.drops.keys())
        names = await context.player_service.get_players(list(players_needed))
        for tx in txs[: parsed.limit]:
            add_names = ", ".join(names[p].display_name if p in names else p for p in tx.adds)
            drop_names = ", ".join(names[p].display_name if p in names else p for p in tx.drops)
            label = tx.type.replace("_", " ")
            body = add_names or drop_names or label
            if add_names and drop_names:
                body = f"+ {add_names} / - {drop_names}"
            events.append(
                {
                    "id": tx.transaction_id,
                    "title": label,
                    "body": body,
                    "at": tx.created_at.isoformat() if tx.created_at else None,
                    "week": tx.week,
                }
            )
        widgets = [
            alert(
                f"League is {stats['heat']}",
                f"{stats['total']} transactions · waivers {stats['counts']['waiver']} · trades {stats['counts']['trade']}",
                severity="warning" if stats["heat"] == "frantic" else "info",
                column="watch",
            ),
            timeline(events, title="Transaction pulse"),
        ]
        return AnalysisResult(
            title="League Pulse",
            summary=f"{stats['total']} recent moves. Heat: {stats['heat']}.",
            data={"pulse": stats, "events": events, "live_alerts": self._alerts[-10:]},
            widgets=widgets,
        )


PLUGIN = LeagueActivityPlugin
