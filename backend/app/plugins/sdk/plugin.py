from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.plugins.sdk.context import AnalysisContext
from app.plugins.sdk.result import AnalysisResult


@dataclass(frozen=True)
class PluginMetadata:
    id: str
    name: str
    description: str
    version: str
    category: str
    icon: str | None = None


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    parameters: dict[str, Any]
    plugin_id: str

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class AnalysisPlugin(ABC):
    """User-invoked analysis. Optionally exposes LLM tools via `tools()`."""

    metadata: PluginMetadata
    subscriptions: list[str] = []

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    @abstractmethod
    async def analyze(self, context: AnalysisContext, params: dict[str, Any]) -> AnalysisResult:
        raise NotImplementedError

    def tools(self) -> list[AgentTool]:
        return []

    async def handle_event(self, event: Any) -> None:
        return None

    async def call_tool(self, name: str, context: AnalysisContext, args: dict[str, Any]) -> AnalysisResult:
        return await self.analyze(context, {**args, "tool": name})


class BackgroundPlugin(AnalysisPlugin):
    """Subscribes to the event bus. `analyze` may still be invoked on demand."""

    subscriptions: list[str] = []
