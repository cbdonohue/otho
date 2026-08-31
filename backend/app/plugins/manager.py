"""Load built-in plugins and pip-installable `otho.plugins` entry points."""

from __future__ import annotations

import importlib
import logging
from importlib.metadata import entry_points
from typing import Any

from app.core.events import EventBus
from app.plugins.sdk.context import AnalysisContext
from app.plugins.sdk.plugin import AgentTool, AnalysisPlugin
from app.plugins.sdk.result import AnalysisResult

logger = logging.getLogger("otho.plugins")

BUILTIN_MODULES = [
    "app.plugins.builtin.matchup.plugin",
    "app.plugins.builtin.lineup.plugin",
    "app.plugins.builtin.waiver_wire.plugin",
    "app.plugins.builtin.roster_health.plugin",
    "app.plugins.builtin.opponent_scout.plugin",
    "app.plugins.builtin.league_activity.plugin",
    "app.plugins.builtin.injury_watch.plugin",
    "app.plugins.builtin.trade_finder.plugin",
    "app.plugins.builtin.playoff_odds.plugin",
]


class PluginManager:
    def __init__(self, events: EventBus) -> None:
        self.events = events
        self._plugins: dict[str, AnalysisPlugin] = {}

    def register(self, plugin: AnalysisPlugin) -> None:
        self._plugins[plugin.metadata.id] = plugin
        logger.info("registered plugin %s v%s", plugin.metadata.id, plugin.metadata.version)

    def get(self, plugin_id: str) -> AnalysisPlugin:
        if plugin_id not in self._plugins:
            raise KeyError(plugin_id)
        return self._plugins[plugin_id]

    def all(self) -> list[AnalysisPlugin]:
        return list(self._plugins.values())

    def load_builtins(self) -> None:
        for module_name in BUILTIN_MODULES:
            module = importlib.import_module(module_name)
            plugin_cls = getattr(module, "PLUGIN", None)
            if plugin_cls is None:
                # convention: first AnalysisPlugin subclass
                for attr in vars(module).values():
                    if isinstance(attr, type) and attr.__name__.endswith("Plugin") and attr is not AnalysisPlugin:
                        plugin_cls = attr
                        break
            if plugin_cls is None:
                logger.warning("no plugin class in %s", module_name)
                continue
            instance = plugin_cls() if isinstance(plugin_cls, type) else plugin_cls
            self.register(instance)

    def load_entry_points(self) -> None:
        try:
            eps = entry_points(group="otho.plugins")
        except TypeError:  # pragma: no cover - py3.11 compat
            eps = entry_points().get("otho.plugins", [])
        for ep in eps:
            try:
                loaded = ep.load()
                instance = loaded() if isinstance(loaded, type) else loaded
                if instance.metadata.id in self._plugins:
                    continue
                self.register(instance)
            except Exception:
                logger.exception("failed loading entry point %s", ep.name)

    async def startup(self) -> None:
        for plugin in self._plugins.values():
            await plugin.startup()
            for event_type in getattr(plugin, "subscriptions", []) or []:
                self.events.subscribe(event_type, plugin.handle_event)

    async def shutdown(self) -> None:
        for plugin in self._plugins.values():
            await plugin.shutdown()

    async def analyze(self, plugin_id: str, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        plugin = self.get(plugin_id)
        result = await plugin.analyze(context, params)
        result.plugin_id = plugin.metadata.id
        return result

    def tools(self) -> list[AgentTool]:
        tools: list[AgentTool] = []
        for plugin in self._plugins.values():
            tools.extend(plugin.tools())
        return tools

    def plugin_for_tool(self, tool_name: str) -> AnalysisPlugin | None:
        for plugin in self._plugins.values():
            for tool in plugin.tools():
                if tool.name == tool_name:
                    return plugin
        return None
