from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Match, User, Team
from app.schemas.prediction import (
    FootballPlayerPickDetail,
    FootballPredictionCreate,
    FootballPredictionDetailResponse,
    FootballPredictionResponse,
    PredictionCreate,
    PredictionResponse,
    PredictionDetailResponse,
)
from app.schemas.match import TeamResponse, PlayerResponse
from app.services.auth import get_current_user
from app.services.prediction import (
    can_submit_prediction,
    create_football_prediction,
    create_prediction,
    get_prediction_by_user_and_match,
    get_user_predictions,
    update_football_prediction,
    update_prediction,
    validate_prediction_players,
)
from app.services.scoring import football_score_breakdown
from app.services.scoring_football import KNOCKOUT_STAGES

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


@router.post(
    "/football",
    response_model=FootballPredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_football_prediction(
    prediction_data: FootballPredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit a football prediction for a match (scoreline + 3 player picks).

    Predictions can only be submitted before kickoff. An existing prediction
    for this match is updated. `advance_winner_id` is required only when the
    predicted scoreline is a draw in a knockout match.
    """
    can_submit, reason = can_submit_prediction(db, prediction_data.match_id)
    if not can_submit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    match = db.query(Match).filter(Match.id == prediction_data.match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if not match.tournament or match.tournament.sport != "football":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for football matches",
        )

    is_knockout = (match.stage or "") in KNOCKOUT_STAGES
    is_draw_pred = prediction_data.team1_goals == prediction_data.team2_goals

    # advance_winner only matters for a knockout draw; required there, else null.
    advance_winner_id: int | None = None
    if is_knockout and is_draw_pred:
        if prediction_data.advance_winner_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="advance_winner_id is required for a draw prediction in a knockout match",
            )
        if prediction_data.advance_winner_id not in (match.team_1_id, match.team_2_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="advance_winner_id must be one of the match teams",
            )
        advance_winner_id = prediction_data.advance_winner_id

    picks = (
        prediction_data.player_pick_1_id,
        prediction_data.player_pick_2_id,
        prediction_data.player_pick_3_id,
    )
    if len(set(picks)) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The three player picks must be distinct",
        )

    # Both squads are pooled for player picks.
    is_valid, error = validate_prediction_players(
        db,
        prediction_data.match_id,
        team1_player_ids=[],
        team2_player_ids=[],
        either_team_player_ids=list(picks),
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    existing = get_prediction_by_user_and_match(
        db, current_user.id, prediction_data.match_id
    )
    if existing:
        prediction = update_football_prediction(
            db, existing, prediction_data.team1_goals, prediction_data.team2_goals,
            advance_winner_id, picks,
        )
    else:
        prediction = create_football_prediction(
            db, current_user.id, prediction_data.match_id,
            prediction_data.team1_goals, prediction_data.team2_goals,
            advance_winner_id, picks,
        )

    fp = prediction.football
    return FootballPredictionResponse(
        id=prediction.id,
        user_id=prediction.user_id,
        match_id=prediction.match_id,
        team1_goals=fp.team1_goals,
        team2_goals=fp.team2_goals,
        advance_winner_id=fp.advance_winner_id,
        player_pick_1_id=fp.player_pick_1_id,
        player_pick_2_id=fp.player_pick_2_id,
        player_pick_3_id=fp.player_pick_3_id,
        points_earned=prediction.points_earned,
        is_processed=prediction.is_processed,
    )


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


def _football_prediction_detail(pred, match) -> FootballPredictionDetailResponse:
    """Build the sport-tagged football detail for a single prediction."""
    fp = pred.football
    fr = match.football_result

    # Per-pick + result score breakdown, available once a result is recorded.
    pick_points: list[int | None] = [None, None, None]
    result_score: int | None = None
    if fr is not None:
        breakdown = football_score_breakdown(pred, match, fr)
        pick_points = list(breakdown["player_scores"])
        result_score = breakdown["result_score"]

    picks = [fp.player_pick_1, fp.player_pick_2, fp.player_pick_3]
    return FootballPredictionDetailResponse(
        id=pred.id,
        match_id=pred.match_id,
        points_earned=pred.points_earned,
        is_processed=pred.is_processed,
        team_1=TeamResponse.model_validate(match.team_1),
        team_2=TeamResponse.model_validate(match.team_2),
        start_time=match.start_time,
        status=match.status.value,
        stage=match.stage,
        team1_goals=fp.team1_goals,
        team2_goals=fp.team2_goals,
        advance_winner=TeamResponse.model_validate(fp.advance_winner) if fp.advance_winner else None,
        player_picks=[
            FootballPlayerPickDetail(player=PlayerResponse.model_validate(p), points=pts)
            for p, pts in zip(picks, pick_points)
        ],
        actual_team1_goals_reg=fr.team1_goals_reg if fr else None,
        actual_team2_goals_reg=fr.team2_goals_reg if fr else None,
        actual_team1_goals_et=fr.team1_goals_et if fr else None,
        actual_team2_goals_et=fr.team2_goals_et if fr else None,
        actual_shootout_winner=TeamResponse.model_validate(fr.shootout_winner) if fr and fr.shootout_winner else None,
        result_score=result_score,
    )


@router.get(
    "/my/detailed",
    response_model=list[PredictionDetailResponse | FootballPredictionDetailResponse],
)
async def get_my_predictions_detailed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all predictions with match context, player names, and actual results.
    Each item is sport-tagged (`sport: "cricket" | "football"`).
    """
    predictions = get_user_predictions(db, current_user.id)
    result = []
    for pred in predictions:
        match = pred.match
        if match.tournament and match.tournament.sport == "football":
            result.append(_football_prediction_detail(pred, match))
            continue
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
