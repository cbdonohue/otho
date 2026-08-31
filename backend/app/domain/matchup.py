from pydantic import BaseModel, ConfigDict, Field


class MatchupSide(BaseModel):
    roster_id: int
    owner_name: str | None = None
    points: float = 0.0
    projected_points: float | None = None
    starters: list[str] = Field(default_factory=list)
    players: list[str] = Field(default_factory=list)
    starter_points: list[float] = Field(default_factory=list)
    player_points: dict[str, float] = Field(default_factory=dict)


class Matchup(BaseModel):
    """One pairing for a week. Two sides when an opponent exists."""

    model_config = ConfigDict(from_attributes=True)

    league_id: str
    week: int
    matchup_id: int | None = None
    home: MatchupSide
    away: MatchupSide | None = None

    @property
    def is_bye(self) -> bool:
        return self.away is None
