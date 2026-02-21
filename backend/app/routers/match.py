from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.database import get_db
from app.models import User, MatchLineup
from app.schemas.match import (
    MatchResponse,
    MatchDetailResponse,
    MatchPlayersResponse,
    TeamResponse,
    PlayerResponse,
)
from app.services.auth import get_current_user
from app.services.match import (
    get_upcoming_matches,
    get_match_by_id,
    get_match_players,
)

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/", response_model=list[MatchResponse])
async def list_matches(
    tournament_id: int | None = Query(None, description="Filter by tournament ID"),
    include_completed: bool = Query(False, description="Include completed matches"),
    db: Session = Depends(get_db),
):
    """
    List matches.
    
    By default returns only upcoming (scheduled) matches.
    Use `include_completed=true` to include completed matches.
    Optionally filter by `tournament_id`.
    """
    matches = get_upcoming_matches(
        db, 
        tournament_id=tournament_id, 
        include_all=include_completed
    )
    
    # Get match IDs that have lineups set (single query)
    match_ids = [m.id for m in matches]
    lineup_match_ids = set()
    if match_ids:
        rows = db.query(MatchLineup.match_id).filter(
            MatchLineup.match_id.in_(match_ids)
        ).distinct().all()
        lineup_match_ids = {r[0] for r in rows}

    # Convert to response format with team objects
    result = []
    for match in matches:
        result.append(MatchResponse(
            id=match.id,
            tournament_id=match.tournament_id,
            team_1=TeamResponse.model_validate(match.team_1),
            team_2=TeamResponse.model_validate(match.team_2),
            start_time=match.start_time,
            status=match.status.value,
            lineup_announced=match.id in lineup_match_ids,
        ))

    return result


@router.get("/{match_id}", response_model=MatchDetailResponse)
async def get_match_detail(
    match_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed match info including results for completed matches.
    """
    match = get_match_by_id(db, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    return MatchDetailResponse(
        id=match.id,
        tournament_id=match.tournament_id,
        team_1=TeamResponse.model_validate(match.team_1),
        team_2=TeamResponse.model_validate(match.team_2),
        start_time=match.start_time,
        status=match.status.value,
        winner=TeamResponse.model_validate(match.winner) if match.winner else None,
        most_runs_player=PlayerResponse.model_validate(match.most_runs_player) if match.most_runs_player else None,
        most_wickets_player=PlayerResponse.model_validate(match.most_wickets_player) if match.most_wickets_player else None,
        pom_player=PlayerResponse.model_validate(match.pom_player) if match.pom_player else None,
    )


@router.get("/{match_id}/players", response_model=MatchPlayersResponse)
async def get_players_for_match(
    match_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all players from both teams in a match.
    
    Used for populating dropdowns in the prediction form.
    """
    match = get_match_by_id(db, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )
    
    players_result = get_match_players(db, match_id)
    if not players_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    team_1_players, team_2_players, lineup_announced = players_result

    return MatchPlayersResponse(
        match_id=match.id,
        team_1=TeamResponse.model_validate(match.team_1),
        team_2=TeamResponse.model_validate(match.team_2),
        team_1_players=[PlayerResponse.model_validate(p) for p in team_1_players],
        team_2_players=[PlayerResponse.model_validate(p) for p in team_2_players],
        lineup_announced=lineup_announced,
    )
