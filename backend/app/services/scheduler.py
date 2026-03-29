"""APScheduler background jobs: match reminders + cricket data sync."""
import logging
from datetime import datetime, timedelta  # timedelta used by reminder window

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.match import Match, MatchStatus
from app.models.reminder_log import ReminderLog
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.services.notifications import send_reminder_email, send_push_notification

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _send_match_reminders() -> None:
    """Find matches starting in ~1 hour and send reminders to all users."""
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        window_start = now + timedelta(minutes=55)
        window_end = now + timedelta(minutes=65)

        matches = (
            db.query(Match)
            .filter(
                Match.status == MatchStatus.SCHEDULED,
                Match.start_time >= window_start,
                Match.start_time <= window_end,
            )
            .all()
        )

        for match in matches:
            # Skip if reminder already sent for this match
            already_sent = db.query(ReminderLog).filter_by(match_id=match.id).first()
            if already_sent:
                continue

            team_1 = match.team_1.short_name
            team_2 = match.team_2.short_name
            match_time = match.start_time.strftime("%b %d, %I:%M %p UTC")

            # Email — disabled until tested; uncomment to enable
            # users = db.query(User).all()
            # email_count = 0
            # for user in users:
            #     if send_reminder_email(user.email, team_1, team_2, match_time):
            #         email_count += 1
            email_count = 0

            # Push — send to all subscribed users
            subscriptions = db.query(PushSubscription).all()
            push_count = 0
            stale_ids = []
            for sub in subscriptions:
                success = send_push_notification(sub.endpoint, sub.auth, sub.p256dh, team_1, team_2)
                if success:
                    push_count += 1
                else:
                    stale_ids.append(sub.id)

            # Remove stale push subscriptions (410 Gone)
            if stale_ids:
                db.query(PushSubscription).filter(PushSubscription.id.in_(stale_ids)).delete(synchronize_session=False)

            # Log that reminder was sent
            db.add(ReminderLog(match_id=match.id))
            db.commit()

            logger.info(
                f"Reminders sent for match {team_1} vs {team_2}: "
                f"{email_count} emails, {push_count} pushes"
            )

    except Exception as e:
        logger.error(f"Reminder job failed: {e}")
        db.rollback()
    finally:
        db.close()


def _run_sync(fn) -> None:
    """Run a sync function with its own DB session, logging errors."""
    db: Session = SessionLocal()
    try:
        fn(db)
    except Exception as e:
        logger.error(f"{fn.__name__} failed: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    from app.services.cricket_sync import sync_lineups
    from app.config import settings

    scheduler.add_job(
        _send_match_reminders,
        trigger="interval",
        minutes=5,
        id="match_reminders",
        replace_existing=True,
    )

    # Lineup sync — only active when CRICAPI_KEY is configured
    # Results are set manually via the admin panel
    if settings.CRICAPI_KEY:
        from app.services.providers.cricapi import CricApiProvider
        from app.services.cricket_sync import set_provider
        set_provider(CricApiProvider(settings.CRICAPI_KEY, settings.CRICAPI_BASE_URL))

        scheduler.add_job(
            lambda: _run_sync(sync_lineups),
            trigger="interval",
            minutes=10,
            id="lineup_sync",
            replace_existing=True,
        )
        logger.info("Cricket lineup sync registered (every 10m)")
    else:
        logger.info("CRICAPI_KEY not set — lineup sync skipped")

    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
