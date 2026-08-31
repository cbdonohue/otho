from app.core.events import PLAYER_INJURY, Event
from app.plugins.builtin.injury_watch.plugin import InjuryWatchPlugin
from tests.fakes import sample_universe


async def test_injury_watch_handles_event_and_analyze():
    ctx, _ = sample_universe()
    plugin = InjuryWatchPlugin()
    await plugin.handle_event(
        Event(type=PLAYER_INJURY, payload={"player_id": "WR4", "status": "Questionable", "name": "Tee Higgins"})
    )
    result = await plugin.analyze(ctx, {"roster_id": 1})
    injured_names = [i["name"] for i in result.data["injured"]]
    assert any("Higgins" in n for n in injured_names)
    assert result.data["recent_events"]
