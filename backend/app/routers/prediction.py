from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Team
from app.schemas.prediction import PredictionCreate, PredictionResponse, PredictionDetailResponse
from app.schemas.match import TeamResponse, PlayerResponse
from app.services.auth import get_current_user
from app.services.prediction import (
    can_submit_prediction,
    create_prediction,
    get_prediction_by_user_and_match,
    get_user_predictions,
    update_prediction,
    validate_prediction_players,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def submit_prediction(
    prediction_data: PredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit a prediction for a match.

    Predictions can only be submitted before the match starts (UTC).
    If a prediction already exists for this match, it will be updated.

    **Scoring:**
    - Winner: +10 pts
    - Most Runs (Team 1): +20 pts
    - Most Runs (Team 2): +20 pts
    - Most Wickets (Team 1): +20 pts
    - Most Wickets (Team 2): +20 pts
    - Player of Match: +50 pts
    - Max total: 140 pts
    """
    # Check if predictions are still open
    can_submit, reason = can_submit_prediction(db, prediction_data.match_id)
    if not can_submit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason,
        )

    # Validate winner team
    winner_team = db.query(Team).filter(Team.id == prediction_data.predicted_winner_id).first()
    if not winner_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid winner team ID",
        )

    # Validate players with per-team constraints
    is_valid, error = validate_prediction_players(
        db,
        prediction_data.match_id,
        team1_player_ids=[
            prediction_data.predicted_most_runs_team1_player_id,
            prediction_data.predicted_most_wickets_team1_player_id,
        ],
        team2_player_ids=[
            prediction_data.predicted_most_runs_team2_player_id,
            prediction_data.predicted_most_wickets_team2_player_id,
        ],
        either_team_player_ids=[
            prediction_data.predicted_pom_player_id,
        ],
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    # Check for existing prediction
    existing = get_prediction_by_user_and_match(
        db, current_user.id, prediction_data.match_id
    )

    if existing:
        prediction = update_prediction(
            db,
            existing,
            prediction_data.predicted_winner_id,
            prediction_data.predicted_most_runs_team1_player_id,
            prediction_data.predicted_most_runs_team2_player_id,
            prediction_data.predicted_most_wickets_team1_player_id,
            prediction_data.predicted_most_wickets_team2_player_id,
            prediction_data.predicted_pom_player_id,
        )
    else:
        prediction = create_prediction(
            db,
            current_user.id,
            prediction_data.match_id,
            prediction_data.predicted_winner_id,
            prediction_data.predicted_most_runs_team1_player_id,
            prediction_data.predicted_most_runs_team2_player_id,
            prediction_data.predicted_most_wickets_team1_player_id,
            prediction_data.predicted_most_wickets_team2_player_id,
            prediction_data.predicted_pom_player_id,
        )

    return prediction


@router.get("/my", response_model=list[PredictionResponse])
async def get_my_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all predictions made by the current user (raw IDs).
    """
    predictions = get_user_predictions(db, current_user.id)
    return predictions


@router.get("/my/detailed", response_model=list[PredictionDetailResponse])
async def get_my_predictions_detailed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all predictions with match context, player names, and actual results.
    """
    predictions = get_user_predictions(db, current_user.id)
    result = []
    for pred in predictions:
        match = pred.match
        result.append(PredictionDetailResponse(
            id=pred.id,
            match_id=pred.match_id,
            points_earned=pred.points_earned,
            is_processed=pred.is_processed,
            team_1=TeamResponse.model_validate(match.team_1),
            team_2=TeamResponse.model_validate(match.team_2),
            start_time=match.start_time,
            status=match.status.value,
            predicted_winner=TeamResponse.model_validate(pred.predicted_winner),
            predicted_most_runs_team1_player=PlayerResponse.model_validate(pred.predicted_most_runs_team1_player),
            predicted_most_runs_team2_player=PlayerResponse.model_validate(pred.predicted_most_runs_team2_player),
            predicted_most_wickets_team1_player=PlayerResponse.model_validate(pred.predicted_most_wickets_team1_player),
            predicted_most_wickets_team2_player=PlayerResponse.model_validate(pred.predicted_most_wickets_team2_player),
            predicted_pom_player=PlayerResponse.model_validate(pred.predicted_pom_player),
            actual_winner=TeamResponse.model_validate(match.winner) if match.winner else None,
            actual_most_runs_team1_player=PlayerResponse.model_validate(match.most_runs_team1_player) if match.most_runs_team1_player else None,
            actual_most_runs_team2_player=PlayerResponse.model_validate(match.most_runs_team2_player) if match.most_runs_team2_player else None,
            actual_most_wickets_team1_player=PlayerResponse.model_validate(match.most_wickets_team1_player) if match.most_wickets_team1_player else None,
            actual_most_wickets_team2_player=PlayerResponse.model_validate(match.most_wickets_team2_player) if match.most_wickets_team2_player else None,
            actual_pom_player=PlayerResponse.model_validate(match.pom_player) if match.pom_player else None,
        ))
    return result
