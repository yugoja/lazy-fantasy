"""Add lineup_data JSON to matches (announced football formation + grid)

Revision ID: 014_match_lineup_data
Revises: 013_football_tournament_awards
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa

revision = "014_match_lineup_data"
down_revision = "013_football_tournament_awards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # JSON-encoded confirmed lineup once the XI is announced:
    # {"team1_formation": "4-2-3-1", "team2_formation": "...",
    #  "slots": {"<db_player_id>": [row, col], ...}}
    # Null until the lineup is published. Drives the real-formation pitch view.
    op.add_column("matches", sa.Column("lineup_data", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "lineup_data")
