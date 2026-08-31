"""Tiny plugin SDK. Plugins depend on this — never on Sleeper JSON."""

from app.plugins.sdk.context import AnalysisContext
from app.plugins.sdk.plugin import AgentTool, AnalysisPlugin, BackgroundPlugin, PluginMetadata
from app.plugins.sdk.result import AnalysisResult
from app.plugins.sdk.widgets import (
    alert,
    chart,
    comparison,
    markdown,
    matchup as matchup_widget,
    metric,
    player_card,
    player_table,
    ranking,
    recommendation,
    timeline,
)

__all__ = [
    "AgentTool",
    "AnalysisContext",
    "AnalysisPlugin",
    "AnalysisResult",
    "BackgroundPlugin",
    "PluginMetadata",
    "alert",
    "chart",
    "comparison",
    "markdown",
    "matchup_widget",
    "metric",
    "player_card",
    "player_table",
    "ranking",
    "recommendation",
    "timeline",
]
