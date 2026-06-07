"""Add source column to football_predictions

Revision ID: 009_football_prediction_source
Revises: 008_match_group_round
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "009_football_prediction_source"
down_revision = "008_match_group_round"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "football_predictions",
        sa.Column("source", sa.String(20), nullable=False, server_default="user"),
    )


def downgrade() -> None:
    op.drop_column("football_predictions", "source")
