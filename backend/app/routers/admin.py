from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Match, MatchStatus, Team, Tournament, Player, User
from app.schemas.admin import MatchCreate, MatchResultCreate
from app.schemas.match import MatchResponse, TeamResponse
from app.services.auth import get_current_user
from app.services.scoring import calculate_scores

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/matches/", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
async def create_match(
    match_data: MatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new match (Admin).
    
    Note: In a production app, this should be restricted to admin users.
    """
    # Validate tournament exists
    tournament = db.query(Tournament).filter(Tournament.id == match_data.tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )
    
    # Validate teams exist
    team_1 = db.query(Team).filter(Team.id == match_data.team_1_id).first()
    team_2 = db.query(Team).filter(Team.id == match_data.team_2_id).first()
    if not team_1 or not team_2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or both teams not found",
        )
    
    if team_1.id == team_2.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team cannot play against itself",
        )
    
    # Ensure start_time is timezone-aware (UTC)
    start_time = match_data.start_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    
    # Create match
    match = Match(
        tournament_id=match_data.tournament_id,
        team_1_id=match_data.team_1_id,
        team_2_id=match_data.team_2_id,
        start_time=start_time,
        status=MatchStatus.SCHEDULED,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    
    return MatchResponse(
        id=match.id,
        tournament_id=match.tournament_id,
        team_1=TeamResponse.model_validate(team_1),
        team_2=TeamResponse.model_validate(team_2),
        start_time=match.start_time,
        status=match.status.value,
    )


@router.post("/matches/{match_id}/result")
async def set_match_result(
    match_id: int,
    result_data: MatchResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Set match results and trigger score calculation (Admin).
    
    This endpoint:
    1. Updates the match with results
    2. Sets match status to COMPLETED
    3. Triggers automatic score calculation for all predictions
    
    Note: In a production app, this should be restricted to admin users.
    """
    # Get match
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )
    
    if match.status == MatchStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match results have already been set",
        )
    
    # Validate winner is one of the match teams
    if result_data.result_winner_id not in [match.team_1_id, match.team_2_id]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Winner must be one of the match teams",
        )
    
    # Validate players exist and belong to match teams
    valid_team_ids = {match.team_1_id, match.team_2_id}
    player_ids = [
        result_data.result_most_runs_player_id,
        result_data.result_most_wickets_player_id,
        result_data.result_pom_player_id,
    ]
    
    for player_id in player_ids:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player with ID {player_id} not found",
            )
        if player.team_id not in valid_team_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player {player.name} is not in either team",
            )
    
    # Update match with results
    match.result_winner_id = result_data.result_winner_id
    match.result_most_runs_player_id = result_data.result_most_runs_player_id
    match.result_most_wickets_player_id = result_data.result_most_wickets_player_id
    match.result_pom_player_id = result_data.result_pom_player_id
    match.status = MatchStatus.COMPLETED
    
    db.commit()
    
    # Calculate scores for all predictions
    predictions_processed = calculate_scores(db, match_id)
    
    return {
        "message": "Match results set successfully",
        "match_id": match_id,
        "status": "COMPLETED",
        "predictions_processed": predictions_processed,
    }


@router.get("/matches")
async def list_all_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all matches with their status (Admin).
    """
    from app.models import Prediction
    
    matches = db.query(Match).order_by(Match.start_time).all()
    
    result = []
    for match in matches:
        prediction_count = db.query(Prediction).filter(Prediction.match_id == match.id).count()
        result.append({
            "id": match.id,
            "tournament_id": match.tournament_id,
            "team_1": {"id": match.team_1.id, "name": match.team_1.name, "short_name": match.team_1.short_name},
            "team_2": {"id": match.team_2.id, "name": match.team_2.name, "short_name": match.team_2.short_name},
            "start_time": match.start_time.isoformat(),
            "status": match.status.value,
            "prediction_count": prediction_count,
        })
    
    return result


@router.get("/matches/{match_id}/predictions")
async def get_match_predictions(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all predictions for a specific match (Admin).
    """
    from app.models import Prediction
    
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )
    
    predictions = db.query(Prediction).filter(Prediction.match_id == match_id).all()
    
    result = []
    for pred in predictions:
        user = db.query(User).filter(User.id == pred.user_id).first()
        
        # Get player names
        winner_team = db.query(Team).filter(Team.id == pred.predicted_winner_id).first()
        most_runs_player = db.query(Player).filter(Player.id == pred.predicted_most_runs_player_id).first()
        most_wickets_player = db.query(Player).filter(Player.id == pred.predicted_most_wickets_player_id).first()
        pom_player = db.query(Player).filter(Player.id == pred.predicted_pom_player_id).first()
        
        result.append({
            "id": pred.id,
            "user_id": pred.user_id,
            "username": user.username if user else "Unknown",
            "predicted_winner": winner_team.name if winner_team else "Unknown",
            "predicted_most_runs": most_runs_player.name if most_runs_player else "Unknown",
            "predicted_most_wickets": most_wickets_player.name if most_wickets_player else "Unknown",
            "predicted_pom": pom_player.name if pom_player else "Unknown",
            "points_earned": pred.points_earned,
            "is_processed": pred.is_processed,
        })
    
    return {
        "match_id": match_id,
        "team_1": {"id": match.team_1.id, "name": match.team_1.name, "short_name": match.team_1.short_name},
        "team_2": {"id": match.team_2.id, "name": match.team_2.name, "short_name": match.team_2.short_name},
        "status": match.status.value,
        "predictions": result,
    }

