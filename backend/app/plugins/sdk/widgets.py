"""Generic dashboard widgets. Plugins return these; the frontend renders them."""

from __future__ import annotations

from typing import Any

WIDGET_TYPES = (
    "player_card",
    "player_table",
    "metric",
    "chart",
    "ranking",
    "alert",
    "timeline",
    "matchup",
    "recommendation",
    "comparison",
    "markdown",
)


def player_card(
    player_id: str,
    name: str,
    *,
    position: str | None = None,
    team: str | None = None,
    projection: float | None = None,
    points: float | None = None,
    subtitle: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "type": "player_card",
        "player_id": player_id,
        "name": name,
        "position": position,
        "team": team,
        "projection": projection,
        "points": points,
        "subtitle": subtitle,
        **extra,
    }


def player_table(columns: list[str], rows: list[dict[str, Any]], title: str | None = None) -> dict[str, Any]:
    return {"type": "player_table", "columns": columns, "rows": rows, "title": title}


def metric(label: str, value: Any, *, delta: Any = None, hint: str | None = None, **extra: Any) -> dict[str, Any]:
    return {"type": "metric", "label": label, "value": value, "delta": delta, "hint": hint, **extra}


def chart(
    chart_type: str,
    labels: list[str],
    series: list[dict[str, Any]],
    title: str | None = None,
) -> dict[str, Any]:
    return {"type": "chart", "chart_type": chart_type, "labels": labels, "series": series, "title": title}


def ranking(items: list[dict[str, Any]], title: str | None = None) -> dict[str, Any]:
    return {"type": "ranking", "items": items, "title": title}


def alert(title: str, body: str, *, severity: str = "info", **extra: Any) -> dict[str, Any]:
    return {"type": "alert", "title": title, "body": body, "severity": severity, **extra}


def timeline(events: list[dict[str, Any]], title: str | None = None) -> dict[str, Any]:
    return {"type": "timeline", "events": events, "title": title}


def matchup(
    home: dict[str, Any],
    away: dict[str, Any] | None,
    *,
    week: int | None = None,
    win_probability: float | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "type": "matchup",
        "home": home,
        "away": away,
        "week": week,
        "win_probability": win_probability,
        **extra,
    }


def recommendation(
    title: str,
    subtitle: str,
    *,
    severity: str = "medium",
    confidence: float | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "type": "recommendation",
        "severity": severity,
        "title": title,
        "subtitle": subtitle,
        "confidence": confidence,
        **extra,
    }


def comparison(left: dict[str, Any], right: dict[str, Any], title: str | None = None) -> dict[str, Any]:
    return {"type": "comparison", "left": left, "right": right, "title": title}


def markdown(content: str, title: str | None = None) -> dict[str, Any]:
    return {"type": "markdown", "content": content, "title": title}
