from datetime import date
from typing import Optional
from sqlalchemy import Integer, String, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    sport: Mapped[str] = mapped_column(String(20), default="cricket", server_default="cricket")

    # Tournament picks window: 'closed' | 'open' | 'locked' | 'open2' | 'finalized'
    picks_window: Mapped[str] = mapped_column(String(10), default="closed", server_default="closed")

    # Result columns for tournament picks scoring
    result_top4_team1_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    result_top4_team2_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    result_top4_team3_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    result_top4_team4_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    result_best_batsman_player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)
    result_best_bowler_player_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)

    # Relationships
    matches = relationship("Match", back_populates="tournament")
    picks = relationship("TournamentPick", back_populates="tournament")

    def __repr__(self) -> str:
        return f"<Tournament(id={self.id}, name='{self.name}')>"
