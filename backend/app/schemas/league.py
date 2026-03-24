from typing import Optional
from pydantic import BaseModel


class LeagueCreate(BaseModel):
    """Schema for creating a new league."""
    name: str
    sport: str = "cricket"


class LeagueResponse(BaseModel):
    """Schema for league response."""
    id: int
    name: str
    invite_code: str
    owner_id: int
    sport: str = "cricket"

    model_config = {"from_attributes": True}


class LeagueJoin(BaseModel):
    """Schema for joining a league."""
    invite_code: str


class LeaderboardEntry(BaseModel):
    """Schema for a leaderboard entry."""
    user_id: int
    username: str
    total_points: int
    rank: int
    rank_delta: Optional[int] = None


class LeaderboardResponse(BaseModel):
    """Schema for leaderboard response."""
    league_id: int
    league_name: str
    entries: list[LeaderboardEntry]
