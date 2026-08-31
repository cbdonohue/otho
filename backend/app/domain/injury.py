from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Injury(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    status: str  # Out | Doubtful | Questionable | IR | PUP | Healthy
    body_part: str | None = None
    practice_status: str | None = None
    notes: str | None = None
    updated_at: datetime | None = None
    player_name: str | None = None
