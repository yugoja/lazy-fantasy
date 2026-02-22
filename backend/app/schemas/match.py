from datetime import datetime, timezone
from pydantic import BaseModel, field_serializer


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
    lineup_announced: bool = False

    model_config = {"from_attributes": True}

    @field_serializer("start_time")
    def serialize_start_time(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


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

    @field_serializer("start_time")
    def serialize_start_time(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class MatchPlayersResponse(BaseModel):
    """Schema for match players response."""
    match_id: int
    team_1: TeamResponse
    team_2: TeamResponse
    team_1_players: list[PlayerResponse]
    team_2_players: list[PlayerResponse]
    lineup_announced: bool = False
    start_time: datetime

    @field_serializer("start_time")
    def serialize_start_time(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
