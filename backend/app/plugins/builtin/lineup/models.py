from pydantic import BaseModel


class LineupParams(BaseModel):
    roster_id: int | None = None
    week: int | None = None
    player_a: str | None = None
    player_b: str | None = None
