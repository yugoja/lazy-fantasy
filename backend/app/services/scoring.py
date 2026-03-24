from sqlalchemy.orm import Session

from app.models import Match, MatchStatus, Prediction

# Points configuration
POINTS_WINNER = 10
POINTS_MOST_RUNS_TEAM1 = 20
POINTS_MOST_RUNS_TEAM2 = 20
POINTS_MOST_WICKETS_TEAM1 = 20
POINTS_MOST_WICKETS_TEAM2 = 20
POINTS_POM = 50
# Max total: 10 + 20 + 20 + 20 + 20 + 50 = 140


def calculate_scores(db: Session, match_id: int) -> int:
    """
    Calculate and update scores for all predictions for a given match.

    Returns the number of predictions processed.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or match.status != MatchStatus.COMPLETED:
        return 0

    # Get all unprocessed predictions for this match
    predictions = (
        db.query(Prediction)
        .filter(
            Prediction.match_id == match_id,
            Prediction.is_processed == False,
        )
        .all()
    )

    processed_count = 0

    for prediction in predictions:
        points = 0

        # Winner prediction
        if prediction.predicted_winner_id == match.result_winner_id:
            points += POINTS_WINNER

        # Most runs — team 1
        if prediction.predicted_most_runs_team1_player_id == match.result_most_runs_team1_player_id:
            points += POINTS_MOST_RUNS_TEAM1

        # Most runs — team 2
        if prediction.predicted_most_runs_team2_player_id == match.result_most_runs_team2_player_id:
            points += POINTS_MOST_RUNS_TEAM2

        # Most wickets — team 1
        if prediction.predicted_most_wickets_team1_player_id == match.result_most_wickets_team1_player_id:
            points += POINTS_MOST_WICKETS_TEAM1

        # Most wickets — team 2
        if prediction.predicted_most_wickets_team2_player_id == match.result_most_wickets_team2_player_id:
            points += POINTS_MOST_WICKETS_TEAM2

        # Player of the match prediction
        if prediction.predicted_pom_player_id == match.result_pom_player_id:
            points += POINTS_POM

        # Update prediction
        prediction.points_earned = points
        prediction.is_processed = True
        processed_count += 1

    db.commit()
    return processed_count
