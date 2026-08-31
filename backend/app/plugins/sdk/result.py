from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    title: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    widgets: list[dict[str, Any]] = field(default_factory=list)
    plugin_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "data": self.data,
            "widgets": self.widgets,
            "plugin_id": self.plugin_id,
        }
