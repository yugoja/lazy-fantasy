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
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}


class LeagueUpdate(BaseModel):
    """Schema for owner-only league updates."""
    name: Optional[str] = None


class LeagueJoin(BaseModel):
    """Schema for joining a league."""
    invite_code: str


class LeaderboardEntry(BaseModel):
    """Schema for a leaderboard entry."""
    user_id: int
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_owner: bool = False
    total_points: int
    rank: int
    rank_delta: Optional[int] = None


class LeaderboardResponse(BaseModel):
    """Schema for leaderboard response."""
    league_id: int
    league_name: str
    entries: list[LeaderboardEntry]
    available_rounds: list[str] = []
