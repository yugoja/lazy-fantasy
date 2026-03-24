"""Unit tests for scoring logic."""
import pytest
from app.services.scoring import calculate_scores


@pytest.mark.unit
class TestScoringLogic:
    """Test the scoring calculation logic."""

    def test_perfect_prediction_score(
        self, db_session, test_user, completed_match, test_teams
    ):
        """Test scoring when all predictions are correct."""
        from app.models.prediction import Prediction
        from app.models.player import Player

        team1, team2 = test_teams
        team1_players = db_session.query(Player).filter(
            Player.team_id == team1.id
        ).all()
        team2_players = db_session.query(Player).filter(
            Player.team_id == team2.id
        ).all()

        # Create prediction matching the result exactly
        prediction = Prediction(
            user_id=test_user.id,
            match_id=completed_match.id,
            predicted_winner_id=completed_match.result_winner_id,
            predicted_most_runs_team1_player_id=completed_match.result_most_runs_team1_player_id,
            predicted_most_runs_team2_player_id=completed_match.result_most_runs_team2_player_id,
            predicted_most_wickets_team1_player_id=completed_match.result_most_wickets_team1_player_id,
            predicted_most_wickets_team2_player_id=completed_match.result_most_wickets_team2_player_id,
            predicted_pom_player_id=completed_match.result_pom_player_id
        )
        db_session.add(prediction)
        db_session.commit()

        # Calculate scores
        calculate_scores(db_session, completed_match.id)
        db_session.refresh(prediction)

        # Should get: 10 + 20 + 20 + 20 + 20 + 50 = 140 points
        assert prediction.points_earned == 140
        assert prediction.is_processed is True

    def test_no_correct_predictions_score(
        self, db_session, test_user, completed_match, test_teams
    ):
        """Test scoring when no predictions are correct."""
        from app.models.prediction import Prediction
        from app.models.player import Player

        team1, team2 = test_teams
        team1_players = db_session.query(Player).filter(
            Player.team_id == team1.id
        ).all()
        team2_players = db_session.query(Player).filter(
            Player.team_id == team2.id
        ).all()

        # Create prediction that's all wrong (but valid per-team)
        prediction = Prediction(
            user_id=test_user.id,
            match_id=completed_match.id,
            predicted_winner_id=team2.id,  # Wrong
            predicted_most_runs_team1_player_id=team1_players[1].id,  # Wrong
            predicted_most_runs_team2_player_id=team2_players[1].id,  # Wrong
            predicted_most_wickets_team1_player_id=team1_players[5].id,  # Wrong
            predicted_most_wickets_team2_player_id=team2_players[5].id,  # Wrong
            predicted_pom_player_id=team2_players[0].id  # Wrong
        )
        db_session.add(prediction)
        db_session.commit()

        # Calculate scores
        calculate_scores(db_session, completed_match.id)
        db_session.refresh(prediction)

        assert prediction.points_earned == 0
        assert prediction.is_processed is True

    def test_partial_correct_predictions(
        self, db_session, test_user, completed_match, test_teams
    ):
        """Test scoring with some correct and some wrong predictions."""
        from app.models.prediction import Prediction
        from app.models.player import Player

        team1, team2 = test_teams
        team1_players = db_session.query(Player).filter(
            Player.team_id == team1.id
        ).all()
        team2_players = db_session.query(Player).filter(
            Player.team_id == team2.id
        ).all()

        # Predict winner and most runs (team1) correctly, others wrong
        prediction = Prediction(
            user_id=test_user.id,
            match_id=completed_match.id,
            predicted_winner_id=completed_match.result_winner_id,  # Correct: +10
            predicted_most_runs_team1_player_id=completed_match.result_most_runs_team1_player_id,  # Correct: +20
            predicted_most_runs_team2_player_id=team2_players[1].id,  # Wrong: +0
            predicted_most_wickets_team1_player_id=team1_players[5].id,  # Wrong: +0
            predicted_most_wickets_team2_player_id=team2_players[5].id,  # Wrong: +0
            predicted_pom_player_id=team2_players[0].id  # Wrong: +0
        )
        db_session.add(prediction)
        db_session.commit()

        calculate_scores(db_session, completed_match.id)
        db_session.refresh(prediction)

        assert prediction.points_earned == 30  # 10 + 20
        assert prediction.is_processed is True
