from pydantic import BaseModel, ConfigDict, Field


class LeagueUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    league_id: str
    display_name: str
    avatar: str | None = None
    is_commissioner: bool = False
    roster_id: int | None = None


class League(BaseModel):
    """Normalized fantasy league. Provider-agnostic."""

    model_config = ConfigDict(from_attributes=True)

    league_id: str
    name: str
    season: str
    sport: str = "nfl"
    status: str = "in_season"
    season_type: str = "regular"
    total_rosters: int = 12
    roster_positions: list[str] = Field(default_factory=list)
    scoring_settings: dict = Field(default_factory=dict)
    settings: dict = Field(default_factory=dict)
    week: int | None = None
    provider: str = "sleeper"
    avatar: str | None = None

    @property
    def starter_slots(self) -> list[str]:
        return [p for p in self.roster_positions if p not in {"BN", "IR", "TAXI"}]

    @property
    def playoff_teams(self) -> int:
        return int(self.settings.get("playoff_teams") or 6)

    @property
    def playoff_week_start(self) -> int:
        return int(self.settings.get("playoff_week_start") or 15)
