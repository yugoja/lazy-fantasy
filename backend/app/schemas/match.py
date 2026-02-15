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


class MatchDetailResponse(BaseModel):
    """Schema for match detail with results."""
    id: int
    tournament_id: int
    team_1: TeamResponse
    team_2: TeamResponse
    start_time: datetime
    status: str
    winner: TeamResponse | None = None
    most_runs_player: PlayerResponse | None = None
    most_wickets_player: PlayerResponse | None = None
    pom_player: PlayerResponse | None = None


class MatchPlayersResponse(BaseModel):
    """Schema for match players response."""
    match_id: int
    team_1: TeamResponse
    team_2: TeamResponse
    team_1_players: list[PlayerResponse]
    team_2_players: list[PlayerResponse]
