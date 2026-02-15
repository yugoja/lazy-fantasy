from datetime import datetime
from pydantic import BaseModel

from app.schemas.match import TeamResponse, PlayerResponse


class PredictionCreate(BaseModel):
    """Schema for creating a prediction."""
    match_id: int
    predicted_winner_id: int
    predicted_most_runs_player_id: int
    predicted_most_wickets_player_id: int
    predicted_pom_player_id: int


class PredictionResponse(BaseModel):
    """Schema for prediction response."""
    id: int
    user_id: int
    match_id: int
    predicted_winner_id: int
    predicted_most_runs_player_id: int
    predicted_most_wickets_player_id: int
    predicted_pom_player_id: int
    points_earned: int
    is_processed: bool

    model_config = {"from_attributes": True}


class PredictionDetailResponse(BaseModel):
    """Enriched prediction with match context and player names."""
    id: int
    match_id: int
    points_earned: int
    is_processed: bool
    # Match context
    team_1: TeamResponse
    team_2: TeamResponse
    start_time: datetime
    status: str
    # What the user predicted (resolved to names)
    predicted_winner: TeamResponse
    predicted_most_runs_player: PlayerResponse
    predicted_most_wickets_player: PlayerResponse
    predicted_pom_player: PlayerResponse
    # Actual results (None if match not completed)
    actual_winner: TeamResponse | None = None
    actual_most_runs_player: PlayerResponse | None = None
    actual_most_wickets_player: PlayerResponse | None = None
    actual_pom_player: PlayerResponse | None = None
