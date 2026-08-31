from pydantic import BaseModel, Field


class TradeParams(BaseModel):
    roster_id: int | None = None
    give: list[str] = Field(default_factory=list)
    receive: list[str] = Field(default_factory=list)
    week: int | None = None
