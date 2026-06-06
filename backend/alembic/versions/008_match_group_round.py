"""add group_round to matches

Revision ID: 008_match_group_round
Revises: 007_api_football_player_id
Create Date: 2026-06-06

"""
from typing import Sequence, Union
from collections import defaultdict

from alembic import op
import sqlalchemy as sa


revision: str = "008_match_group_round"
down_revision: Union[str, Sequence[str], None] = "007_api_football_player_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("group_round", sa.Integer(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, tournament_id, team_1_id, team_2_id, start_time "
            "FROM matches WHERE stage = 'GROUP' "
            "ORDER BY tournament_id, start_time ASC"
        )
    ).fetchall()

    # Track per-team appearance count: {(tournament_id, team_id): count}
    team_counts: dict = defaultdict(int)
    for row in rows:
        match_id, tournament_id, team_1_id, team_2_id, _ = row
        team_counts[(tournament_id, team_1_id)] += 1
        team_counts[(tournament_id, team_2_id)] += 1
        group_round = max(
            team_counts[(tournament_id, team_1_id)],
            team_counts[(tournament_id, team_2_id)],
        )
        bind.execute(
            sa.text("UPDATE matches SET group_round = :gr WHERE id = :mid"),
            {"gr": group_round, "mid": match_id},
        )


def downgrade() -> None:
    op.drop_column("matches", "group_round")
