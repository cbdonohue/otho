"""Shared fakes for plugin tests. No network, no database."""

from __future__ import annotations

from app.core.cache import InMemoryCache
from app.core.events import InProcessEventBus
from app.domain import Injury, League, Matchup, MatchupSide, Player, PlayerNews, Projection, Roster, Transaction, TrendingPlayer
from app.plugins.sdk.context import AnalysisContext
from app.providers.projections.heuristic import HeuristicProjectionProvider


def player(pid, name, pos, team="KC", rank=20, inj=None) -> Player:
    first, _, last = name.partition(" ")
    return Player(
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


class FakeLeagueService:
    def __init__(self, league: League, rosters: list[Roster], matchups: list[Matchup], txs: list[Transaction] | None = None):
        self.league = league
        self.rosters = rosters
        self.matchups = matchups
        self.txs = txs or []

    async def get_league(self, league_id: str) -> League:
        return self.league

    async def get_rosters(self, league_id: str) -> list[Roster]:
        return self.rosters

    async def get_roster(self, league_id: str, roster_id: int) -> Roster:
        return next(r for r in self.rosters if r.roster_id == roster_id)

    async def get_matchups(self, league_id: str, week: int) -> list[Matchup]:
        return self.matchups

    async def get_transactions(self, league_id: str, week: int | None = None) -> list[Transaction]:
        return self.txs

    async def get_users(self, league_id: str):
        return []

    async def get_nfl_state(self):
        return {"week": 8, "season": "2025"}


class FakePlayerService:
    def __init__(self, players: dict[str, Player], available: list[Player] | None = None):
        self.players = players
        self._available = available or []

    async def get_player(self, player_id: str):
        return self.players.get(player_id)

    async def get_players(self, player_ids: list[str]) -> dict[str, Player]:
        return {pid: self.players[pid] for pid in player_ids if pid in self.players}

    async def search(self, query: str, limit: int = 20):
        q = query.lower()
        return [p for p in self.players.values() if q in p.full_name.lower()][:limit]

    async def available(self, league_id: str, positions=None):
        if positions:
            return [p for p in self._available if p.position in positions]
        return list(self._available)

    async def trending(self, kind: str = "add"):
        return [TrendingPlayer(player_id=p.player_id, count=40, kind=kind) for p in self._available[:3]]


class FakeProjectionService:
    def __init__(self):
        self.provider = HeuristicProjectionProvider()

    async def get_projections(self, player_ids, week, season):
        # caller should pass players via a side channel — we rebuild from ids if we have them
        return {}

    async def get_projection(self, player_id, week, season):
        return None


class Projecting(FakeProjectionService):
    def __init__(self, players: dict[str, Player]):
        super().__init__()
        self.players = players

    async def get_projections(self, player_ids, week, season):
        plist = [self.players[pid] for pid in player_ids if pid in self.players]
        return await self.provider.projections(plist, week, season)

    async def get_projection(self, player_id, week, season):
        found = await self.get_projections([player_id], week, season)
        return found.get(player_id)


class FakeNews:
    async def get_news(self, player_id=None):
        return []

    async def get_injuries(self, player_ids=None):
        return []


def sample_universe():
    players = {
        "QB1": player("QB1", "Patrick Mahomes", "QB", "KC", 5),
        "QB2": player("QB2", "Jared Goff", "QB", "DET", 40),
        "RB1": player("RB1", "Breece Hall", "RB", "NYJ", 18),
        "RB2": player("RB2", "James Cook", "RB", "BUF", 35),
        "RB3": player("RB3", "Jaylen Warren", "RB", "PIT", 55),
        "RB4": player("RB4", "Rachaad White", "RB", "TB", 90),
        "WR1": player("WR1", "Justin Jefferson", "WR", "MIN", 3),
        "WR2": player("WR2", "Amon-Ra St. Brown", "WR", "DET", 12),
        "WR3": player("WR3", "DK Metcalf", "WR", "SEA", 28),
        "WR4": player("WR4", "Tee Higgins", "WR", "CIN", 32, "Questionable"),
        "WR5": player("WR5", "Courtland Sutton", "WR", "DEN", 60),
        "TE1": player("TE1", "Travis Kelce", "TE", "KC", 22),
        "TE2": player("TE2", "Evan Engram", "TE", "JAX", 80),
        "K1": player("K1", "Harrison Butker", "K", "KC", 90),
        "DEF1": player("DEF1", "Bills DEF", "DEF", "BUF", 80),
        "FA1": player("FA1", "Rico Dowdle", "RB", "DAL", 100),
        "FA2": player("FA2", "Wan'Dale Robinson", "WR", "NYG", 95),
    }
    you_starters = ["QB1", "RB1", "RB4", "WR1", "WR2", "WR3", "TE1", "WR4", "K1", "DEF1"]
    you_players = you_starters + ["RB2", "RB3", "WR5", "TE2"]
    opp_starters = ["QB2", "RB2", "FA1", "WR5", "FA2", "WR4", "TE2", "WR3", "K1", "DEF1"]
    league = League(
        league_id="L1",
        name="Test",
        season="2025",
        week=8,
        roster_positions=["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN"],
        settings={"playoff_teams": 6, "playoff_week_start": 15},
        total_rosters=2,
    )
    you = Roster(
        roster_id=1,
        league_id="L1",
        owner_name="You",
        wins=5,
        losses=2,
        points_for=980,
        starters=you_starters,
        players=you_players,
    )
    opp = Roster(
        roster_id=2,
        league_id="L1",
        owner_name="Rival",
        wins=4,
        losses=3,
        points_for=900,
        starters=opp_starters,
        players=opp_starters,
    )
    matchup = Matchup(
        league_id="L1",
        week=8,
        matchup_id=1,
        home=MatchupSide(roster_id=1, owner_name="You", starters=you_starters, points=10),
        away=MatchupSide(roster_id=2, owner_name="Rival", starters=opp_starters, points=8),
    )
    txs = [
        Transaction(
            transaction_id="t1",
            league_id="L1",
            week=8,
            type="waiver",
            status="complete",
            roster_ids=[1],
            adds={"FA1": 1},
            drops={"RB4": 1},
        )
    ]
    available = [players["FA1"], players["FA2"], player("FA3", "Bo Nix", "QB", "DEN", 70)]
    ctx = AnalysisContext(
        league_id="L1",
        roster_id=1,
        week=8,
        season="2025",
        league_service=FakeLeagueService(league, [you, opp], [matchup], txs),
        player_service=FakePlayerService(players, available),
        projection_service=Projecting(players),
        news_service=FakeNews(),
        cache=InMemoryCache(),
        events=InProcessEventBus(),
    )
    return ctx, players
