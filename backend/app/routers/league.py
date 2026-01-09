from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.league import (
    LeagueCreate,
    LeagueResponse,
    LeagueJoin,
    LeaderboardEntry,
    LeaderboardResponse,
)
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
    league = create_league(db, league_data.name, current_user.id)
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

    # Build response with ranks
    entries = [
        LeaderboardEntry(
            user_id=user_id,
            username=username,
            total_points=int(total_points),
            rank=idx + 1,
        )
        for idx, (user_id, username, total_points) in enumerate(leaderboard_data)
    ]

    return LeaderboardResponse(
        league_id=league.id,
        league_name=league.name,
        entries=entries,
    )
