from datetime import datetime
from pydantic import BaseModel


class MatchCreate(BaseModel):
    """Schema for creating a match."""
    tournament_id: int
    team_1_id: int
    team_2_id: int
    start_time: datetime


class MatchResultCreate(BaseModel):
    """Schema for setting match results."""
    result_winner_id: int
    result_most_runs_team1_player_id: int
    result_most_runs_team2_player_id: int
    result_most_wickets_team1_player_id: int
    result_most_wickets_team2_player_id: int
    result_pom_player_id: int


class SetLineupRequest(BaseModel):
    """Schema for setting match playing XI."""
    player_ids: list[int]
