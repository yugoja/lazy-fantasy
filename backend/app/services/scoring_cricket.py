"""Cricket (IPL) scoring: the original all-or-nothing, 6-category model.

Moved verbatim out of the old `scoring.py` (which is now a sport dispatcher).
Cricket picks/results remain inline on the `Prediction` / `Match` rows, so this
module reads `prediction.predicted_*` and `match.result_*` directly.
"""

from app.models import Match, Prediction

# Points configuration
POINTS_WINNER = 10
POINTS_MOST_RUNS_TEAM1 = 20
POINTS_MOST_RUNS_TEAM2 = 20
POINTS_MOST_WICKETS_TEAM1 = 20
POINTS_MOST_WICKETS_TEAM2 = 20
POINTS_POM = 50
# Max group-stage total: 10 + 20 + 20 + 20 + 20 + 50 = 140
GROUP_MAX_SCORE = 140

# Knockout (IPL playoffs) double every prediction, mirroring the football
# stage-driven multiplier. The stage codes below are set on the playoff fixtures
# by scripts/seed_ipl2026_knockouts.py; group-stage matches leave stage NULL.
KNOCKOUT_STAGES = frozenset({"Q1", "ELIM", "Q2", "FINAL"})
KNOCKOUT_MULTIPLIER = 2


def compute_hits(prediction: Prediction, match: Match) -> dict[str, bool]:
    """Per-category hit map comparing a prediction against a completed match's result."""
    return {
        "winner": prediction.predicted_winner_id == match.result_winner_id,
        "runs_t1": prediction.predicted_most_runs_team1_player_id == match.result_most_runs_team1_player_id,
        "runs_t2": prediction.predicted_most_runs_team2_player_id == match.result_most_runs_team2_player_id,
        "wkts_t1": prediction.predicted_most_wickets_team1_player_id == match.result_most_wickets_team1_player_id,
        "wkts_t2": prediction.predicted_most_wickets_team2_player_id == match.result_most_wickets_team2_player_id,
        "pom": prediction.predicted_pom_player_id == match.result_pom_player_id,
    }


_CATEGORY_POINTS = {
    "winner": POINTS_WINNER,
    "runs_t1": POINTS_MOST_RUNS_TEAM1,
    "runs_t2": POINTS_MOST_RUNS_TEAM2,
    "wkts_t1": POINTS_MOST_WICKETS_TEAM1,
    "wkts_t2": POINTS_MOST_WICKETS_TEAM2,
    "pom": POINTS_POM,
}

# Number of scored categories, surfaced for the Dugout's "N/M agreement" copy.
CATEGORY_COUNT = len(_CATEGORY_POINTS)


def points_for_hits(hits: dict[str, bool]) -> int:
    return sum(pts for cat, pts in _CATEGORY_POINTS.items() if hits.get(cat))


def is_knockout(match: Match) -> bool:
    """Whether a match is an IPL knockout (playoff), which doubles all points."""
    return (match.stage or "") in KNOCKOUT_STAGES


def stage_multiplier(match: Match) -> int:
    """Points multiplier for a match: 2 for knockouts, 1 otherwise."""
    return KNOCKOUT_MULTIPLIER if is_knockout(match) else 1


def max_score(match: Match) -> int:
    """The maximum points a single prediction can earn for this match."""
    return GROUP_MAX_SCORE * stage_multiplier(match)


def score_prediction(prediction: Prediction, match: Match) -> int:
    """Points a single cricket prediction earns against a completed match.

    Knockout (playoff) matches double the total (spec parity with football)."""
    return points_for_hits(compute_hits(prediction, match)) * stage_multiplier(match)
