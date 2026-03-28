from typing import Optional
from pydantic import BaseModel


class TournamentPicksSubmit(BaseModel):
    top4_team_ids: list[int]  # up to 4 team IDs
    best_batsman_player_id: Optional[int] = None
    best_bowler_player_id: Optional[int] = None


class TeamPickOption(BaseModel):
    id: int
    name: str
    short_name: str
    logo_url: Optional[str] = None

    model_config = {"from_attributes": True}


class PlayerPickOption(BaseModel):
    id: int
    name: str
    role: str
    team_id: int
    team_name: Optional[str] = None

    model_config = {"from_attributes": True}


class TournamentPicksResponse(BaseModel):
    tournament_id: int
    tournament_name: str
    picks_window: str
    top4_team_ids: list[Optional[int]]
    best_batsman_player_id: Optional[int]
    best_bowler_player_id: Optional[int]
    points_earned: int
    is_window2: bool
    is_processed: bool


class SetPicksWindowRequest(BaseModel):
    window: str  # 'open' | 'locked' | 'open2' | 'finalized' | 'closed'


class SetPicksResultRequest(BaseModel):
    result_top4_team_ids: list[int]  # exactly 4
    result_best_batsman_player_id: int
    result_best_bowler_player_id: int
