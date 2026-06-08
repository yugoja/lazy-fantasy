"""APScheduler background jobs: match reminders + cricket data sync."""
import logging
from datetime import datetime, timedelta, timezone

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
                result = send_push_notification(sub.endpoint, sub.auth, sub.p256dh, team_1, team_2)
                if result is True:
                    push_count += 1
                elif result is None:
                    # None means 410 Gone — subscription is no longer valid
                    stale_ids.append(sub.id)

            # Remove expired push subscriptions (410 Gone only)
            if stale_ids:
                db.query(PushSubscription).filter(PushSubscription.id.in_(stale_ids)).delete(synchronize_session=False)

            # Only log the reminder as sent if there were subscriptions to attempt.
            # If the DB had zero subscriptions (e.g. all previously wiped), skip logging
            # so the next scheduler run can retry once subscriptions re-sync.
            attempted = len(subscriptions)
            if attempted > 0:
                db.add(ReminderLog(match_id=match.id))

            db.commit()

            logger.info(
                f"Reminders sent for match {team_1} vs {team_2}: "
                f"{email_count} emails, {push_count} pushes"
                + (" (no subscriptions — will retry)" if attempted == 0 else "")
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


def _run_football_fallback_for_match(match_id: int) -> None:
    """One-shot job: auto-fill predictions for a single match at kickoff."""
    from app.models.match import Match
    from app.services.fallback_job import build_prediction_inputs_from_db, run_football_fallback

    db: Session = SessionLocal()
    try:
        match = db.query(Match).get(match_id)
        if match is None:
            logger.warning(f"Football fallback: match {match_id} not found")
            return
        inputs = build_prediction_inputs_from_db(db, match)
        summary = run_football_fallback(db, match, inputs)
        logger.info(
            f"Football fallback: match {match_id} "
            f"({match.team_1.short_name} vs {match.team_2.short_name}) — "
            f"filled {summary.filled}, skipped {summary.skipped}"
        )
    except Exception as e:
        logger.error(f"Football fallback job for match {match_id} failed: {e}")
        db.rollback()
    finally:
        db.close()


def _run_lineup_sync(match_id: int) -> None:
    """One-shot job: update player availability from confirmed lineup ~1h before kickoff."""
    from app.models.match import Match
    from app.services.football_sync import get_provider
    from app.services.player_form_service import update_availability_from_lineup

    provider = get_provider()
    if not provider:
        return

    db: Session = SessionLocal()
    try:
        match = db.query(Match).get(match_id)
        if match is None or not match.external_match_id:
            return
        lineup = provider.get_fixture_lineup(int(match.external_match_id))
        if lineup is None:
            logger.info(f"Lineup not yet announced for match {match_id}")
            return
        update_availability_from_lineup(db, match, lineup)
        logger.info(f"Lineup sync done for match {match_id}")
    except Exception as e:
        logger.error(f"Lineup sync job for match {match_id} failed: {e}")
        db.rollback()
    finally:
        db.close()


def schedule_football_fallback(match) -> None:
    """Register a one-shot fallback job to fire at match.start_time.

    Safe to call for any match — silently skips non-football or past matches.
    Called at startup (for all upcoming matches) and from create_match.
    """
    from app.models.tournament import Tournament

    if not scheduler.running:
        return

    # Resolve sport — match.tournament may not be loaded yet if called pre-commit
    # so we re-query via the scheduler's own session only if needed.
    sport = None
    if match.tournament:
        sport = match.tournament.sport
    else:
        db: Session = SessionLocal()
        try:
            t = db.query(Tournament).get(match.tournament_id)
            sport = t.sport if t else None
        finally:
            db.close()

    if sport != "football":
        return

    start = match.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    if start <= now:
        return  # already past — skip (startup handles this separately)

    job_id = f"football_fallback_{match.id}"
    scheduler.add_job(
        _run_football_fallback_for_match,
        trigger="date",
        run_date=start,
        args=[match.id],
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"Scheduled fallback for match {match.id} at {start.isoformat()}")

    lineup_time = start - timedelta(hours=1)
    if lineup_time > datetime.now(timezone.utc):
        scheduler.add_job(
            _run_lineup_sync,
            trigger="date",
            run_date=lineup_time,
            args=[match.id],
            id=f"lineup_sync_{match.id}",
            replace_existing=True,
        )


def _run_football_result_sync(match_id: int) -> None:
    """One-shot job: sync result for a single match, fired ~1h after it ends.

    If the result isn't available yet (extra time / delay), retries in 30 minutes.
    """
    from app.services.football_sync import get_provider, sync_match_result

    if not get_provider():
        return

    db: Session = SessionLocal()
    try:
        result = sync_match_result(db, match_id)
        status = result.get("status")
        logger.info(f"Football result sync match {match_id}: {status}")

        if status == "not_finished":
            retry_at = datetime.now(timezone.utc) + timedelta(minutes=30)
            scheduler.add_job(
                _run_football_result_sync,
                trigger="date",
                run_date=retry_at,
                args=[match_id],
                id=f"football_result_sync_{match_id}",
                replace_existing=True,
            )
            logger.info(f"Football result sync match {match_id}: not finished — retrying at {retry_at.isoformat()}")
    except Exception as e:
        logger.error(f"Football result sync for match {match_id} failed: {e}")
        db.rollback()
    finally:
        db.close()


def schedule_football_result_sync(match) -> None:
    """Schedule a one-shot result sync for 1 hour after the match ends (~3h after kickoff).

    Safe to call for any match — silently skips if scheduler isn't running,
    match has no fixture ID, or the match is already result-synced.
    If the fire time is already past, schedules immediately (catches up missed syncs).
    """
    if not scheduler.running:
        return

    if not match.external_match_id or not match.external_match_id.lstrip("-").isdigit():
        return

    start = match.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    # Fire 3h after kickoff: ~2h for the match + 1h buffer requested by user
    fire_at = start + timedelta(hours=3)
    now = datetime.now(timezone.utc)
    if fire_at <= now:
        # Overdue — run soon (give the scheduler a few seconds to settle)
        fire_at = now + timedelta(seconds=15)

    job_id = f"football_result_sync_{match.id}"
    scheduler.add_job(
        _run_football_result_sync,
        trigger="date",
        run_date=fire_at,
        args=[match.id],
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"Scheduled result sync for match {match.id} at {fire_at.isoformat()}")


def _schedule_football_jobs_at_startup() -> None:
    """At startup, register date-triggered jobs for all upcoming and overdue football matches.

    For each football match:
    - Fallback job: fires at kickoff to auto-fill predictions
    - Result sync job: fires 3h after kickoff to score results (1h after match ends)

    Matches already past their sync time but not yet result_synced are scheduled
    immediately so results aren't missed after a server restart.
    """
    from app.models.match import Match, MatchStatus
    from app.models.tournament import Tournament

    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        matches = (
            db.query(Match)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .filter(
                Match.status == MatchStatus.SCHEDULED,
                Tournament.sport == "football",
            )
            .all()
        )

        fallbacks_scheduled = 0
        syncs_scheduled = 0

        for match in matches:
            start = match.start_time
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)

            # Fallback job — only for future matches
            if start > now:
                scheduler.add_job(
                    _run_football_fallback_for_match,
                    trigger="date",
                    run_date=start,
                    args=[match.id],
                    id=f"football_fallback_{match.id}",
                    replace_existing=True,
                )
                fallbacks_scheduled += 1

                lineup_time = start - timedelta(hours=1)
                if lineup_time > now:
                    scheduler.add_job(
                        _run_lineup_sync,
                        trigger="date",
                        run_date=lineup_time,
                        args=[match.id],
                        id=f"lineup_sync_{match.id}",
                        replace_existing=True,
                    )

            # Result sync job — for any linked match not yet result_synced
            if match.external_match_id and match.sync_state != "result_synced":
                schedule_football_result_sync(match)
                syncs_scheduled += 1

        logger.info(
            f"Startup: scheduled {fallbacks_scheduled} fallback jobs, "
            f"{syncs_scheduled} result sync jobs for football matches"
        )
    except Exception as e:
        logger.error(f"Failed to schedule football jobs at startup: {e}")
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

    # Football — register provider; per-match jobs are scheduled below
    if settings.FOOTBALL_API_KEY:
        from app.services.football_provider import ApiFootballProvider
        from app.services.football_sync import set_provider as set_football_provider
        set_football_provider(ApiFootballProvider(settings.FOOTBALL_API_KEY, settings.FOOTBALL_API_BASE_URL))
        logger.info("Football provider configured")
    else:
        logger.info("FOOTBALL_API_KEY not set — football sync skipped")

    scheduler.start()
    logger.info("Scheduler started")

    # Schedule one-shot fallback + result-sync jobs for all football matches.
    # Must run after scheduler.start() so add_job is accepted.
    _schedule_football_jobs_at_startup()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
