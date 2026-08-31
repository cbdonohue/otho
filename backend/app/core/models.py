"""SQLAlchemy ORM models. Historical snapshots live alongside current state."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LeagueRow(Base):
    __tablename__ = "leagues"

    league_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    season: Mapped[str] = mapped_column(String(8))
    sport: Mapped[str] = mapped_column(String(16), default="nfl")
    status: Mapped[str] = mapped_column(String(32), default="in_season")
    season_type: Mapped[str] = mapped_column(String(32), default="regular")
    total_rosters: Mapped[int] = mapped_column(Integer, default=12)
    roster_positions: Mapped[list] = mapped_column(JSON, default=list)
    scoring_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), default="sleeper")
    avatar: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class LeagueUserRow(Base):
    __tablename__ = "league_users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    league_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128))
    avatar: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_commissioner: Mapped[bool] = mapped_column(default=False)
    roster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RosterRow(Base):
    __tablename__ = "rosters"

    league_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    roster_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    team_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    ties: Mapped[int] = mapped_column(Integer, default=0)
    points_for: Mapped[float] = mapped_column(Float, default=0.0)
    points_against: Mapped[float] = mapped_column(Float, default=0.0)
    starters: Mapped[list] = mapped_column(JSON, default=list)
    players: Mapped[list] = mapped_column(JSON, default=list)
    taxi: Mapped[list] = mapped_column(JSON, default=list)
    reserve: Mapped[list] = mapped_column(JSON, default=list)
    waiver_budget_used: Mapped[int] = mapped_column(Integer, default=0)
    waiver_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class RosterPlayerRow(Base):
    __tablename__ = "roster_players"

    league_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    roster_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_starter: Mapped[bool] = mapped_column(default=False)


class PlayerRow(Base):
    __tablename__ = "players"

    player_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(128))
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    position: Mapped[str | None] = mapped_column(String(8), nullable=True)
    team: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    injury_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    years_exp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    depth_chart_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sport: Mapped[str] = mapped_column(String(8), default="nfl")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MatchupRow(Base):
    __tablename__ = "matchups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league_id: Mapped[str] = mapped_column(String(64), index=True)
    week: Mapped[int] = mapped_column(Integer)
    matchup_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    roster_id: Mapped[int] = mapped_column(Integer)
    opponent_roster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[float] = mapped_column(Float, default=0.0)
    projected_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    starters: Mapped[list] = mapped_column(JSON, default=list)
    players: Mapped[list] = mapped_column(JSON, default=list)
    starter_points: Mapped[list] = mapped_column(JSON, default=list)
    player_points: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (UniqueConstraint("league_id", "week", "roster_id", name="uq_matchup_roster_week"),)


class MatchupPlayerRow(Base):
    __tablename__ = "matchup_players"

    league_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    week: Mapped[int] = mapped_column(Integer, primary_key=True)
    roster_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    points: Mapped[float] = mapped_column(Float, default=0.0)
    is_starter: Mapped[bool] = mapped_column(default=False)


class TransactionRow(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    league_id: Mapped[str] = mapped_column(String(64), index=True)
    week: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    roster_ids: Mapped[list] = mapped_column(JSON, default=list)
    adds: Mapped[dict] = mapped_column(JSON, default=dict)
    drops: Mapped[dict] = mapped_column(JSON, default=dict)
    waiver_budget: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProjectionRow(Base):
    __tablename__ = "projections"

    player_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    week: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[str] = mapped_column(String(8), primary_key=True)
    points: Mapped[float] = mapped_column(Float)
    floor: Mapped[float | None] = mapped_column(Float, nullable=True)
    ceiling: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="otho.heuristic")
    position: Mapped[str | None] = mapped_column(String(8), nullable=True)


class PlayerNewsRow(Base):
    __tablename__ = "player_news"

    news_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(64), index=True)
    headline: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="stub")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    impact: Mapped[str | None] = mapped_column(String(16), nullable=True)


class PlayerStatRow(Base):
    __tablename__ = "player_stats"

    player_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    week: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[str] = mapped_column(String(8), primary_key=True)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    points: Mapped[float] = mapped_column(Float, default=0.0)


class PluginResultRow(Base):
    __tablename__ = "plugin_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plugin_id: Mapped[str] = mapped_column(String(64), index=True)
    league_id: Mapped[str] = mapped_column(String(64), index=True)
    roster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    widgets: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SnapshotRow(Base):
    """Point-in-time capture of league/roster state for historical analysis."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # roster | matchup | league
    week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
