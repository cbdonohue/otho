from pydantic import BaseModel


class HealthParams(BaseModel):
    roster_id: int | None = None
    week: int | None = None
