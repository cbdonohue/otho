from app.plugins.builtin.matchup.plugin import MatchupSimulatorPlugin
from tests.fakes import sample_universe


async def test_matchup_analyze_returns_win_probability():
    ctx, _ = sample_universe()
    plugin = MatchupSimulatorPlugin()
    result = await plugin.analyze(ctx, {"roster_id": 1, "week": 8, "iterations": 800})
    assert result.title
    assert "win_probability" in result.data
    wp = result.data["win_probability"]
    assert 0.0 <= wp <= 1.0
    types = {w["type"] for w in result.widgets}
    assert "matchup" in types
    assert "metric" in types
    assert "recommendation" in types
    # Jaylen Warren is on the roster but not a starter — still a real analysis payload
    assert result.data["home"]["mean"] > 0
    assert result.data["away"]["mean"] > 0
