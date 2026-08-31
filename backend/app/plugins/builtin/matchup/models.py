from pydantic import BaseModel, Field


class MatchupSimParams(BaseModel):
    roster_id: int | None = None
    week: int | None = None
    iterations: int = Field(default=4000, ge=200, le=20000)


class SideResult(BaseModel):
    roster_id: int
    name: str
    mean: float
    p10: float
    p90: float
    starters: list[dict]
