"""Provider contracts. Plugins never import these — they use AnalysisContext services."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain import Injury, League, LeagueUser, Matchup, Player, PlayerNews, Projection, Roster, Transaction


class FantasyDataProvider(Protocol):
    name: str

    async def get_nfl_state(self) -> dict[str, Any]: ...
    async def get_players(self) -> dict[str, Player]: ...
    async def get_league(self, league_id: str) -> League: ...
    async def get_users(self, league_id: str) -> list[LeagueUser]: ...
    async def get_rosters(self, league_id: str) -> list[Roster]: ...
    async def get_matchups(self, league_id: str, week: int) -> list[Matchup]: ...
    async def get_transactions(self, league_id: str, week: int) -> list[Transaction]: ...
    async def get_trending(self, kind: str = "add") -> list[dict[str, Any]]: ...


class ProjectionProvider(Protocol):
    name: str

    async def projections(
        self, players: list[Player], week: int, season: str
    ) -> dict[str, Projection]: ...


class NewsProvider(Protocol):
    name: str

    async def news(self, player_id: str | None = None) -> list[PlayerNews]: ...
    async def injuries(self, players: list[Player] | None = None) -> list[Injury]: ...


class StatsProvider(Protocol):
    name: str

    async def weekly_stats(self, player_id: str, week: int, season: str) -> dict[str, Any]: ...
