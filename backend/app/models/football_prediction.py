from typing import Optional

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FootballPrediction(Base):
    """Sport-specific child of a shared :class:`Prediction` row for football.

    Holds a user's per-match picks (WC2026 scoring spec §1): the predicted
    scoreline, who they think advances (knockout draws only), and three player
    picks. The parent ``predictions`` row owns ``points_earned`` /
    ``is_processed``; sport is resolved via ``prediction.match.tournament.sport``.
    """

    __tablename__ = "football_predictions"

    prediction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("predictions.id", ondelete="CASCADE"), primary_key=True
    )

    # Predicted scoreline. Result (W/D/W) is derived from these.
    team1_goals: Mapped[int] = mapped_column(Integer)
    team2_goals: Mapped[int] = mapped_column(Integer)

    # Who the user thinks advances. Required only when the predicted scoreline
    # is a draw in a knockout match (e.g. "France 2-2 win"); null otherwise.
    advance_winner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )

    # Three player picks (spec: 3 player picks per match, no captain).
    player_pick_1_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))
    player_pick_2_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))
    player_pick_3_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))

    # How this prediction was created: 'user' (manual submit) or 'autopick' (fallback job).
    source: Mapped[str] = mapped_column(String(20), default="user", server_default="user")

    # Relationships
    prediction = relationship("Prediction", back_populates="football")
    advance_winner = relationship("Team", foreign_keys=[advance_winner_id])
    player_pick_1 = relationship("Player", foreign_keys=[player_pick_1_id])
    player_pick_2 = relationship("Player", foreign_keys=[player_pick_2_id])
    player_pick_3 = relationship("Player", foreign_keys=[player_pick_3_id])

    def __repr__(self) -> str:
        return (
            f"<FootballPrediction(prediction_id={self.prediction_id}, "
            f"{self.team1_goals}-{self.team2_goals})>"
        )
