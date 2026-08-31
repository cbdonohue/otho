from pydantic import BaseModel


class ActivityParams(BaseModel):
    week: int | None = None
    limit: int = 20
