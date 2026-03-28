from typing import Optional
from sqlalchemy import Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TournamentPick(Base):
    __tablename__ = "tournament_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)

    top4_team1_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    top4_team2_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    top4_team3_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    top4_team4_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    best_batsman_player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    best_bowler_player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)

    points_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_window2: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "tournament_id"),)

    # Relationships
    user = relationship("User", backref="tournament_picks")
    tournament = relationship("Tournament", back_populates="picks")
    top4_team1 = relationship("Team", foreign_keys=[top4_team1_id])
    top4_team2 = relationship("Team", foreign_keys=[top4_team2_id])
    top4_team3 = relationship("Team", foreign_keys=[top4_team3_id])
    top4_team4 = relationship("Team", foreign_keys=[top4_team4_id])
    best_batsman = relationship("Player", foreign_keys=[best_batsman_player_id])
    best_bowler = relationship("Player", foreign_keys=[best_bowler_player_id])

    def __repr__(self) -> str:
        return f"<TournamentPick(id={self.id}, user_id={self.user_id}, tournament_id={self.tournament_id})>"
