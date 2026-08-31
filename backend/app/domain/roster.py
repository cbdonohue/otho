from pydantic import BaseModel, ConfigDict, Field


class RosterPlayer(BaseModel):
    player_id: str
    slot: str | None = None  # starter slot name or BN/IR
    is_starter: bool = False


class Roster(BaseModel):
    """Normalized team roster. Provider-agnostic."""

    model_config = ConfigDict(from_attributes=True)

    roster_id: int
    league_id: str
    owner_id: str | None = None
    owner_name: str | None = None
    team_name: str | None = None
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    starters: list[str] = Field(default_factory=list)
    players: list[str] = Field(default_factory=list)
    taxi: list[str] = Field(default_factory=list)
    reserve: list[str] = Field(default_factory=list)
    waiver_budget_used: int = 0
    waiver_position: int | None = None

    @property
    def bench(self) -> list[str]:
        starter_set = set(self.starters)
        reserved = set(self.reserve) | set(self.taxi)
        return [p for p in self.players if p not in starter_set and p not in reserved]

    @property
    def record(self) -> str:
        if self.ties:
            return f"{self.wins}-{self.losses}-{self.ties}"
        return f"{self.wins}-{self.losses}"

    @property
    def games_played(self) -> int:
        return self.wins + self.losses + self.ties
