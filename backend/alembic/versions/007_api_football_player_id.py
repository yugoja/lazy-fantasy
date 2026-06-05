"""add api_football_player_id to players

Revision ID: 007_api_football_player_id
Revises: 006_football_models
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_api_football_player_id"
down_revision: Union[str, Sequence[str], None] = "006_football_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("players", sa.Column("api_football_player_id", sa.String(100), nullable=True))
    op.create_index(
        "ix_players_api_football_player_id",
        "players",
        ["api_football_player_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_players_api_football_player_id", table_name="players")
    op.drop_column("players", "api_football_player_id")
