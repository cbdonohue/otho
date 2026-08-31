"""In-memory news/injury provider. Swap for a real feed without touching plugins."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain import Injury, Player, PlayerNews


class StubNewsProvider:
    name = "stub"

    def __init__(self) -> None:
        self._news: list[PlayerNews] = []
        self._injuries: dict[str, Injury] = {}

    def seed_from_players(self, players: list[Player]) -> None:
        now = datetime.now(UTC)
        for player in players:
            if not player.injury_status:
                continue
            self._injuries[player.player_id] = Injury(
                player_id=player.player_id,
                status=player.injury_status,
                notes=f"{player.display_name} listed as {player.injury_status}",
                updated_at=now,
                player_name=player.display_name,
            )
            impact = "high" if player.injury_status.lower() in {"out", "ir", "doubtful"} else "medium"
            self._news.append(
                PlayerNews(
                    news_id=f"inj-{player.player_id}",
                    player_id=player.player_id,
                    headline=f"{player.display_name} injury: {player.injury_status}",
                    body=f"Status from league data: {player.injury_status}.",
                    source="sleeper-status",
                    published_at=now,
                    impact=impact,
                )
            )

    async def news(self, player_id: str | None = None) -> list[PlayerNews]:
        if player_id:
            return [n for n in self._news if n.player_id == player_id]
        return list(self._news)

    async def injuries(self, players: list[Player] | None = None) -> list[Injury]:
        if players is None:
            return list(self._injuries.values())
        found: list[Injury] = []
        for player in players:
            if player.player_id in self._injuries:
                found.append(self._injuries[player.player_id])
            elif player.injury_status:
                found.append(
                    Injury(
                        player_id=player.player_id,
                        status=player.injury_status,
                        player_name=player.display_name,
                    )
                )
        return found
