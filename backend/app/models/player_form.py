from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PlayerForm(Base):
    __tablename__ = "player_form"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), unique=True, nullable=False)

    expected_points: Mapped[float] = mapped_column(Float, nullable=False, default=6.0)
    floor: Mapped[str] = mapped_column(String(4), nullable=False, default="mid")
    availability: Mapped[str] = mapped_column(String(10), nullable=False, default="starter")

    wc_goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wc_assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wc_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wc_clean_sheets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wc_games: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pre_expected_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    player = relationship("Player", back_populates="form")
