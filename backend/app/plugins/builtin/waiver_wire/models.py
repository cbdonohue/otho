from pydantic import BaseModel, Field


class WaiverParams(BaseModel):
    roster_id: int | None = None
    week: int | None = None
    limit: int = Field(default=12, ge=3, le=40)
    position: str | None = None
