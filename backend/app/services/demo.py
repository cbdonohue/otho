from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import (
    LeagueRow,
    LeagueUserRow,
    MatchupRow,
    PlayerRow,
    RosterRow,
    TransactionRow,
)
PLAYERS = [
    ("QB1", "Patrick Mahomes", "QB", "KC", 5, None),
    ("QB2", "Jared Goff", "QB", "DET", 40, None),
    ("RB1", "Breece Hall", "RB", "NYJ", 18, None),
    ("RB2", "James Cook", "RB", "BUF", 35, None),
    ("RB3", "Jaylen Warren", "RB", "PIT", 55, None),
    ("RB4", "Rachaad White", "RB", "TB", 70, None),
    ("WR1", "Justin Jefferson", "WR", "MIN", 3, None),
    ("WR2", "Amon-Ra St. Brown", "WR", "DET", 12, None),
    ("WR3", "DK Metcalf", "WR", "SEA", 28, None),
    ("WR4", "Tee Higgins", "WR", "CIN", 32, "Questionable"),
    ("WR5", "Courtland Sutton", "WR", "DEN", 60, None),
    ("TE1", "Travis Kelce", "TE", "KC", 22, None),
    ("TE2", "Evan Engram", "TE", "JAX", 48, None),
    ("K1", "Harrison Butker", "K", "KC", 90, None),
    ("DEF1", "Bills DEF", "DEF", "BUF", 80, None),
    ("QB3", "Bo Nix", "QB", "DEN", 75, None),
    ("RB5", "Rico Dowdle", "RB", "DAL", 110, None),
    ("WR6", "Wan'Dale Robinson", "WR", "NYG", 95, None),
    ("WR7", "Rome Odunze", "WR", "CHI", 85, None),
    ("TE3", "Pat Freiermuth", "TE", "PIT", 120, None),
    ("FA1", "Javonte Williams", "RB", "DEN", 88, None),
    ("FA2", "Josh Downs", "WR", "IND", 92, None),
    ("FA3", "Tyler Allgeier", "RB", "ATL", 105, None),
    ("FA4", "Romeo Doubs", "WR", "GB", 98, None),
    ("FA5", "Sam Darnold", "QB", "MIN", 72, None),
]


async def seed_demo_league(session: AsyncSession, league_id: str = "demo") -> str:
    for pid, name, pos, team, rank, inj in PLAYERS:
        existing = await session.get(PlayerRow, pid)
        if existing:
            continue
        first, _, last = name.partition(" ")
        session.add(
            PlayerRow(
                player_id=pid,
                full_name=name,
                first_name=first,
                last_name=last or first,
                position=pos,
                team=team,
                status="Active",
                injury_status=inj,
                search_rank=rank,
                depth_chart_order=1,
                years_exp=4,
            )
        )
    existing = await session.get(LeagueRow, league_id)
    if existing:
        await session.commit()
        return league_id
    session.add(
        LeagueRow(
            league_id=league_id,
            name="Otho Demo League",
            season="2025",
            roster_positions=["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN", "BN", "BN", "BN", "BN"],
            scoring_settings={"rec": 1.0, "pass_td": 4},
            settings={"playoff_teams": 6, "playoff_week_start": 15},
            week=8,
            total_rosters=2,
        )
    )
    you_starters = ["QB1", "RB1", "RB2", "WR1", "WR2", "WR3", "TE1", "WR4", "K1", "DEF1"]
    you_players = you_starters + ["RB3", "WR5", "TE2"]
    opp_starters = ["QB2", "RB4", "RB5", "WR5", "WR6", "WR7", "TE2", "TE3", "K1", "DEF1"]
    opp_players = opp_starters + ["QB3"]
    session.add(
        RosterRow(
            league_id=league_id,
            roster_id=1,
            owner_id="u1",
            owner_name="You",
            team_name="The Operators",
            wins=5,
            losses=2,
            points_for=980,
            points_against=870,
            starters=you_starters,
            players=you_players,
        )
    )
    session.add(
        RosterRow(
            league_id=league_id,
            roster_id=2,
            owner_id="u2",
            owner_name="Rival GM",
            team_name="Chaos Theory",
            wins=4,
            losses=3,
            points_for=910,
            points_against=900,
            starters=opp_starters,
            players=opp_players,
        )
    )
    session.add(LeagueUserRow(user_id="u1", league_id=league_id, display_name="You", roster_id=1, is_commissioner=True))
    session.add(LeagueUserRow(user_id="u2", league_id=league_id, display_name="Rival GM", roster_id=2))
    session.add(
        MatchupRow(
            league_id=league_id,
            week=8,
            matchup_id=1,
            roster_id=1,
            opponent_roster_id=2,
            points=42.3,
            starters=you_starters,
            players=you_players,
        )
    )
    session.add(
        MatchupRow(
            league_id=league_id,
            week=8,
            matchup_id=1,
            roster_id=2,
            opponent_roster_id=1,
            points=38.1,
            starters=opp_starters,
            players=opp_players,
        )
    )
    session.add(
        TransactionRow(
            transaction_id="tx1",
            league_id=league_id,
            week=8,
            type="waiver",
            status="complete",
            roster_ids=[1],
            adds={"RB3": 1},
            drops={"RB4": 1},
            created_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return league_id
