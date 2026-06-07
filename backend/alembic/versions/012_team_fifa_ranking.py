"""Add fifa_ranking to teams

Revision ID: 012_team_fifa_ranking
Revises: 010_images_and_urls
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "012_team_fifa_ranking"
down_revision = "011_player_form"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("fifa_ranking", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("teams", "fifa_ranking")
