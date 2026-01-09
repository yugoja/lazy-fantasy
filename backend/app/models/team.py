from typing import Optional
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str] = mapped_column(String(10))
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    players = relationship("Player", back_populates="team")

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', short='{self.short_name}')>"
