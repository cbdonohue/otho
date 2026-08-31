from app.core.events import LEAGUE_SYNCED, InProcessEventBus, Event
from app.plugins.manager import PluginManager
from app.plugins.sdk import AnalysisPlugin, AnalysisResult, PluginMetadata


class DummyPlugin(AnalysisPlugin):
    metadata = PluginMetadata(id="dummy", name="Dummy", description="d", version="0", category="test")

    async def analyze(self, context, params):
        return AnalysisResult(title="ok", summary="ok", data=params)


async def test_manager_register_and_analyze():
    bus = InProcessEventBus()
    manager = PluginManager(bus)
    manager.register(DummyPlugin())
    result = await manager.analyze("dummy", context=None, params={"a": 1})  # type: ignore[arg-type]
    assert result.title == "ok"
    assert result.plugin_id == "dummy"
    assert result.data["a"] == 1


def test_load_builtins():
    bus = InProcessEventBus()
    manager = PluginManager(bus)
    manager.load_builtins()
    ids = {p.metadata.id for p in manager.all()}
    assert {
        "matchup",
        "lineup",
        "waiver_wire",
        "roster_health",
        "opponent_scout",
        "league_activity",
        "injury_watch",
        "trade_finder",
        "playoff_odds",
    } <= ids
    tools = {t.name for t in manager.tools()}
    assert "simulate_matchup" in tools
    assert "rank_waivers" in tools
    assert "calculate_playoff_odds" in tools


async def test_event_bus_delivers():
    bus = InProcessEventBus()
    seen = []

    async def handler(event: Event):
        seen.append(event.type)

    bus.subscribe(LEAGUE_SYNCED, handler)
    await bus.publish(Event(type=LEAGUE_SYNCED, league_id="L", payload={"ok": True}))
    assert seen == [LEAGUE_SYNCED]
