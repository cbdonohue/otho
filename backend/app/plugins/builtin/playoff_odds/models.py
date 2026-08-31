from pydantic import BaseModel, Field


class OddsParams(BaseModel):
    roster_id: int | None = None
    iterations: int = Field(default=2500, ge=200, le=10000)
