from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.dugout_dismissal import DugoutDismissal
from app.schemas.dugout import DugoutEvent, DugoutDismissRequest
from app.services.auth import get_current_user
from app.services.dugout import get_dugout_events

router = APIRouter(prefix="/dugout", tags=["dugout"])


@router.get("/", response_model=list[DugoutEvent])
async def get_dugout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dugout_events(db, current_user.id)


@router.post("/dismiss", status_code=204)
async def dismiss_dugout_event(
    body: DugoutDismissRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match_id = body.match_id if body.match_id is not None else 0
    existing = db.query(DugoutDismissal).filter(
        DugoutDismissal.user_id == current_user.id,
        DugoutDismissal.type == body.type,
        DugoutDismissal.league_id == body.league_id,
        DugoutDismissal.match_id == match_id,
        DugoutDismissal.subject_username == body.subject_username,
    ).first()
    if not existing:
        db.add(DugoutDismissal(
            user_id=current_user.id,
            type=body.type,
            league_id=body.league_id,
            match_id=match_id,
            subject_username=body.subject_username,
        ))
        db.commit()
