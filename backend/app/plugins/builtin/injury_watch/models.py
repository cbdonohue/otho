from pydantic import BaseModel


class InjuryParams(BaseModel):
    roster_id: int | None = None
