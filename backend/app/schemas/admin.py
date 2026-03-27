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


class LinkMatchRequest(BaseModel):
    """Link a match to a CricAPI external_match_id."""
    external_match_id: str


class PlayerMappingItem(BaseModel):
    provider_id: str
    player_id: int


class BulkPlayerMappingRequest(BaseModel):
    """Save cricapi_player_id on one or more Player records."""
    mappings: list[PlayerMappingItem]


class SyncStatusResponse(BaseModel):
    match_id: int
    external_match_id: str | None
    sync_state: str
    last_synced_at: datetime | None
    sync_error: str | None
    cricapi_preview: dict | None = None
