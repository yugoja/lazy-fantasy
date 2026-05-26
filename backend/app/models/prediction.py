from typing import Optional

from sqlalchemy import Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Prediction(Base):
    """Shared prediction row across sports.

    Owns the cross-sport fields (``points_earned`` / ``is_processed``). The
    cricket picks remain inline here (nullable, since a football prediction
    leaves them empty); football picks live in the 1:1 :class:`FootballPrediction`
    child. Sport is resolved via ``match.tournament.sport``.
    """

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"))

    # Cricket picks (inline, nullable — empty for football predictions).
    predicted_winner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    predicted_most_runs_team1_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    predicted_most_runs_team2_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    predicted_most_wickets_team1_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    predicted_most_wickets_team2_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    predicted_pom_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="predictions")
    match = relationship("Match", back_populates="predictions")
    football = relationship(
        "FootballPrediction",
        back_populates="prediction",
        uselist=False,
        cascade="all, delete-orphan",
    )
    predicted_winner = relationship("Team", foreign_keys=[predicted_winner_id])
    predicted_most_runs_team1_player = relationship(
        "Player", foreign_keys=[predicted_most_runs_team1_player_id]
    )
    predicted_most_runs_team2_player = relationship(
        "Player", foreign_keys=[predicted_most_runs_team2_player_id]
    )
    predicted_most_wickets_team1_player = relationship(
        "Player", foreign_keys=[predicted_most_wickets_team1_player_id]
    )
    predicted_most_wickets_team2_player = relationship(
        "Player", foreign_keys=[predicted_most_wickets_team2_player_id]
    )
    predicted_pom_player = relationship("Player", foreign_keys=[predicted_pom_player_id])

    def __repr__(self) -> str:
        return f"<Prediction(id={self.id}, user={self.user_id}, match={self.match_id})>"
