from pydantic import BaseModel, ConfigDict, Field


class Player(BaseModel):
    """Normalized NFL player. Provider-agnostic."""

    model_config = ConfigDict(from_attributes=True)

    player_id: str
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    team: str | None = None
    status: str | None = None
    injury_status: str | None = None
    number: int | None = None
    age: int | None = None
    years_exp: int | None = None
    depth_chart_order: int | None = None
    search_rank: int | None = None
    sport: str = "nfl"

    @property
    def is_available(self) -> bool:
        return (self.status or "").lower() in {"active", "", "healthy"} and not self.is_out

    @property
    def is_out(self) -> bool:
        status = (self.injury_status or "").lower()
        return status in {"out", "ir", "pup", "suspended", "covid"}

    @property
    def display_name(self) -> str:
        return self.full_name or f"{self.first_name or ''} {self.last_name or ''}".strip() or self.player_id


class TrendingPlayer(BaseModel):
    player_id: str
    count: int
    kind: str = "add"  # add | drop
    player: Player | None = None
