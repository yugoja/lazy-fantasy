from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Match, Prediction, Player, Team
from app.schemas.league import (
    LeagueCreate,
    LeagueResponse,
    LeagueJoin,
    LeaderboardEntry,
    LeaderboardResponse,
)
from app.schemas.prediction import FriendPrediction
from app.schemas.match import TeamResponse, PlayerResponse
from app.services.auth import get_current_user
from app.services.league import (
    create_league,
    get_league_by_id,
    get_league_by_invite_code,
    get_league_leaderboard,
    get_user_leagues,
    is_user_in_league,
    join_league,
)
from app.models.league import LeagueMember

router = APIRouter(prefix="/leagues", tags=["leagues"])


@router.post("/", response_model=LeagueResponse, status_code=status.HTTP_201_CREATED)
async def create_new_league(
    league_data: LeagueCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new league.

    The current user becomes the owner and is automatically added as a member.
    A unique 6-character invite code is generated.
    """
    league = create_league(db, league_data.name, current_user.id, sport=league_data.sport)
    return league


@router.post("/join", response_model=LeagueResponse)
async def join_existing_league(
    join_data: LeagueJoin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Join a league using an invite code.
    """
    # Find league by invite code
    league = get_league_by_invite_code(db, join_data.invite_code.upper())
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found with this invite code",
        )

    # Check if already a member
    if is_user_in_league(db, current_user.id, league.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this league",
        )

    # Join the league
    join_league(db, current_user.id, league.id)
    return league


@router.get("/my", response_model=list[LeagueResponse])
async def get_my_leagues(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all leagues the current user is a member of.
    """
    leagues = get_user_leagues(db, current_user.id)
    return leagues


@router.get("/{league_id}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    league_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the leaderboard for a specific league.

    Only members of the league can view the leaderboard.
    """
    # Check if league exists
    league = get_league_by_id(db, league_id)
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found",
        )

    # Check if user is a member
    if not is_user_in_league(db, current_user.id, league_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this league",
        )

    # Get leaderboard data
    leaderboard_data = get_league_leaderboard(db, league_id)

    # Build response with ranks and deltas
    entries = []
    for idx, (user_id, username, total_points, prev_rank) in enumerate(leaderboard_data):
        current_rank = idx + 1
        rank_delta = (prev_rank - current_rank) if prev_rank is not None else None
        entries.append(LeaderboardEntry(
            user_id=user_id,
            username=username,
            total_points=int(total_points),
            rank=current_rank,
            rank_delta=rank_delta,
        ))

    return LeaderboardResponse(
        league_id=league.id,
        league_name=league.name,
        entries=entries,
    )


@router.get("/{league_id}/matches/{match_id}/predictions", response_model=list[FriendPrediction])
async def get_league_match_predictions(
    league_id: int,
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all league members' predictions for a locked match.
    Only accessible after the match's prediction window has closed (start_time has passed).
    """
    league = get_league_by_id(db, league_id)
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found")

    if not is_user_in_league(db, current_user.id, league_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this league")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    match_start = match.start_time if match.start_time.tzinfo else match.start_time.replace(tzinfo=timezone.utc)
    if match_start > datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Predictions are still open — check back after the match starts")

    # Get all member user_ids in this league
    member_ids = [
        uid for (uid,) in db.query(LeagueMember.user_id)
        .filter(LeagueMember.league_id == league_id)
        .all()
    ]

    # Get all predictions for this match from league members
    preds = (
        db.query(Prediction, User)
        .join(User, Prediction.user_id == User.id)
        .filter(Prediction.match_id == match_id, Prediction.user_id.in_(member_ids))
        .all()
    )

    def get_team(team_id: int | None) -> TeamResponse | None:
        if team_id is None:
            return None
        t = db.query(Team).filter(Team.id == team_id).first()
        return TeamResponse.model_validate(t) if t else None

    def get_player(player_id: int | None) -> PlayerResponse | None:
        if player_id is None:
            return None
        p = db.query(Player).filter(Player.id == player_id).first()
        return PlayerResponse.model_validate(p) if p else None

    results = []
    for pred, user in preds:
        entry = FriendPrediction(
            username=user.username,
            is_me=(user.id == current_user.id),
            points_earned=pred.points_earned,
            is_processed=pred.is_processed,
            predicted_winner=get_team(pred.predicted_winner_id),
            predicted_most_runs_team1_player=get_player(pred.predicted_most_runs_team1_player_id),
            predicted_most_runs_team2_player=get_player(pred.predicted_most_runs_team2_player_id),
            predicted_most_wickets_team1_player=get_player(pred.predicted_most_wickets_team1_player_id),
            predicted_most_wickets_team2_player=get_player(pred.predicted_most_wickets_team2_player_id),
            predicted_pom_player=get_player(pred.predicted_pom_player_id),
            actual_winner=get_team(match.result_winner_id),
            actual_most_runs_team1_player=get_player(match.result_most_runs_team1_player_id),
            actual_most_runs_team2_player=get_player(match.result_most_runs_team2_player_id),
            actual_most_wickets_team1_player=get_player(match.result_most_wickets_team1_player_id),
            actual_most_wickets_team2_player=get_player(match.result_most_wickets_team2_player_id),
            actual_pom_player=get_player(match.result_pom_player_id),
        )
        results.append(entry)

    # Current user first, then sort by points desc (processed) or username (unprocessed)
    results.sort(key=lambda x: (not x.is_me, -x.points_earned if x.is_processed else 0, x.username))
    return results
