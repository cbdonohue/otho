from app.core.config import Settings
from app.core.events import InProcessEventBus
from app.plugins.manager import PluginManager
from app.services.ask import AskOtho
from tests.fakes import sample_universe


async def test_ask_fallback_runs_plugins():
    ctx, _ = sample_universe()
    manager = PluginManager(InProcessEventBus())
    manager.load_builtins()
    ask = AskOtho(manager, Settings(openai_api_key=""))
    payload = await ask.ask("Who should I start and who is on waivers?", ctx)
    assert payload["mode"] == "plugin-fallback"
    assert payload["tools_used"]
    assert "get_roster" in payload["tools_used"] or "rank_waivers" in payload["tools_used"]
    assert payload["answer"]
    assert payload["widgets"]
