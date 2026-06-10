import secrets
import string

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import League, LeagueMember, Match, User, Prediction, Tournament, TournamentPick

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
    """Get all leagues a user is a member of (excludes archived)."""
    return (
        db.query(League)
        .join(LeagueMember)
        .filter(LeagueMember.user_id == user_id, League.is_archived == False)
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


def _get_tournament_pick_points(db: Session, league_created_at, sport: str) -> dict:
    """
    Returns {user_id: total_tournament_pick_points} for processed picks in
    tournaments of the given sport that started after the league was created.
    Scoped by sport so e.g. football mega-picks only count in football leagues.
    """
    rows = (
        db.query(TournamentPick.user_id, func.sum(TournamentPick.points_earned))
        .join(Tournament, TournamentPick.tournament_id == Tournament.id)
        .filter(
            TournamentPick.is_processed == True,
            Tournament.start_date >= league_created_at,
            Tournament.sport == sport,
        )
        .group_by(TournamentPick.user_id)
        .all()
    )
    return {user_id: pts for user_id, pts in rows}


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

    # Add tournament pick points
    tp_points = _get_tournament_pick_points(db, league.created_at, league.sport)
    totals = [(user_id, pts + tp_points.get(user_id, 0)) for user_id, pts in results]
    totals.sort(key=lambda x: x[1], reverse=True)

    # Standard competition ranking: tied users share the same rank,
    # and the next rank skips accordingly (1, 2, 2, 4 — not 1, 2, 3, 4).
    ranked = []
    for i, (user_id, pts) in enumerate(totals):
        if i == 0 or pts != totals[i - 1][1]:
            rank = i + 1
        ranked.append((user_id, rank))
    return ranked


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


_ROUND_ORDER = ["GROUP_1", "GROUP_2", "GROUP_3", "R32", "R16", "QF", "SF", "THIRD", "FINAL"]


def _get_available_rounds(db: Session, league_created_at) -> list[str]:
    """Return round keys that have at least one COMPLETED match after league creation."""
    from app.models.match import MatchStatus
    rows = (
        db.query(Match.stage, Match.group_round)
        .filter(
            Match.start_time >= league_created_at,
            Match.status == MatchStatus.COMPLETED,
            Match.stage.isnot(None),
        )
        .distinct()
        .all()
    )
    found: set[str] = set()
    for stage, group_round in rows:
        if stage == "GROUP" and group_round is not None:
            found.add(f"GROUP_{group_round}")
        elif stage != "GROUP":
            found.add(stage)
    return [r for r in _ROUND_ORDER if r in found]


def _round_filter_clause(round_key: str) -> tuple:
    """Return SQLAlchemy filter clauses for a given round key."""
    if round_key.startswith("GROUP_"):
        n = int(round_key.split("_")[1])
        return (Match.stage == "GROUP", Match.group_round == n)
    return (Match.stage == round_key,)


def get_league_leaderboard(
    db: Session, league_id: int, round_key: str | None = None
) -> list[tuple[int, str, int]]:
    """
    Get leaderboard for a league.
    Returns list of (user_id, username, display_name, total_points, prev_rank) sorted by points descending.
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

    pred_query = (
        db.query(Prediction.user_id, Prediction.points_earned)
        .join(Match, Prediction.match_id == Match.id)
        .filter(Match.start_time >= league.created_at)
    )
    if round_key:
        pred_query = pred_query.filter(*_round_filter_clause(round_key))
    eligible_predictions = pred_query.subquery()

    results = (
        db.query(
            User.id,
            User.username,
            User.display_name,
            User.avatar_url,
            func.coalesce(func.sum(eligible_predictions.c.points_earned), 0).label(
                "total_points"
            ),
        )
        .join(members, User.id == members.c.user_id)
        .outerjoin(
            eligible_predictions,
            User.id == eligible_predictions.c.user_id,
        )
        .group_by(User.id, User.username, User.display_name, User.avatar_url)
        .order_by(
            func.coalesce(func.sum(eligible_predictions.c.points_earned), 0).desc()
        )
        .all()
    )

    if round_key:
        # Tournament picks have no per-round granularity; rank deltas are meaningless
        augmented = [
            (user_id, username, display_name, avatar_url, total_points)
            for user_id, username, display_name, avatar_url, total_points in results
        ]
        augmented.sort(key=lambda x: x[4], reverse=True)
        return [(user_id, username, display_name, avatar_url, total_points, None)
                for user_id, username, display_name, avatar_url, total_points in augmented]

    # Add tournament pick points and re-sort
    tp_points = _get_tournament_pick_points(db, league.created_at, league.sport)
    augmented = [
        (user_id, username, display_name, avatar_url, total_points + tp_points.get(user_id, 0))
        for user_id, username, display_name, avatar_url, total_points in results
    ]
    augmented.sort(key=lambda x: x[4], reverse=True)

    # Attach prev_rank to each result row
    return [(user_id, username, display_name, avatar_url, total_points, prev_rank_map.get(user_id))
            for user_id, username, display_name, avatar_url, total_points in augmented]
