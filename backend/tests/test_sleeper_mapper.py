from app.providers.sleeper.mapper import map_league, map_matchup_sides, map_player, map_roster, map_transaction


def test_map_player_skill():
    raw = {
        "full_name": "Patrick Mahomes",
        "first_name": "Patrick",
        "last_name": "Mahomes",
        "position": "QB",
        "team": "KC",
        "status": "Active",
        "injury_status": None,
        "number": 15,
        "search_rank": 8,
        "depth_chart_order": 1,
        "years_exp": 8,
    }
    player = map_player("4046", raw)
    assert player.player_id == "4046"
    assert player.position == "QB"
    assert player.team == "KC"
    assert player.search_rank == 8
    assert "Sleeper" not in player.model_dump_json()


def test_map_league_settings():
    raw = {
        "league_id": "123",
        "name": "The Gauntlet",
        "season": "2025",
        "status": "in_season",
        "total_rosters": 12,
        "roster_positions": ["QB", "RB", "WR", "TE", "FLEX", "BN"],
        "scoring_settings": {"rec": 1.0},
        "settings": {"playoff_teams": 6, "playoff_week_start": 15},
    }
    league = map_league(raw)
    assert league.provider == "sleeper"
    assert league.playoff_teams == 6
    assert "QB" in league.starter_slots
    assert "BN" not in league.starter_slots


def test_map_roster_points():
    raw = {
        "roster_id": 4,
        "owner_id": "u1",
        "players": ["1", "2"],
        "starters": ["1", "0"],
        "settings": {"wins": 3, "losses": 1, "fpts": 412, "fpts_decimal": 50},
        "metadata": {"team_name": "Ops"},
    }
    roster = map_roster(raw, "123", owner_name="Ada")
    assert roster.roster_id == 4
    assert roster.starters == ["1"]
    assert roster.points_for == 412.5
    assert roster.owner_name == "Ada"


def test_map_matchups_pair():
    raw = [
        {"roster_id": 1, "matchup_id": 3, "points": 110.2, "starters": ["a"], "players": ["a"]},
        {"roster_id": 2, "matchup_id": 3, "points": 99.0, "starters": ["b"], "players": ["b"]},
    ]
    matchups = map_matchup_sides(raw, "L", 8, {1: "You", 2: "Them"})
    assert len(matchups) == 1
    assert matchups[0].home.roster_id == 1
    assert matchups[0].away.roster_id == 2
    assert matchups[0].home.owner_name == "You"


def test_map_transaction_unix_ms():
    raw = {
        "transaction_id": "tx9",
        "type": "trade",
        "status": "complete",
        "leg": 7,
        "roster_ids": [1, 2],
        "adds": {"111": 2},
        "drops": {"222": 1},
        "created": 1_700_000_000_000,
    }
    tx = map_transaction(raw, "L")
    assert tx.type == "trade"
    assert tx.adds["111"] == 2
    assert tx.created_at is not None
