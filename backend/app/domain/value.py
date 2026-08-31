from pydantic import BaseModel, ConfigDict


class PlayerValue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    league_id: str
    week: int
    projection: float
    rest_of_season: float | None = None
    trade_value: float | None = None
    waiver_rank: int | None = None
    positional_rank: int | None = None
