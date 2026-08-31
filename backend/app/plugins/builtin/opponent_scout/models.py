from pydantic import BaseModel


class ScoutParams(BaseModel):
    roster_id: int | None = None
    week: int | None = None
