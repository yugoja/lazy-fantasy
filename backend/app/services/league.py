import secrets
import string

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import League, LeagueMember, Match, User, Prediction


def generate_invite_code(length: int = 6) -> str:
    """Generate a random alphanumeric invite code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_league_by_id(db: Session, league_id: int) -> League | None:
    """Get league by ID."""
    return db.query(League).filter(League.id == league_id).first()


def get_league_by_invite_code(db: Session, invite_code: str) -> League | None:
    """Get league by invite code."""
    return db.query(League).filter(League.invite_code == invite_code).first()


def get_user_leagues(db: Session, user_id: int) -> list[League]:
    """Get all leagues a user is a member of."""
    return (
        db.query(League)
        .join(LeagueMember)
        .filter(LeagueMember.user_id == user_id)
        .all()
    )


def is_user_in_league(db: Session, user_id: int, league_id: int) -> bool:
    """Check if user is a member of a league."""
    return (
        db.query(LeagueMember)
        .filter(LeagueMember.user_id == user_id, LeagueMember.league_id == league_id)
        .first()
        is not None
    )


def create_league(db: Session, name: str, owner_id: int) -> League:
    """Create a new league."""
    # Generate unique invite code
    while True:
        invite_code = generate_invite_code()
        if not get_league_by_invite_code(db, invite_code):
            break

    league = League(
        name=name,
        invite_code=invite_code,
        owner_id=owner_id,
    )
    db.add(league)
    db.flush()

    # Add owner as a member
    member = LeagueMember(league_id=league.id, user_id=owner_id)
    db.add(member)
    db.commit()
    db.refresh(league)
    return league


def join_league(db: Session, user_id: int, league_id: int) -> LeagueMember:
    """Add a user to a league."""
    member = LeagueMember(league_id=league_id, user_id=user_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def get_league_leaderboard(
    db: Session, league_id: int
) -> list[tuple[int, str, int]]:
    """
    Get leaderboard for a league.
    Returns list of (user_id, username, total_points) sorted by points descending.
    Only counts predictions for matches that started after the league was created.
    """
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        return []

    # Get all members of the league
    members = (
        db.query(LeagueMember.user_id)
        .filter(LeagueMember.league_id == league_id)
        .subquery()
    )

    # Subquery: eligible predictions (match started after league creation)
    eligible_predictions = (
        db.query(Prediction.user_id, Prediction.points_earned)
        .join(Match, Prediction.match_id == Match.id)
        .filter(Match.start_time >= league.created_at)
        .subquery()
    )

    # Calculate total points per user from eligible predictions only
    results = (
        db.query(
            User.id,
            User.username,
            func.coalesce(func.sum(eligible_predictions.c.points_earned), 0).label(
                "total_points"
            ),
        )
        .join(members, User.id == members.c.user_id)
        .outerjoin(
            eligible_predictions,
            User.id == eligible_predictions.c.user_id,
        )
        .group_by(User.id, User.username)
        .order_by(
            func.coalesce(func.sum(eligible_predictions.c.points_earned), 0).desc()
        )
        .all()
    )

    return results
