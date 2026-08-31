from app.domain import Player
from app.providers.projections.heuristic import HeuristicProjectionProvider


async def test_out_player_projects_zero():
    provider = HeuristicProjectionProvider()
    healthy = Player(player_id="1", full_name="Star", position="RB", team="KC", search_rank=10)
    out = Player(player_id="2", full_name="Hurt", position="RB", team="KC", search_rank=10, injury_status="Out")
    result = await provider.projections([healthy, out], 8, "2025")
    assert result["1"].points > 10
    assert result["2"].points == 0
    assert result["1"].source == "otho.heuristic"
