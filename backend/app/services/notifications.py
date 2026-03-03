"""Email and push notification sending."""
import json
import logging

import resend
from pywebpush import webpush, WebPushException

from app.config import settings

logger = logging.getLogger(__name__)


def send_reminder_email(user_email: str, team_1: str, team_2: str, match_time: str) -> bool:
    """Send a match reminder email via Resend. Returns True on success."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email reminder")
        return False

    resend.api_key = settings.RESEND_API_KEY
    app_url = settings.FRONTEND_URL

    html = f"""
    <div style="font-family:Inter,sans-serif;background:#0a0a0f;color:#e8e8e6;max-width:480px;margin:0 auto;padding:32px 24px;border-radius:16px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:28px;">
        <span style="font-size:20px;">🏆</span>
        <span style="font-size:17px;font-weight:700;color:#e8e8e6;">Lazy Fantasy</span>
      </div>
      <p style="font-size:13px;font-weight:600;color:#26d666;letter-spacing:0.08em;text-transform:uppercase;margin:0 0 12px;">Match Reminder</p>
      <h1 style="font-size:26px;font-weight:700;color:#e8e8e6;margin:0 0 8px;line-height:1.2;">
        {team_1} vs {team_2}
      </h1>
      <p style="font-size:15px;color:#6b7280;margin:0 0 28px;">Starts in 1 hour · {match_time}</p>
      <p style="font-size:15px;color:#e8e8e6;margin:0 0 24px;line-height:1.6;">
        Don't miss out — lock in your prediction before the match starts.
      </p>
      <a href="{app_url}/predictions" style="display:inline-block;background:#26d666;color:#0a0a0f;font-weight:700;font-size:15px;padding:14px 28px;border-radius:10px;text-decoration:none;">
        Predict Now →
      </a>
      <p style="font-size:12px;color:#6b7280;margin-top:32px;">
        You're receiving this because you have an account on Lazy Fantasy.
      </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": "Lazy Fantasy <reminders@lazyfantasy.app>",
            "to": [user_email],
            "subject": f"⏰ {team_1} vs {team_2} starts in 1 hour — predict now!",
            "html": html,
        })
        return True
    except Exception as e:
        logger.error(f"Failed to send reminder email to {user_email}: {e}")
        return False


def send_push_notification(endpoint: str, auth: str, p256dh: str, team_1: str, team_2: str) -> bool:
    """Send a Web Push notification. Returns True on success."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_CLAIMS_EMAIL:
        logger.warning("VAPID keys not configured — skipping push notification")
        return False

    app_url = settings.FRONTEND_URL
    payload = json.dumps({
        "title": f"⏰ {team_1} vs {team_2} in 1 hour!",
        "body": "Lock in your prediction before it's too late.",
        "url": f"{app_url}/predictions",
    })

    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"auth": auth, "p256dh": p256dh},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
        )
        return True
    except WebPushException as e:
        # 410 Gone means the subscription is no longer valid
        if "410" in str(e):
            logger.info(f"Push subscription expired (410): {endpoint[:50]}...")
        else:
            logger.error(f"Push notification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Push notification error: {e}")
        return False
