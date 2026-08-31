from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlayerNews(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    news_id: str
    player_id: str
    headline: str
    body: str | None = None
    source: str = "stub"
    published_at: datetime | None = None
    impact: str | None = None  # high | medium | low
