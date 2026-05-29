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
# Max total: 10 + 20 + 20 + 20 + 20 + 50 = 140


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


def score_prediction(prediction: Prediction, match: Match) -> int:
    """Points a single cricket prediction earns against a completed match."""
    return points_for_hits(compute_hits(prediction, match))
