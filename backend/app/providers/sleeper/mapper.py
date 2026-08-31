"""Map Sleeper JSON → normalized domain models.

This is the ONLY module allowed to know Sleeper's JSON shape.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain import League, LeagueUser, Matchup, MatchupSide, Player, Roster, Transaction


def map_player(player_id: str, raw: dict[str, Any]) -> Player:
    full = raw.get("full_name") or " ".join(
        p for p in (raw.get("first_name"), raw.get("last_name")) if p
    )
    if raw.get("position") == "DEF" or raw.get("fantasy_positions") == ["DEF"]:
        full = full or raw.get("last_name") or raw.get("team") or player_id
    return Player(
        player_id=str(player_id),
        full_name=full or str(player_id),
        first_name=raw.get("first_name"),
        last_name=raw.get("last_name"),
        position=_position(raw),
        team=raw.get("team"),
        status=raw.get("status"),
        injury_status=raw.get("injury_status"),
        number=_int(raw.get("number")),
        age=_int(raw.get("age")),
        years_exp=_int(raw.get("years_exp")),
        depth_chart_order=_int(raw.get("depth_chart_order")),
        search_rank=_int(raw.get("search_rank")),
        sport=raw.get("sport") or "nfl",
    )


def map_players(raw: dict[str, Any]) -> dict[str, Player]:
    out: dict[str, Player] = {}
    for pid, body in raw.items():
        if not isinstance(body, dict):
            continue
        pos = _position(body)
        # Keep skill + IDP-ish relevant fantasy positions; skip coaches/empty.
        if not pos and not body.get("full_name"):
            continue
        out[str(pid)] = map_player(pid, body)
    return out


def map_league(raw: dict[str, Any]) -> League:
    settings = raw.get("settings") or {}
    return League(
        league_id=str(raw["league_id"]),
        name=raw.get("name") or "Unnamed League",
        season=str(raw.get("season") or ""),
        sport=raw.get("sport") or "nfl",
        status=raw.get("status") or "in_season",
        season_type=raw.get("season_type") or "regular",
        total_rosters=int(raw.get("total_rosters") or settings.get("num_teams") or 12),
        roster_positions=list(raw.get("roster_positions") or []),
        scoring_settings=dict(raw.get("scoring_settings") or {}),
        settings=dict(settings),
        provider="sleeper",
        avatar=raw.get("avatar"),
    )


def map_user(raw: dict[str, Any], league_id: str) -> LeagueUser:
    meta = raw.get("metadata") or {}
    return LeagueUser(
        user_id=str(raw["user_id"]),
        league_id=league_id,
        display_name=raw.get("display_name") or raw.get("username") or "Unknown",
        avatar=raw.get("avatar"),
        is_commissioner=bool(raw.get("is_owner")),
        roster_id=None,
    )


def map_roster(raw: dict[str, Any], league_id: str, owner_name: str | None = None) -> Roster:
    settings = raw.get("settings") or {}
    players = [str(p) for p in (raw.get("players") or []) if p]
    starters = [str(p) for p in (raw.get("starters") or []) if p and p != "0"]
    return Roster(
        roster_id=int(raw["roster_id"]),
        league_id=league_id,
        owner_id=str(raw["owner_id"]) if raw.get("owner_id") else None,
        owner_name=owner_name,
        team_name=(raw.get("metadata") or {}).get("team_name") or owner_name,
        wins=int(settings.get("wins") or 0),
        losses=int(settings.get("losses") or 0),
        ties=int(settings.get("ties") or 0),
        points_for=float(settings.get("fpts") or 0) + float(settings.get("fpts_decimal") or 0) / 100.0,
        points_against=float(settings.get("fpts_against") or 0)
        + float(settings.get("fpts_against_decimal") or 0) / 100.0,
        starters=starters,
        players=players,
        taxi=[str(p) for p in (raw.get("taxi") or []) if p],
        reserve=[str(p) for p in (raw.get("reserve") or []) if p],
        waiver_budget_used=int(settings.get("waiver_budget_used") or 0),
        waiver_position=_int(settings.get("waiver_position")),
    )


def map_matchup_sides(
    raw_list: list[dict[str, Any]],
    league_id: str,
    week: int,
    roster_names: dict[int, str] | None = None,
) -> list[Matchup]:
    """Pair Sleeper per-roster matchup rows into home/away Matchup objects."""
    names = roster_names or {}
    by_id: dict[int, list[dict[str, Any]]] = {}
    byes: list[dict[str, Any]] = []
    for row in raw_list:
        mid = row.get("matchup_id")
        if mid is None:
            byes.append(row)
            continue
        by_id.setdefault(int(mid), []).append(row)

    matchups: list[Matchup] = []
    for mid, rows in by_id.items():
        sides = [_side(r, names) for r in rows]
        home = sides[0]
        away = sides[1] if len(sides) > 1 else None
        matchups.append(
            Matchup(league_id=league_id, week=week, matchup_id=mid, home=home, away=away)
        )
    for row in byes:
        matchups.append(
            Matchup(
                league_id=league_id,
                week=week,
                matchup_id=None,
                home=_side(row, names),
                away=None,
            )
        )
    return matchups


def map_transaction(raw: dict[str, Any], league_id: str) -> Transaction:
    created = raw.get("created")
    created_at = None
    if created:
        try:
            created_at = datetime.fromtimestamp(int(created) / 1000, tz=UTC)
        except (TypeError, ValueError, OSError):
            created_at = None
    adds = {str(k): int(v) for k, v in (raw.get("adds") or {}).items()}
    drops = {str(k): int(v) for k, v in (raw.get("drops") or {}).items()}
    return Transaction(
        transaction_id=str(raw.get("transaction_id") or raw.get("type") + str(created)),
        league_id=league_id,
        week=int(raw.get("leg") or raw.get("week") or 0),
        type=str(raw.get("type") or "unknown"),
        status=str(raw.get("status") or "complete"),
        roster_ids=[int(r) for r in (raw.get("roster_ids") or [])],
        adds=adds,
        drops=drops,
        waiver_budget=list(raw.get("waiver_budget") or []),
        created_at=created_at,
        notes=(raw.get("metadata") or {}).get("notes"),
    )


def _side(raw: dict[str, Any], names: dict[int, str]) -> MatchupSide:
    rid = int(raw["roster_id"])
    player_points = raw.get("players_points") or {}
    return MatchupSide(
        roster_id=rid,
        owner_name=names.get(rid),
        points=float(raw.get("points") or 0),
        projected_points=_float(raw.get("custom_points")),
        starters=[str(p) for p in (raw.get("starters") or []) if p and p != "0"],
        players=[str(p) for p in (raw.get("players") or []) if p],
        starter_points=[float(x or 0) for x in (raw.get("starters_points") or [])],
        player_points={str(k): float(v or 0) for k, v in player_points.items()},
    )


def _position(raw: dict[str, Any]) -> str | None:
    pos = raw.get("position")
    if pos:
        return str(pos)
    fantasy = raw.get("fantasy_positions") or []
    return str(fantasy[0]) if fantasy else None


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
