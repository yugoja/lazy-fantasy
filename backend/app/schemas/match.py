from datetime import datetime
from pydantic import BaseModel


class TeamResponse(BaseModel):
    """Schema for team response."""
    id: int
    name: str
    short_name: str
    logo_url: str | None = None

    model_config = {"from_attributes": True}


class PlayerResponse(BaseModel):
    """Schema for player response."""
    id: int
    name: str
    team_id: int
    role: str

    model_config = {"from_attributes": True}


class MatchResponse(BaseModel):
    """Schema for match response."""
    id: int
    tournament_id: int
    team_1: TeamResponse
    team_2: TeamResponse
    start_time: datetime
    status: str

    model_config = {"from_attributes": True}


class MatchPlayersResponse(BaseModel):
    """Schema for match players response."""
    match_id: int
    team_1: TeamResponse
    team_2: TeamResponse
    team_1_players: list[PlayerResponse]
    team_2_players: list[PlayerResponse]
