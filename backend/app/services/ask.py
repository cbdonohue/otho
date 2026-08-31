from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.plugins.manager import PluginManager
from app.plugins.sdk.context import AnalysisContext
from app.plugins.sdk.result import AnalysisResult

logger = logging.getLogger("otho.ask")

KEYWORD_TOOLS: list[tuple[tuple[str, ...], str]] = [
    (("start", "sit", "lineup", "bench"), "get_roster"),
    (("compare", " or "), "compare_players"),
    (("waiver", "claim", "pickup", "drop", "available"), "rank_waivers"),
    (("trade", "deal", "offer"), "find_trade_targets"),
    (("matchup", "win", "opponent", "this week"), "simulate_matchup"),
    (("playoff", "odds", "seed"), "calculate_playoff_odds"),
    (("weak", "hole", "depth", "grade"), "find_roster_weaknesses"),
    (("injury", "hurt", "out", "questionable"), "injury_report"),
    (("pulse", "transaction", "waiver wire news", "activity"), "league_pulse"),
    (("scout",), "scout_opponent"),
]


class AskOtho:
    def __init__(self, manager: PluginManager, settings: Settings) -> None:
        self.manager = manager
        self.settings = settings

    async def ask(self, question: str, context: AnalysisContext) -> dict[str, Any]:
        if self.settings.has_openai:
            try:
                return await self._llm_ask(question, context)
            except Exception:
                logger.exception("LLM ask failed; using plugin fallback")
        return await self._fallback_ask(question, context)

    async def _fallback_ask(self, question: str, context: AnalysisContext) -> dict[str, Any]:
        q = question.lower()
        tool_names: list[str] = []
        for keys, tool in KEYWORD_TOOLS:
            if any(k in q for k in keys):
                tool_names.append(tool)
        if not tool_names:
            tool_names = ["simulate_matchup", "get_roster", "rank_waivers", "find_roster_weaknesses"]
        # de-dupe preserving order
        seen: set[str] = set()
        ordered = []
        for name in tool_names:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        results: list[AnalysisResult] = []
        used = []
        for name in ordered[:4]:
            plugin = self.manager.plugin_for_tool(name)
            if not plugin:
                continue
            result = await plugin.call_tool(name, context, {"tool": name, "roster_id": context.roster_id})
            result.plugin_id = plugin.metadata.id
            results.append(result)
            used.append(name)
        answer = self._synthesize(question, results)
        widgets: list[dict[str, Any]] = []
        for result in results:
            widgets.extend(result.widgets)
        return {
            "answer": answer,
            "mode": "plugin-fallback",
            "tools_used": used,
            "results": [r.to_dict() for r in results],
            "widgets": widgets[:20],
        }

    def _synthesize(self, question: str, results: list[AnalysisResult]) -> str:
        if not results:
            return "I don't have plugin output yet. Add a Sleeper league and ask again."
        parts = [f"Ask Otho read {len(results)} plugin(s) for: {question.strip()}"]
        for result in results:
            parts.append(f"**{result.title}** — {result.summary}")
        parts.append("Numbers come from plugins (projections + league state), not from me guessing.")
        return "\n\n".join(parts)

    async def _llm_ask(self, question: str, context: AnalysisContext) -> dict[str, Any]:
        tools = [t.openai_schema() for t in self.manager.tools()]
        system = (
            "You are Otho, a fantasy-football analysis OS. "
            "You MUST call plugins via tools for any league facts, rankings, or recommendations. "
            "Never invent projections or roster data. After tools return, answer concisely."
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"League {context.league_id}, roster {context.roster_id}, week {context.week}.\n"
                    f"Question: {question}"
                ),
            },
        ]
        used: list[str] = []
        widgets: list[dict[str, Any]] = []
        plugin_results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=45.0) as client:
            for _ in range(4):
                payload = {
                    "model": self.settings.openai_model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                }
                response = await client.post(
                    f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                choice = response.json()["choices"][0]["message"]
                messages.append(choice)
                calls = choice.get("tool_calls") or []
                if not calls:
                    return {
                        "answer": choice.get("content") or "",
                        "mode": "llm",
                        "tools_used": used,
                        "results": plugin_results,
                        "widgets": widgets[:20],
                    }
                for call in calls:
                    name = call["function"]["name"]
                    try:
                        args = json.loads(call["function"].get("arguments") or "{}")
                    except Exception:
                        args = {}
                    plugin = self.manager.plugin_for_tool(name)
                    if not plugin:
                        tool_content = f"unknown tool {name}"
                    else:
                        result = await plugin.call_tool(name, context, {**args, "tool": name})
                        result.plugin_id = plugin.metadata.id
                        used.append(name)
                        widgets.extend(result.widgets)
                        plugin_results.append(result.to_dict())
                        tool_content = result.summary + "\n" + json.dumps(result.data)[:4000]
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": tool_content,
                        }
                    )
        return {
            "answer": "I ran plugins but the model did not produce a final answer.",
            "mode": "llm",
            "tools_used": used,
            "results": plugin_results,
            "widgets": widgets[:20],
        }
