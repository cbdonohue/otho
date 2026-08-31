"""Persist and read normalized league state. Never exposes Sleeper JSON."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import LeagueRow, LeagueUserRow, MatchupRow, RosterRow, TransactionRow
from app.domain import League, LeagueUser, Matchup, MatchupSide, Roster, Transaction


class LeagueService:
    def __init__(self, session: AsyncSession, nfl_state: dict[str, Any] | None = None) -> None:
        self.session = session
        self._nfl_state = nfl_state or {}

    def set_nfl_state(self, state: dict[str, Any]) -> None:
        self._nfl_state = state

    async def get_nfl_state(self) -> dict[str, Any]:
        return dict(self._nfl_state)

    async def list_leagues(self) -> list[League]:
        rows = (await self.session.execute(select(LeagueRow))).scalars().all()
        return [self._league(r) for r in rows]

    async def get_league(self, league_id: str) -> League:
        row = await self.session.get(LeagueRow, league_id)
        if row is None:
            raise KeyError(f"league {league_id} not found")
        return self._league(row)

    async def upsert_league(self, league: League) -> None:
        row = await self.session.get(LeagueRow, league.league_id)
        data = league.model_dump()
        if row is None:
            self.session.add(LeagueRow(**data))
        else:
            for key, value in data.items():
                setattr(row, key, value)
        await self.session.flush()

    async def get_users(self, league_id: str) -> list[LeagueUser]:
        rows = (
            (
                await self.session.execute(
                    select(LeagueUserRow).where(LeagueUserRow.league_id == league_id)
                )
            )
            .scalars()
            .all()
        )
        return [
            LeagueUser(
                user_id=r.user_id,
                league_id=r.league_id,
                display_name=r.display_name,
                avatar=r.avatar,
                is_commissioner=r.is_commissioner,
                roster_id=r.roster_id,
            )
            for r in rows
        ]

    async def replace_users(self, league_id: str, users: list[LeagueUser]) -> None:
        existing = (
            (
                await self.session.execute(
                    select(LeagueUserRow).where(LeagueUserRow.league_id == league_id)
                )
            )
            .scalars()
            .all()
        )
        for row in existing:
            await self.session.delete(row)
        for user in users:
            self.session.add(
                LeagueUserRow(
                    user_id=user.user_id,
                    league_id=user.league_id,
                    display_name=user.display_name,
                    avatar=user.avatar,
                    is_commissioner=user.is_commissioner,
                    roster_id=user.roster_id,
                )
            )
        await self.session.flush()

    async def get_rosters(self, league_id: str) -> list[Roster]:
        rows = (
            (await self.session.execute(select(RosterRow).where(RosterRow.league_id == league_id)))
            .scalars()
            .all()
        )
        return [self._roster(r) for r in rows]

    async def get_roster(self, league_id: str, roster_id: int) -> Roster:
        row = await self.session.get(RosterRow, {"league_id": league_id, "roster_id": roster_id})
        if row is None:
            raise KeyError(f"roster {roster_id} not found in {league_id}")
        return self._roster(row)

    async def upsert_rosters(self, league_id: str, rosters: list[Roster]) -> None:
        for roster in rosters:
            row = await self.session.get(
                RosterRow, {"league_id": league_id, "roster_id": roster.roster_id}
            )
            data = roster.model_dump()
            if row is None:
                self.session.add(RosterRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
        await self.session.flush()

    async def get_matchups(self, league_id: str, week: int) -> list[Matchup]:
        rows = (
            (
                await self.session.execute(
                    select(MatchupRow).where(MatchupRow.league_id == league_id, MatchupRow.week == week)
                )
            )
            .scalars()
            .all()
        )
        grouped: dict[tuple[int | None, ...], list[MatchupRow]] = {}
        for row in rows:
            key = (row.matchup_id,)
            grouped.setdefault(key, []).append(row)
        matchups: list[Matchup] = []
        seen_pairs: set[tuple[int, int | None]] = set()
        for group in grouped.values():
            if group[0].matchup_id is None:
                for row in group:
                    matchups.append(
                        Matchup(
                            league_id=league_id,
                            week=week,
                            matchup_id=None,
                            home=self._side(row),
                            away=None,
                        )
                    )
                continue
            by_roster = {r.roster_id: r for r in group}
            for row in group:
                pair = tuple(sorted((row.roster_id, row.opponent_roster_id or -1)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                away_row = by_roster.get(row.opponent_roster_id) if row.opponent_roster_id else None
                matchups.append(
                    Matchup(
                        league_id=league_id,
                        week=week,
                        matchup_id=row.matchup_id,
                        home=self._side(row),
                        away=self._side(away_row) if away_row else None,
                    )
                )
        return matchups

    async def replace_matchups(self, league_id: str, week: int, matchups: list[Matchup]) -> None:
        existing = (
            (
                await self.session.execute(
                    select(MatchupRow).where(MatchupRow.league_id == league_id, MatchupRow.week == week)
                )
            )
            .scalars()
            .all()
        )
        for row in existing:
            await self.session.delete(row)
        await self.session.flush()
        for m in matchups:
            self._add_side_row(m, m.home, m.away.roster_id if m.away else None)
            if m.away:
                self._add_side_row(m, m.away, m.home.roster_id)
        await self.session.flush()

    async def get_transactions(self, league_id: str, week: int | None = None) -> list[Transaction]:
        stmt = select(TransactionRow).where(TransactionRow.league_id == league_id)
        if week is not None:
            stmt = stmt.where(TransactionRow.week == week)
        stmt = stmt.order_by(TransactionRow.created_at.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            Transaction(
                transaction_id=r.transaction_id,
                league_id=r.league_id,
                week=r.week,
                type=r.type,
                status=r.status,
                roster_ids=list(r.roster_ids or []),
                adds=dict(r.adds or {}),
                drops=dict(r.drops or {}),
                waiver_budget=list(r.waiver_budget or []),
                created_at=r.created_at,
                notes=r.notes,
            )
            for r in rows
        ]

    async def upsert_transactions(self, transactions: list[Transaction]) -> list[Transaction]:
        created: list[Transaction] = []
        for tx in transactions:
            existing = await self.session.get(TransactionRow, tx.transaction_id)
            if existing is None:
                self.session.add(
                    TransactionRow(
                        transaction_id=tx.transaction_id,
                        league_id=tx.league_id,
                        week=tx.week,
                        type=tx.type,
                        status=tx.status,
                        roster_ids=tx.roster_ids,
                        adds=tx.adds,
                        drops=tx.drops,
                        waiver_budget=tx.waiver_budget,
                        created_at=tx.created_at,
                        notes=tx.notes,
                    )
                )
                created.append(tx)
        await self.session.flush()
        return created

    def _add_side_row(self, matchup: Matchup, side: MatchupSide, opponent_id: int | None) -> None:
        self.session.add(
            MatchupRow(
                league_id=matchup.league_id,
                week=matchup.week,
                matchup_id=matchup.matchup_id,
                roster_id=side.roster_id,
                opponent_roster_id=opponent_id,
                points=side.points,
                projected_points=side.projected_points,
                starters=side.starters,
                players=side.players,
                starter_points=side.starter_points,
                player_points=side.player_points,
            )
        )

    @staticmethod
    def _league(row: LeagueRow) -> League:
        return League(
            league_id=row.league_id,
            name=row.name,
            season=row.season,
            sport=row.sport,
            status=row.status,
            season_type=row.season_type,
            total_rosters=row.total_rosters,
            roster_positions=list(row.roster_positions or []),
            scoring_settings=dict(row.scoring_settings or {}),
            settings=dict(row.settings or {}),
            week=row.week,
            provider=row.provider,
            avatar=row.avatar,
        )

    @staticmethod
    def _roster(row: RosterRow) -> Roster:
        return Roster(
            roster_id=row.roster_id,
            league_id=row.league_id,
            owner_id=row.owner_id,
            owner_name=row.owner_name,
            team_name=row.team_name,
            wins=row.wins,
            losses=row.losses,
            ties=row.ties,
            points_for=row.points_for,
            points_against=row.points_against,
            starters=list(row.starters or []),
            players=list(row.players or []),
            taxi=list(row.taxi or []),
            reserve=list(row.reserve or []),
            waiver_budget_used=row.waiver_budget_used,
            waiver_position=row.waiver_position,
        )

    @staticmethod
    def _side(row: MatchupRow) -> MatchupSide:
        return MatchupSide(
            roster_id=row.roster_id,
            owner_name=None,
            points=row.points,
            projected_points=row.projected_points,
            starters=list(row.starters or []),
            players=list(row.players or []),
            starter_points=list(row.starter_points or []),
            player_points=dict(row.player_points or {}),
        )
