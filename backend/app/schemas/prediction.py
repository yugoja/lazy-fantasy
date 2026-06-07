from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_serializer

from app.schemas.match import TeamResponse, PlayerResponse


class PredictionCreate(BaseModel):
    """Schema for creating a cricket prediction."""
    match_id: int
    predicted_winner_id: int
    predicted_most_runs_team1_player_id: int
    predicted_most_runs_team2_player_id: int
    predicted_most_wickets_team1_player_id: int
    predicted_most_wickets_team2_player_id: int
    predicted_pom_player_id: int


class FootballPredictionCreate(BaseModel):
    """Schema for creating a football prediction (WC2026 spec §1).

    The result (W/D/W) is derived from the predicted scoreline. `advance_winner_id`
    is only needed for knockout matches where the predicted scoreline is a draw
    (e.g. "France 2-2 win") — the router enforces that.
    """
    match_id: int
    team1_goals: int = Field(ge=0, le=30)
    team2_goals: int = Field(ge=0, le=30)
    advance_winner_id: Optional[int] = None
    player_pick_1_id: int
    player_pick_2_id: int
    player_pick_3_id: int


class FootballAutoPickRequest(BaseModel):
    match_id: int
    strategy: Literal["safe", "balanced", "bold"]


class PredictionResponse(BaseModel):
    """Schema for prediction response (cricket fields are null for football)."""
    id: int
    user_id: int
    match_id: int
    predicted_winner_id: Optional[int] = None
    predicted_most_runs_team1_player_id: Optional[int] = None
    predicted_most_runs_team2_player_id: Optional[int] = None
    predicted_most_wickets_team1_player_id: Optional[int] = None
    predicted_most_wickets_team2_player_id: Optional[int] = None
    predicted_pom_player_id: Optional[int] = None
    points_earned: int
    is_processed: bool

    model_config = {"from_attributes": True}


class FootballPredictionResponse(BaseModel):
    """Schema for a football prediction response."""
    id: int
    user_id: int
    match_id: int
    team1_goals: int
    team2_goals: int
    advance_winner_id: Optional[int] = None
    player_pick_1_id: int
    player_pick_2_id: int
    player_pick_3_id: int
    points_earned: int
    is_processed: bool


class PredictionDetailResponse(BaseModel):
    """Enriched cricket prediction with match context and player names."""
    sport: Literal["cricket"] = "cricket"
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
    predicted_most_runs_team1_player: PlayerResponse
    predicted_most_runs_team2_player: PlayerResponse
    predicted_most_wickets_team1_player: PlayerResponse
    predicted_most_wickets_team2_player: PlayerResponse
    predicted_pom_player: PlayerResponse
    # Actual results (None if match not completed)
    actual_winner: TeamResponse | None = None
    actual_most_runs_team1_player: PlayerResponse | None = None
    actual_most_runs_team2_player: PlayerResponse | None = None
    actual_most_wickets_team1_player: PlayerResponse | None = None
    actual_most_wickets_team2_player: PlayerResponse | None = None
    actual_pom_player: PlayerResponse | None = None

    @field_serializer("start_time")
    def serialize_start_time(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class FootballPlayerPickDetail(BaseModel):
    """One of a user's three player picks, with its individual score once the
    match has been scored."""
    player: PlayerResponse
    points: int | None = None  # None until the match is processed


class FootballPredictionDetailResponse(BaseModel):
    """Enriched football prediction with match context, picks, and actuals."""
    sport: Literal["football"] = "football"
    id: int
    match_id: int
    points_earned: int
    is_processed: bool
    # Match context
    team_1: TeamResponse
    team_2: TeamResponse
    start_time: datetime
    status: str
    stage: Optional[str] = None
    # What the user predicted
    team1_goals: int
    team2_goals: int
    advance_winner: TeamResponse | None = None
    player_picks: list[FootballPlayerPickDetail]
    # Actual result (None until completed)
    actual_team1_goals_reg: int | None = None
    actual_team2_goals_reg: int | None = None
    actual_team1_goals_et: int | None = None
    actual_team2_goals_et: int | None = None
    actual_shootout_winner: TeamResponse | None = None
    # Score breakdown (None until processed); result_score is pre-multiplier
    result_score: int | None = None

    @field_serializer("start_time")
    def serialize_start_time(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class FriendPrediction(BaseModel):
    """A league member's prediction for a match, shown in the league activity feed."""
    username: str
    display_name: Optional[str] = None
    is_me: bool
    points_earned: int
    is_processed: bool
    predicted_winner: TeamResponse
    predicted_most_runs_team1_player: PlayerResponse
    predicted_most_runs_team2_player: PlayerResponse
    predicted_most_wickets_team1_player: PlayerResponse
    predicted_most_wickets_team2_player: PlayerResponse
    predicted_pom_player: PlayerResponse
    actual_winner: TeamResponse | None = None
    actual_most_runs_team1_player: PlayerResponse | None = None
    actual_most_runs_team2_player: PlayerResponse | None = None
    actual_most_wickets_team1_player: PlayerResponse | None = None
    actual_most_wickets_team2_player: PlayerResponse | None = None
    actual_pom_player: PlayerResponse | None = None
