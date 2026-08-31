from __future__ import annotations

from app.domain import Injury, Player, PlayerNews
from app.providers.news.stub import StubNewsProvider


class NewsService:
    def __init__(self, provider: StubNewsProvider | None = None) -> None:
        self.provider = provider or StubNewsProvider()

    def seed(self, players: list[Player]) -> None:
        self.provider.seed_from_players(players)

    async def get_news(self, player_id: str | None = None) -> list[PlayerNews]:
        return await self.provider.news(player_id)

    async def get_injuries(self, player_ids: list[str] | None = None) -> list[Injury]:
        if player_ids is None:
            return await self.provider.injuries()
        # Provider accepts Player list; synthesize thin Player objects
        thin = [Player(player_id=pid, full_name=pid) for pid in player_ids]
        return await self.provider.injuries(thin)
