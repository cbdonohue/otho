"""initial otho schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column("league_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("season", sa.String(8), nullable=False),
        sa.Column("sport", sa.String(16), default="nfl"),
        sa.Column("status", sa.String(32), default="in_season"),
        sa.Column("season_type", sa.String(32), default="regular"),
        sa.Column("total_rosters", sa.Integer, default=12),
        sa.Column("roster_positions", sa.JSON, default=list),
        sa.Column("scoring_settings", sa.JSON, default=dict),
        sa.Column("settings", sa.JSON, default=dict),
        sa.Column("week", sa.Integer, nullable=True),
        sa.Column("provider", sa.String(32), default="sleeper"),
        sa.Column("avatar", sa.String(128), nullable=True),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "league_users",
        sa.Column("user_id", sa.String(64), primary_key=True),
        sa.Column("league_id", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("avatar", sa.String(128), nullable=True),
        sa.Column("is_commissioner", sa.Boolean, default=False),
        sa.Column("roster_id", sa.Integer, nullable=True),
    )
    op.create_table(
        "rosters",
        sa.Column("league_id", sa.String(64), primary_key=True),
        sa.Column("roster_id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.String(64), nullable=True),
        sa.Column("owner_name", sa.String(128), nullable=True),
        sa.Column("team_name", sa.String(128), nullable=True),
        sa.Column("wins", sa.Integer, default=0),
        sa.Column("losses", sa.Integer, default=0),
        sa.Column("ties", sa.Integer, default=0),
        sa.Column("points_for", sa.Float, default=0),
        sa.Column("points_against", sa.Float, default=0),
        sa.Column("starters", sa.JSON, default=list),
        sa.Column("players", sa.JSON, default=list),
        sa.Column("taxi", sa.JSON, default=list),
        sa.Column("reserve", sa.JSON, default=list),
        sa.Column("waiver_budget_used", sa.Integer, default=0),
        sa.Column("waiver_position", sa.Integer, nullable=True),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "roster_players",
        sa.Column("league_id", sa.String(64), primary_key=True),
        sa.Column("roster_id", sa.Integer, primary_key=True),
        sa.Column("player_id", sa.String(64), primary_key=True),
        sa.Column("slot", sa.String(16), nullable=True),
        sa.Column("is_starter", sa.Boolean, default=False),
    )
    op.create_table(
        "players",
        sa.Column("player_id", sa.String(64), primary_key=True),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("first_name", sa.String(64), nullable=True),
        sa.Column("last_name", sa.String(64), nullable=True),
        sa.Column("position", sa.String(8), nullable=True),
        sa.Column("team", sa.String(8), nullable=True),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("injury_status", sa.String(32), nullable=True),
        sa.Column("number", sa.Integer, nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("years_exp", sa.Integer, nullable=True),
        sa.Column("depth_chart_order", sa.Integer, nullable=True),
        sa.Column("search_rank", sa.Integer, nullable=True),
        sa.Column("sport", sa.String(8), default="nfl"),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "matchups",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("league_id", sa.String(64), index=True),
        sa.Column("week", sa.Integer),
        sa.Column("matchup_id", sa.Integer, nullable=True),
        sa.Column("roster_id", sa.Integer),
        sa.Column("opponent_roster_id", sa.Integer, nullable=True),
        sa.Column("points", sa.Float, default=0),
        sa.Column("projected_points", sa.Float, nullable=True),
        sa.Column("starters", sa.JSON, default=list),
        sa.Column("players", sa.JSON, default=list),
        sa.Column("starter_points", sa.JSON, default=list),
        sa.Column("player_points", sa.JSON, default=dict),
        sa.UniqueConstraint("league_id", "week", "roster_id", name="uq_matchup_roster_week"),
    )
    op.create_table(
        "matchup_players",
        sa.Column("league_id", sa.String(64), primary_key=True),
        sa.Column("week", sa.Integer, primary_key=True),
        sa.Column("roster_id", sa.Integer, primary_key=True),
        sa.Column("player_id", sa.String(64), primary_key=True),
        sa.Column("points", sa.Float, default=0),
        sa.Column("is_starter", sa.Boolean, default=False),
    )
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.String(64), primary_key=True),
        sa.Column("league_id", sa.String(64), index=True),
        sa.Column("week", sa.Integer),
        sa.Column("type", sa.String(32)),
        sa.Column("status", sa.String(32)),
        sa.Column("roster_ids", sa.JSON, default=list),
        sa.Column("adds", sa.JSON, default=dict),
        sa.Column("drops", sa.JSON, default=dict),
        sa.Column("waiver_budget", sa.JSON, default=list),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_table(
        "projections",
        sa.Column("player_id", sa.String(64), primary_key=True),
        sa.Column("week", sa.Integer, primary_key=True),
        sa.Column("season", sa.String(8), primary_key=True),
        sa.Column("points", sa.Float),
        sa.Column("floor", sa.Float, nullable=True),
        sa.Column("ceiling", sa.Float, nullable=True),
        sa.Column("source", sa.String(64), default="otho.heuristic"),
        sa.Column("position", sa.String(8), nullable=True),
    )
    op.create_table(
        "player_news",
        sa.Column("news_id", sa.String(64), primary_key=True),
        sa.Column("player_id", sa.String(64), index=True),
        sa.Column("headline", sa.String(512)),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("source", sa.String(64), default="stub"),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("impact", sa.String(16), nullable=True),
    )
    op.create_table(
        "player_stats",
        sa.Column("player_id", sa.String(64), primary_key=True),
        sa.Column("week", sa.Integer, primary_key=True),
        sa.Column("season", sa.String(8), primary_key=True),
        sa.Column("stats", sa.JSON, default=dict),
        sa.Column("points", sa.Float, default=0),
    )
    op.create_table(
        "plugin_results",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("plugin_id", sa.String(64), index=True),
        sa.Column("league_id", sa.String(64), index=True),
        sa.Column("roster_id", sa.Integer, nullable=True),
        sa.Column("week", sa.Integer),
        sa.Column("title", sa.String(256)),
        sa.Column("summary", sa.Text),
        sa.Column("data", sa.JSON, default=dict),
        sa.Column("widgets", sa.JSON, default=list),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("league_id", sa.String(64), index=True),
        sa.Column("kind", sa.String(32)),
        sa.Column("week", sa.Integer, nullable=True),
        sa.Column("payload", sa.JSON, default=dict),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in [
        "snapshots",
        "plugin_results",
        "player_stats",
        "player_news",
        "projections",
        "transactions",
        "matchup_players",
        "matchups",
        "players",
        "roster_players",
        "rosters",
        "league_users",
        "leagues",
    ]:
        op.drop_table(table)
