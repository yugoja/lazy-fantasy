from sqlalchemy import Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"))
    predicted_winner_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    predicted_most_runs_player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id")
    )
    predicted_most_wickets_player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id")
    )
    predicted_pom_player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id")
    )
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="predictions")
    match = relationship("Match", back_populates="predictions")
    predicted_winner = relationship("Team", foreign_keys=[predicted_winner_id])
    predicted_most_runs_player = relationship(
        "Player", foreign_keys=[predicted_most_runs_player_id]
    )
    predicted_most_wickets_player = relationship(
        "Player", foreign_keys=[predicted_most_wickets_player_id]
    )
    predicted_pom_player = relationship("Player", foreign_keys=[predicted_pom_player_id])

    def __repr__(self) -> str:
        return f"<Prediction(id={self.id}, user={self.user_id}, match={self.match_id})>"
