from app.plugins.builtin.lineup.plugin import LineupPlugin
from app.plugins.builtin.waiver_wire.plugin import WaiverWirePlugin
from tests.fakes import sample_universe


async def test_lineup_flags_warren_over_white():
    ctx, players = sample_universe()
    result = await LineupPlugin().analyze(ctx, {"roster_id": 1})
    assert "swaps" in result.data
    # RB4 (White, worse rank) is starting over RB2/RB3 — expect a sit/start rec
    assert result.data["optimal_total"] >= result.data["current_total"] - 0.5
    recs = [w for w in result.widgets if w["type"] == "recommendation"]
    assert recs


async def test_waiver_ranks_available():
    ctx, _ = sample_universe()
    result = await WaiverWirePlugin().analyze(ctx, {"roster_id": 1, "limit": 8})
    assert result.data["targets"]
    assert result.data["targets"][0]["name"]
    types = {w["type"] for w in result.widgets}
    assert "ranking" in types
