from pydantic import BaseModel, ConfigDict, Field


class PositionalGrade(BaseModel):
    position: str
    grade: str  # A+ .. F
    score: float
    starter_projection: float
    depth_projection: float
    notes: str = ""


class AnalysisBrief(BaseModel):
    """Decision-oriented summary used by the dashboard and Ask Otho."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    summary: str
    severity: str = "info"  # info | low | medium | high
    actions: list[str] = Field(default_factory=list)
