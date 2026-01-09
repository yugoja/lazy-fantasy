from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import Match, MatchStatus, Player, Prediction


def get_prediction_by_user_and_match(
    db: Session, user_id: int, match_id: int
) -> Prediction | None:
    """Get a user's prediction for a specific match."""
    return (
        db.query(Prediction)
        .filter(Prediction.user_id == user_id, Prediction.match_id == match_id)
        .first()
    )


def get_user_predictions(db: Session, user_id: int) -> list[Prediction]:
    """Get all predictions for a user."""
    return (
        db.query(Prediction)
        .filter(Prediction.user_id == user_id)
        .order_by(Prediction.id.desc())
        .all()
    )


def can_submit_prediction(db: Session, match_id: int) -> tuple[bool, str]:
    """
    Check if predictions can be submitted for a match.
    Returns (can_submit, reason).
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        return False, "Match not found"
    
    if match.status == MatchStatus.COMPLETED:
        return False, "Match has already been completed"
    
    now = datetime.now(timezone.utc)
    # Handle both timezone-aware and naive datetimes from DB
    match_start = match.start_time
    if match_start.tzinfo is None:
        match_start = match_start.replace(tzinfo=timezone.utc)
    
    if now >= match_start:
        return False, "Match has already started, predictions are closed"
    
    return True, ""


def validate_prediction_players(
    db: Session, match_id: int, player_ids: list[int]
) -> tuple[bool, str]:
    """
    Validate that all predicted players belong to one of the match teams.
    Returns (is_valid, error_message).
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        return False, "Match not found"
    
    valid_team_ids = {match.team_1_id, match.team_2_id}
    
    for player_id in player_ids:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return False, f"Player with ID {player_id} not found"
        if player.team_id not in valid_team_ids:
            return False, f"Player {player.name} is not in either team"
    
    return True, ""


def create_prediction(
    db: Session,
    user_id: int,
    match_id: int,
    predicted_winner_id: int,
    predicted_most_runs_player_id: int,
    predicted_most_wickets_player_id: int,
    predicted_pom_player_id: int,
) -> Prediction:
    """Create a new prediction."""
    prediction = Prediction(
        user_id=user_id,
        match_id=match_id,
        predicted_winner_id=predicted_winner_id,
        predicted_most_runs_player_id=predicted_most_runs_player_id,
        predicted_most_wickets_player_id=predicted_most_wickets_player_id,
        predicted_pom_player_id=predicted_pom_player_id,
        points_earned=0,
        is_processed=False,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def update_prediction(
    db: Session,
    prediction: Prediction,
    predicted_winner_id: int,
    predicted_most_runs_player_id: int,
    predicted_most_wickets_player_id: int,
    predicted_pom_player_id: int,
) -> Prediction:
    """Update an existing prediction."""
    prediction.predicted_winner_id = predicted_winner_id
    prediction.predicted_most_runs_player_id = predicted_most_runs_player_id
    prediction.predicted_most_wickets_player_id = predicted_most_wickets_player_id
    prediction.predicted_pom_player_id = predicted_pom_player_id
    db.commit()
    db.refresh(prediction)
    return prediction
