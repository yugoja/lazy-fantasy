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


def create_league(db: Session, name: str, owner_id: int, sport: str = "cricket") -> League:
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
        sport=sport,
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


def _compute_standings(db: Session, league_id: int) -> list[tuple[int, int]]:
    """
    Compute current standings for a league.
    Returns list of (user_id, rank) sorted by points descending.
    """
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        return []

    members = (
        db.query(LeagueMember.user_id)
        .filter(LeagueMember.league_id == league_id)
        .subquery()
    )

    eligible_predictions = (
        db.query(Prediction.user_id, Prediction.points_earned)
        .join(Match, Prediction.match_id == Match.id)
        .filter(Match.start_time >= league.created_at)
        .subquery()
    )

    results = (
        db.query(
            User.id,
            func.coalesce(func.sum(eligible_predictions.c.points_earned), 0).label("total_points"),
        )
        .join(members, User.id == members.c.user_id)
        .outerjoin(eligible_predictions, User.id == eligible_predictions.c.user_id)
        .group_by(User.id)
        .order_by(func.coalesce(func.sum(eligible_predictions.c.points_earned), 0).desc())
        .all()
    )

    return [(user_id, rank + 1) for rank, (user_id, _) in enumerate(results)]


def snapshot_league_ranks(db: Session, match_id: int) -> None:
    """
    Snapshot current rank of every league member into prev_rank, for leagues
    that have at least one member who predicted this match. Called before scoring
    so the frontend can show rank deltas after results land.
    """
    # Find all users who predicted this match
    predictor_ids = [
        uid for (uid,) in db.query(Prediction.user_id)
        .filter(Prediction.match_id == match_id)
        .distinct()
        .all()
    ]
    if not predictor_ids:
        return

    # Find all leagues those users belong to
    league_ids = [
        lid for (lid,) in db.query(LeagueMember.league_id)
        .filter(LeagueMember.user_id.in_(predictor_ids))
        .distinct()
        .all()
    ]

    for league_id in league_ids:
        standings = _compute_standings(db, league_id)
        for user_id, rank in standings:
            db.query(LeagueMember).filter(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == user_id,
            ).update({"prev_rank": rank})
    db.commit()


def get_league_leaderboard(
    db: Session, league_id: int
) -> list[tuple[int, str, int]]:
    """
    Get leaderboard for a league.
    Returns list of (user_id, username, total_points) sorted by points descending.
    Only counts predictions for events that started after the league was created.
    """
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        return []

    # Get all members with their prev_rank
    member_rows = (
        db.query(LeagueMember.user_id, LeagueMember.prev_rank)
        .filter(LeagueMember.league_id == league_id)
        .all()
    )
    prev_rank_map = {user_id: prev_rank for user_id, prev_rank in member_rows}
    members = (
        db.query(LeagueMember.user_id)
        .filter(LeagueMember.league_id == league_id)
        .subquery()
    )

    eligible_predictions = (
        db.query(Prediction.user_id, Prediction.points_earned)
        .join(Match, Prediction.match_id == Match.id)
        .filter(Match.start_time >= league.created_at)
        .subquery()
    )

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

    # Attach prev_rank to each result row
    return [(user_id, username, total_points, prev_rank_map.get(user_id)) for user_id, username, total_points in results]
