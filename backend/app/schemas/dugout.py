from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class DugoutEventType(str, Enum):
    CONTRARIAN = "contrarian"
    AGREEMENT = "agreement"
    STREAK = "streak"
    RANK_SHIFT = "rank_shift"
    MATCH_VERDICT = "match_verdict"
    TOURNAMENT_PICKS = "tournament_picks"


class VerdictHits(BaseModel):
    winner: bool
    runs_t1: bool
    runs_t2: bool
    wkts_t1: bool
    wkts_t2: bool
    pom: bool


class VerdictWinner(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    points_earned: int
    hits: VerdictHits
    prev_rank: int | None = None
    new_rank: int


class VerdictRunner(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    points_earned: int
    prev_rank: int | None = None
    new_rank: int


class DugoutEvent(BaseModel):
    type: DugoutEventType
    league_name: str
    league_id: int
    match_id: int | None = None
    username: str
    display_name: str | None = None
    is_me: bool = False
    # Type-specific fields used by existing event types
    streak_count: int | None = None
    rank: int | None = None
    rank_delta: int | None = None
    agreement_count: int | None = None
    team_short_name: str | None = None
    # Match verdict fields
    winners: list[VerdictWinner] | None = None
    runners_up: list[VerdictRunner] | None = None
    pom_player_name: str | None = None
    winning_team_short: str | None = None
    losing_team_short: str | None = None
    match_label: str | None = None
    top_score: int | None = None
    runner_up_score: int | None = None
    # Tournament-picks CTA fields
    tournament_id: int | None = None
    tournament_name: str | None = None
    picks_lock_at: datetime | None = None
    has_picks: bool | None = None


class DugoutDismissRequest(BaseModel):
    type: DugoutEventType
    league_id: int
    match_id: int | None = None
    subject_username: str
