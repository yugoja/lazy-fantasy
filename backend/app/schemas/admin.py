from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MatchCreate(BaseModel):
    """Schema for creating a match."""
    tournament_id: int
    team_1_id: int
    team_2_id: int
    start_time: datetime
    stage: Optional[str] = None


class MatchResultCreate(BaseModel):
    """Schema for setting match results."""
    result_winner_id: int
    result_most_runs_team1_player_id: int
    result_most_runs_team2_player_id: int
    result_most_wickets_team1_player_id: int
    result_most_wickets_team2_player_id: int
    result_pom_player_id: int


class FootballPlayerEventInput(BaseModel):
    """Per-player events for a football match result (WC2026 spec §10).

    `team_goals_conceded` is intentionally absent — the server derives it from
    the final scoreline and the player's team, so it can't desync.
    """
    player_id: int
    minutes_played: int = Field(default=0, ge=0, le=120)
    goals: int = Field(default=0, ge=0)
    assists: int = Field(default=0, ge=0)
    ingame_pen_saves: int = Field(default=0, ge=0)
    shootout_pen_saves: int = Field(default=0, ge=0)
    red_card: bool = False
    own_goals: int = Field(default=0, ge=0)
    ingame_pen_misses: int = Field(default=0, ge=0)


class FootballMatchResultCreate(BaseModel):
    """Schema for setting a football match result + per-player events."""
    team1_goals_reg: int = Field(ge=0, le=30)
    team2_goals_reg: int = Field(ge=0, le=30)
    team1_goals_et: Optional[int] = Field(default=None, ge=0, le=30)
    team2_goals_et: Optional[int] = Field(default=None, ge=0, le=30)
    shootout_winner_id: Optional[int] = None
    player_events: list[FootballPlayerEventInput] = Field(default_factory=list)


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


class LinkFootballRequest(BaseModel):
    fixture_id: int


class FootballSyncResponse(BaseModel):
    match_id: int
    status: str
    predictions_processed: int
    unresolved_players: list[str]
    sync_error: str | None
    sync_state: str
    last_synced_at: datetime | None


class SeedPlayerFormRequest(BaseModel):
    wc_league_id: int
    season: int = 2026


class SeedSummaryResponse(BaseModel):
    teams_matched: int
    teams_unmatched: int
    players_matched: int
    players_unmatched: int
    forms_created: int
