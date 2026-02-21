from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MatchLineup(Base):
    __tablename__ = "match_lineups"
    __table_args__ = (
        UniqueConstraint("match_id", "player_id", name="uq_match_player"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"))
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))

    match = relationship("Match")
    player = relationship("Player")

    def __repr__(self) -> str:
        return f"<MatchLineup(match_id={self.match_id}, player_id={self.player_id})>"
