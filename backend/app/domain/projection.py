from pydantic import BaseModel, ConfigDict


class Projection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    week: int
    season: str
    points: float
    floor: float | None = None
    ceiling: float | None = None
    source: str = "otho.heuristic"
    position: str | None = None
