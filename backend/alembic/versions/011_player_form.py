"""Add player_form table and api_football_team_id to teams

Revision ID: 011_player_form
Revises: 010_images_and_urls
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "011_player_form"
down_revision = "010_images_and_urls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("api_football_team_id", sa.String(50), nullable=True))

    op.create_table(
        "player_form",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("player_id", sa.Integer, sa.ForeignKey("players.id"), unique=True, nullable=False),
        sa.Column("expected_points", sa.Float, nullable=False, server_default="6.0"),
        sa.Column("floor", sa.String(4), nullable=False, server_default="mid"),
        sa.Column("availability", sa.String(10), nullable=False, server_default="starter"),
        sa.Column("wc_goals", sa.Integer, nullable=False, server_default="0"),
        sa.Column("wc_assists", sa.Integer, nullable=False, server_default="0"),
        sa.Column("wc_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("wc_clean_sheets", sa.Integer, nullable=False, server_default="0"),
        sa.Column("wc_games", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pre_expected_points", sa.Float, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("player_form")
    op.drop_column("teams", "api_football_team_id")
