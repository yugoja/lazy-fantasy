"""Football (FIFA World Cup 2026) scoring engine.

Implements the partial-credit, position-weighted, binary big-event model from
`docs/.../wc2026-scoring-spec-v2`. This module is intentionally pure: it knows
nothing about the DB or request layer. Inputs are plain dataclasses that mirror
the per-match facts the data layer must expose (spec §10); outputs are ints.

This keeps the scorer idempotent and trivially unit-testable against the spec's
§8 worked examples (see tests/unit/test_scoring_football.py). The DB models,
schemas, and the cross-sport dispatcher are wired up in a later pass; nothing
here imports from app.models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# --- Team identifiers (relative to a match's team_1 / team_2) ---------------
# Pure functions speak in sides, not DB ids. The DB layer maps team ids ⇆ sides.
TEAM1 = 1
TEAM2 = 2
DRAW = 0


class Position(str, Enum):
    """Player's *listed* squad position (spec §4: use the squad role, not the
    position played on the day). Wing-backs are seeded as DEF; GK is its own."""

    GK = "Goalkeeper"
    DEF = "Defender"
    MID = "Midfielder"
    FWD = "Forward"


# --- Stages (spec §5) -------------------------------------------------------
GROUP = "GROUP"
KNOCKOUT_STAGES = frozenset({"R32", "R16", "QF", "SF", "THIRD", "FINAL"})
KNOCKOUT_MULTIPLIER = 2

# --- Result / scoreline points (spec §3) ------------------------------------
RESULT_CORRECT_POINTS = 5
SCORELINE_ONE_TEAM_POINTS = 5
SCORELINE_BOTH_TEAMS_POINTS = 10
MAX_RESULT_SCORE = 15  # result(5) + both scores(10)

# --- Player event points, position-weighted (spec §4) -----------------------
FLOOR_POINTS = 3  # played 30+ mins, all positions
PEN_SAVE_POINTS = 5  # GK only, in-game OR shootout
RED_CARD_POINTS = -3
OWN_GOAL_POINTS = -3
INGAME_PEN_MISS_POINTS = -3
MIN_FLOOR_MINUTES = 30
MIN_CLEAN_SHEET_MINUTES = 60

GOAL_POINTS: dict[Position, int] = {
    Position.FWD: 10,
    Position.MID: 15,
    Position.DEF: 25,
    Position.GK: 25,
}
ASSIST_POINTS: dict[Position, int] = {
    Position.FWD: 5,
    Position.MID: 10,
    Position.DEF: 12,
    Position.GK: 12,
}
CLEAN_SHEET_POINTS: dict[Position, int] = {
    Position.FWD: 0,
    Position.MID: 3,
    Position.DEF: 6,
    Position.GK: 6,
}

# Number of scored line items, surfaced for the Dugout's "N/M agreement" copy.
# Result + scoreline + 3 player picks.
CATEGORY_COUNT = 5


# ---------------------------------------------------------------------------
# Input dataclasses (mirror spec §10 data requirements)
# ---------------------------------------------------------------------------
@dataclass
class ScorelinePrediction:
    """A user's per-match prediction: the scoreline plus, for knockout draws,
    who they think advances."""

    team1_goals: int
    team2_goals: int
    # Required only when the predicted scoreline is a draw in a knockout match
    # (e.g. "France 2-2 win"). Ignored in the group stage.
    advance_winner: int | None = None


@dataclass
class MatchResult:
    """Actual match facts used for result + scoreline scoring (spec §10).

    Goals are stored as regulation and (knockout-only) end-of-extra-time totals.
    Penalty shootouts never feed the scoreline; the shootout only decides who
    advances in a knockout.
    """

    stage: str
    team1_goals_reg: int
    team2_goals_reg: int
    team1_goals_et: int | None = None
    team2_goals_et: int | None = None
    shootout_winner: int | None = None  # TEAM1 / TEAM2 / None

    @property
    def is_knockout(self) -> bool:
        return self.stage in KNOCKOUT_STAGES


@dataclass
class PlayerMatchEvents:
    """Per-player events for one match (spec §10). `team_goals_conceded` is the
    reg+ET total (shootout goals excluded) used for clean-sheet eligibility.

    Shootout outfield misses are deliberately absent — they don't score
    (spec §7). Shootout *saves* by the GK do score and are tracked separately
    from in-game saves only because the data layer must distinguish them; both
    are worth the same +5.
    """

    position: Position
    minutes_played: int
    goals: int = 0
    assists: int = 0
    team_goals_conceded: int = 0  # reg + ET, excludes shootout
    ingame_pen_saves: int = 0  # GK only
    shootout_pen_saves: int = 0  # GK only
    red_card: bool = False
    own_goals: int = 0
    ingame_pen_misses: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _outcome(team1_goals: int, team2_goals: int) -> int:
    """W/D/W from a scoreline."""
    if team1_goals > team2_goals:
        return TEAM1
    if team2_goals > team1_goals:
        return TEAM2
    return DRAW


def _scoring_scoreline(result: MatchResult) -> tuple[int, int]:
    """The scoreline used for scoring: end-of-ET if ET was played, else the
    90-minute (regulation) score. Pens never count (spec §3)."""
    if result.team1_goals_et is not None and result.team2_goals_et is not None:
        return result.team1_goals_et, result.team2_goals_et
    return result.team1_goals_reg, result.team2_goals_reg


def _advancing_team(result: MatchResult) -> int:
    """Who advances in a knockout: decided by the ET/reg score if decisive,
    otherwise by the shootout winner."""
    t1, t2 = _scoring_scoreline(result)
    outcome = _outcome(t1, t2)
    if outcome != DRAW:
        return outcome
    return result.shootout_winner


def _predicted_advancing(pred: ScorelinePrediction) -> int | None:
    """Who the user thinks advances in a knockout: implied by a decisive
    predicted scoreline, else their explicit `advance_winner` pick."""
    outcome = _outcome(pred.team1_goals, pred.team2_goals)
    if outcome != DRAW:
        return outcome
    return pred.advance_winner


# ---------------------------------------------------------------------------
# Pure scoring functions
# ---------------------------------------------------------------------------
def compute_result_score(pred: ScorelinePrediction, result: MatchResult) -> int:
    """Result + scoreline component, max 15 (spec §3).

    Result and scoreline are decoupled, independent line items.
    """
    if result.is_knockout:
        result_correct = _predicted_advancing(pred) == _advancing_team(result)
    else:
        result_correct = _outcome(pred.team1_goals, pred.team2_goals) == _outcome(
            result.team1_goals_reg, result.team2_goals_reg
        )

    actual_t1, actual_t2 = _scoring_scoreline(result)
    t1_match = pred.team1_goals == actual_t1
    t2_match = pred.team2_goals == actual_t2
    if t1_match and t2_match:
        scoreline_pts = SCORELINE_BOTH_TEAMS_POINTS
    elif t1_match or t2_match:
        scoreline_pts = SCORELINE_ONE_TEAM_POINTS
    else:
        scoreline_pts = 0

    return (RESULT_CORRECT_POINTS if result_correct else 0) + scoreline_pts


def compute_player_score(ev: PlayerMatchEvents) -> int:
    """Sum of all event points for one player in one match (spec §4).

    No minute-based scaling on event values: a 75'-minute sub who scores still
    earns the full goal points. The only minute thresholds are the 30' floor
    and the 60' clean-sheet gate.
    """
    pos = ev.position
    score = 0

    if ev.minutes_played >= MIN_FLOOR_MINUTES:
        score += FLOOR_POINTS

    score += ev.goals * GOAL_POINTS[pos]
    score += ev.assists * ASSIST_POINTS[pos]

    if ev.minutes_played >= MIN_CLEAN_SHEET_MINUTES and ev.team_goals_conceded == 0:
        score += CLEAN_SHEET_POINTS[pos]

    if pos == Position.GK:
        score += (ev.ingame_pen_saves + ev.shootout_pen_saves) * PEN_SAVE_POINTS

    if ev.red_card:
        score += RED_CARD_POINTS
    score += ev.own_goals * OWN_GOAL_POINTS
    score += ev.ingame_pen_misses * INGAME_PEN_MISS_POINTS

    return score


def compute_match_score(
    pred: ScorelinePrediction,
    player_picks: list[PlayerMatchEvents],
    result: MatchResult,
) -> int:
    """Full per-match score for a user (spec §6): result + 3 player scores,
    doubled for knockout matches."""
    total = compute_result_score(pred, result) + sum(
        compute_player_score(p) for p in player_picks
    )
    if result.is_knockout:
        total *= KNOCKOUT_MULTIPLIER
    return total
