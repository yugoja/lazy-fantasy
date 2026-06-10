"""Add football tournament-level award picks (golden ball/boot/glove)

Revision ID: 013_football_tournament_awards
Revises: 012_team_fifa_ranking
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "013_football_tournament_awards"
down_revision = "012_team_fifa_ranking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # User picks: 3 football player awards (semi-finalists reuse top4_team* columns)
    op.add_column(
        "tournament_picks",
        sa.Column("golden_ball_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
    )
    op.add_column(
        "tournament_picks",
        sa.Column("golden_boot_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
    )
    op.add_column(
        "tournament_picks",
        sa.Column("golden_glove_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
    )

    # Tournament results for scoring
    op.add_column(
        "tournaments",
        sa.Column("result_golden_ball_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
    )
    op.add_column(
        "tournaments",
        sa.Column("result_golden_boot_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
    )
    op.add_column(
        "tournaments",
        sa.Column("result_golden_glove_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tournaments", "result_golden_glove_player_id")
    op.drop_column("tournaments", "result_golden_boot_player_id")
    op.drop_column("tournaments", "result_golden_ball_player_id")
    op.drop_column("tournament_picks", "golden_glove_player_id")
    op.drop_column("tournament_picks", "golden_boot_player_id")
    op.drop_column("tournament_picks", "golden_ball_player_id")
