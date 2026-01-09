from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    role: Mapped[str] = mapped_column(String(50))  # Batsman, Bowler, All-Rounder, Wicketkeeper

    # Relationships
    team = relationship("Team", back_populates="players")

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name='{self.name}', role='{self.role}')>"
