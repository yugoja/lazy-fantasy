from datetime import datetime

from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReminderLog(Base):
    """Tracks which matches have had reminders sent to avoid duplicates."""
    __tablename__ = "reminder_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), unique=True, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
