from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Transaction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    league_id: str
    week: int
    type: str  # waiver | free_agent | trade | commissioner
    status: str
    roster_ids: list[int] = Field(default_factory=list)
    adds: dict[str, int] = Field(default_factory=dict)  # player_id -> roster_id
    drops: dict[str, int] = Field(default_factory=dict)
    waiver_budget: list[dict] = Field(default_factory=list)
    created_at: datetime | None = None
    notes: str | None = None
