from datetime import datetime

from sqlalchemy import DateTime, Integer, String, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    invite_code: Mapped[str] = mapped_column(String(6), unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    sport: Mapped[str] = mapped_column(String(20), default="cricket", server_default="cricket")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    owner = relationship("User", back_populates="owned_leagues")
    members = relationship("LeagueMember", back_populates="league")

    def __repr__(self) -> str:
        return f"<League(id={self.id}, name='{self.name}')>"


class LeagueMember(Base):
    __tablename__ = "league_members"

    league_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leagues.id"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), primary_key=True
    )
    prev_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    league = relationship("League", back_populates="members")
    user = relationship("User", back_populates="league_memberships")

    def __repr__(self) -> str:
        return f"<LeagueMember(league_id={self.league_id}, user_id={self.user_id})>"
