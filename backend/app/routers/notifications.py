"""Push notification subscription endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.push_subscription import PushSubscription
from app.services.auth import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PushSubscribeRequest(BaseModel):
    endpoint: str
    auth: str
    p256dh: str


@router.get("/vapid-public-key")
def get_vapid_public_key():
    """Return the VAPID public key for the frontend to use when subscribing."""
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/push/subscribe", status_code=201)
def subscribe(
    body: PushSubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a push subscription for the current user."""
    existing = db.query(PushSubscription).filter_by(endpoint=body.endpoint).first()
    if existing:
        return {"status": "already_subscribed"}

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=body.endpoint,
        auth=body.auth,
        p256dh=body.p256dh,
    )
    db.add(sub)
    db.commit()
    return {"status": "subscribed"}


@router.delete("/push/subscribe")
def unsubscribe(
    body: PushSubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a push subscription."""
    db.query(PushSubscription).filter_by(
        endpoint=body.endpoint,
        user_id=current_user.id,
    ).delete()
    db.commit()
    return {"status": "unsubscribed"}
