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
    TOURNAMENT_VERDICT = "tournament_verdict"
    ANNOUNCEMENT = "announcement"


class TournamentVerdictLine(BaseModel):
    """One row of a Mega Picks recap: what the user picked vs the actual result."""
    category: str            # "semi" | "boot" | "ball" | "glove"
    label: str               # display label, e.g. "Golden Boot"
    pick: str | None = None      # user's pick (team short name or player name)
    actual: str | None = None    # actual winner (players only; semis are a set)
    correct: bool = False
    points: int = 0


class VerdictHits(BaseModel):
    # Cricket categories (default False so the football path can omit them)
    winner: bool = False
    runs_t1: bool = False
    runs_t2: bool = False
    wkts_t1: bool = False
    wkts_t2: bool = False
    pom: bool = False
    # Football categories
    outcome: bool = False       # predicted the correct W/D/L result
    exact_score: bool = False   # predicted the exact final scoreline
    pick_1: bool = False        # each player pick that scored points
    pick_2: bool = False
    pick_3: bool = False


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
    agreement_total: int | None = None
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
    # Match verdict — football extras (sport defaults to cricket for back-compat)
    sport: str = "cricket"
    team1_short: str | None = None
    team2_short: str | None = None
    team1_goals: int | None = None
    team2_goals: int | None = None
    is_draw: bool | None = None
    # Tournament-picks CTA fields
    tournament_id: int | None = None
    tournament_name: str | None = None
    picks_lock_at: datetime | None = None
    has_picks: bool | None = None
    # Tournament-verdict (Mega Picks recap) fields
    tv_points: int | None = None          # total tournament-pick points earned
    tv_semis_correct: int | None = None   # correct semi-finalists (0-4)
    tv_semis_total: int | None = None     # how many semis the user picked (usually 4)
    tv_lines: list[TournamentVerdictLine] | None = None
    # One-off announcement fields (system message, not tied to a member/match)
    announcement_title: str | None = None
    announcement_body: str | None = None
    announcement_link: str | None = None       # optional CTA href
    announcement_expires_at: datetime | None = None  # drives countdown timer


class DugoutDismissRequest(BaseModel):
    type: DugoutEventType
    league_id: int
    match_id: int | None = None
    subject_username: str
