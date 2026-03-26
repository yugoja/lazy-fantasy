from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DugoutDismissal(Base):
    __tablename__ = "dugout_dismissals"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    type: Mapped[str] = mapped_column(String(20), primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, ForeignKey("leagues.id"), primary_key=True)
    # match_id is nullable (rank_shift has no match_id)
    match_id: Mapped[int | None] = mapped_column(Integer, nullable=True, primary_key=True, default=0)
    # The subject of the event (username of the person the event is about)
    subject_username: Mapped[str] = mapped_column(String(50), primary_key=True)
