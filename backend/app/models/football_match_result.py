from typing import Optional

from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FootballMatchResult(Base):
    """Sport-specific result for a football match (WC2026 scoring spec §10).

    Goals are stored as regulation and (knockout-only) end-of-extra-time
    totals. Penalty shootouts never feed the scoreline — they only set
    ``shootout_winner_id`` to decide who advances in a knockout. Per-player
    events live in :class:`FootballPlayerMatchEvent`.
    """

    __tablename__ = "football_match_results"

    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True
    )

    team1_goals_reg: Mapped[int] = mapped_column(Integer)
    team2_goals_reg: Mapped[int] = mapped_column(Integer)

    # End-of-extra-time totals; null when no ET was played (e.g. group stage).
    team1_goals_et: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    team2_goals_et: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Set only when a knockout match goes to penalties; null otherwise.
    shootout_winner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )

    # Relationships
    match = relationship("Match", back_populates="football_result")
    shootout_winner = relationship("Team", foreign_keys=[shootout_winner_id])
    player_events = relationship(
        "FootballPlayerMatchEvent",
        back_populates="match_result",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<FootballMatchResult(match_id={self.match_id}, "
            f"{self.team1_goals_reg}-{self.team2_goals_reg})>"
        )


class FootballPlayerMatchEvent(Base):
    """Per-player events for one football match (WC2026 scoring spec §10).

    ``team_goals_conceded`` is the reg+ET total (shootout goals excluded), used
    for clean-sheet eligibility. In-game and shootout penalty saves are tracked
    separately because the data layer must distinguish them, though both score
    the same +5. Shootout outfield misses are intentionally not stored — they
    don't affect scoring.
    """

    __tablename__ = "football_player_match_events"
    __table_args__ = (
        # one event row per (match, player)
        UniqueConstraint("match_id", "player_id", name="uq_football_event_match_player"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("football_match_results.match_id", ondelete="CASCADE")
    )
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))

    minutes_played: Mapped[int] = mapped_column(Integer, default=0)
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    team_goals_conceded: Mapped[int] = mapped_column(Integer, default=0)
    ingame_pen_saves: Mapped[int] = mapped_column(Integer, default=0)
    shootout_pen_saves: Mapped[int] = mapped_column(Integer, default=0)
    red_card: Mapped[bool] = mapped_column(default=False)
    own_goals: Mapped[int] = mapped_column(Integer, default=0)
    ingame_pen_misses: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    match_result = relationship("FootballMatchResult", back_populates="player_events")
    player = relationship("Player", foreign_keys=[player_id])

    def __repr__(self) -> str:
        return (
            f"<FootballPlayerMatchEvent(match={self.match_id}, "
            f"player={self.player_id})>"
        )
