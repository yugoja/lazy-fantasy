from pydantic import BaseModel


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
