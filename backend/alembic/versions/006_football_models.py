"""football models: polymorphic football child tables + match stage

Adds the football side of the multi-sport schema (hybrid approach: cricket
picks/results stay inline on predictions/matches; football gets 1:1 child
tables). Also relaxes the inline cricket prediction columns to nullable so a
football prediction row can leave them empty.

Revision ID: 006_football_models
Revises: a1c99c58f11a
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006_football_models"
down_revision: Union[str, Sequence[str], None] = "a1c99c58f11a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CRICKET_PREDICTION_COLS = (
    "predicted_winner_id",
    "predicted_most_runs_team1_player_id",
    "predicted_most_runs_team2_player_id",
    "predicted_most_wickets_team1_player_id",
    "predicted_most_wickets_team2_player_id",
    "predicted_pom_player_id",
)


def upgrade() -> None:
    op.create_table(
        "football_predictions",
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("team1_goals", sa.Integer(), nullable=False),
        sa.Column("team2_goals", sa.Integer(), nullable=False),
        sa.Column("advance_winner_id", sa.Integer(), nullable=True),
        sa.Column("player_pick_1_id", sa.Integer(), nullable=False),
        sa.Column("player_pick_2_id", sa.Integer(), nullable=False),
        sa.Column("player_pick_3_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["advance_winner_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["player_pick_1_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["player_pick_2_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["player_pick_3_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("prediction_id"),
    )

    op.create_table(
        "football_match_results",
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("team1_goals_reg", sa.Integer(), nullable=False),
        sa.Column("team2_goals_reg", sa.Integer(), nullable=False),
        sa.Column("team1_goals_et", sa.Integer(), nullable=True),
        sa.Column("team2_goals_et", sa.Integer(), nullable=True),
        sa.Column("shootout_winner_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shootout_winner_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("match_id"),
    )

    op.create_table(
        "football_player_match_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("minutes_played", sa.Integer(), server_default="0", nullable=False),
        sa.Column("goals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("assists", sa.Integer(), server_default="0", nullable=False),
        sa.Column("team_goals_conceded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ingame_pen_saves", sa.Integer(), server_default="0", nullable=False),
        sa.Column("shootout_pen_saves", sa.Integer(), server_default="0", nullable=False),
        sa.Column("red_card", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("own_goals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ingame_pen_misses", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["match_id"], ["football_match_results.match_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_id", "player_id", name="uq_football_event_match_player"
        ),
    )
    op.create_index(
        op.f("ix_football_player_match_events_id"),
        "football_player_match_events",
        ["id"],
        unique=False,
    )

    # Match stage (drives the football knockout 2x multiplier; null for cricket).
    op.add_column("matches", sa.Column("stage", sa.String(length=10), nullable=True))

    # Relax inline cricket prediction columns so football rows can omit them.
    with op.batch_alter_table("predictions") as batch_op:
        for col in _CRICKET_PREDICTION_COLS:
            batch_op.alter_column(col, existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("predictions") as batch_op:
        for col in _CRICKET_PREDICTION_COLS:
            batch_op.alter_column(col, existing_type=sa.Integer(), nullable=False)

    op.drop_column("matches", "stage")

    op.drop_index(
        op.f("ix_football_player_match_events_id"),
        table_name="football_player_match_events",
    )
    op.drop_table("football_player_match_events")
    op.drop_table("football_match_results")
    op.drop_table("football_predictions")
