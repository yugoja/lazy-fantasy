from enum import Enum
from pydantic import BaseModel, field_validator


class DugoutEventType(str, Enum):
    CONTRARIAN = "contrarian"
    AGREEMENT = "agreement"
    STREAK = "streak"
    RANK_SHIFT = "rank_shift"


class DugoutEvent(BaseModel):
    type: DugoutEventType
    league_name: str
    league_id: int
    match_id: int | None = None
    username: str
    display_name: str | None = None
    is_me: bool = False
    # Type-specific fields
    streak_count: int | None = None
    rank: int | None = None
    rank_delta: int | None = None
    agreement_count: int | None = None
    team_short_name: str | None = None


class DugoutDismissRequest(BaseModel):
    type: DugoutEventType
    league_id: int
    match_id: int | None = None
    subject_username: str
