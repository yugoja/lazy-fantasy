from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MatchStatus(str, PyEnum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"))
    team_1_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    team_2_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.SCHEDULED
    )

    # CricAPI sync fields
    external_match_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sync_state: Mapped[str] = mapped_column(String(20), default="unlinked")
    # sync_state values: unlinked | linked | lineup_synced | result_synced
    sync_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Match results (nullable until match is completed)
    result_winner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    result_most_runs_team1_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    result_most_runs_team2_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    result_most_wickets_team1_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    result_most_wickets_team2_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )
    result_pom_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=True
    )

    # Relationships
    tournament = relationship("Tournament", back_populates="matches")
    team_1 = relationship("Team", foreign_keys=[team_1_id])
    team_2 = relationship("Team", foreign_keys=[team_2_id])
    winner = relationship("Team", foreign_keys=[result_winner_id])
    most_runs_team1_player = relationship("Player", foreign_keys=[result_most_runs_team1_player_id])
    most_runs_team2_player = relationship("Player", foreign_keys=[result_most_runs_team2_player_id])
    most_wickets_team1_player = relationship("Player", foreign_keys=[result_most_wickets_team1_player_id])
    most_wickets_team2_player = relationship("Player", foreign_keys=[result_most_wickets_team2_player_id])
    pom_player = relationship("Player", foreign_keys=[result_pom_player_id])
    predictions = relationship("Prediction", back_populates="match")

    def __repr__(self) -> str:
        return f"<Match(id={self.id}, {self.team_1_id} vs {self.team_2_id})>"
