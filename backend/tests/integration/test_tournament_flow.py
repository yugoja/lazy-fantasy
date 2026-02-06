"""
Integration tests for the complete tournament flow.

This test suite simulates a full tournament lifecycle:
1. Users sign up and log in
2. Create and join leagues
3. View upcoming matches
4. Make predictions before matches start
5. Admin sets match results
6. Points are calculated and leaderboards updated
"""
import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.integration
class TestCompleteTournamentFlow:
    """Test the complete tournament flow from start to finish."""

    def test_complete_tournament_workflow(
        self, client, db_session, test_tournament, test_teams
    ):
        """
        End-to-end test of a complete tournament workflow.

        Flow:
        1. Two users sign up
        2. User 1 creates a league
        3. User 2 joins the league
        4. Match is created
        5. Both users make predictions
        6. Match result is set
        7. Scores are calculated
        8. Leaderboard shows correct rankings
        """
        # Step 1: User Registration
        user1_data = {
            "username": "player1",
            "email": "player1@test.com",
            "password": "secure123"
        }
        user2_data = {
            "username": "player2",
            "email": "player2@test.com",
            "password": "secure123"
        }

        response = client.post("/auth/signup", json=user1_data)
        assert response.status_code == 201
        user1_id = response.json()["id"]

        response = client.post("/auth/signup", json=user2_data)
        assert response.status_code == 201
        user2_id = response.json()["id"]

        # Step 2: User Login
        response = client.post(
            "/auth/login",
            data={"username": "player1", "password": "secure123"}
        )
        assert response.status_code == 200
        user1_token = response.json()["access_token"]

        response = client.post(
            "/auth/login",
            data={"username": "player2", "password": "secure123"}
        )
        assert response.status_code == 200
        user2_token = response.json()["access_token"]

        # Step 3: User 1 creates a league
        response = client.post(
            "/leagues/",
            json={"name": "Champions League"},
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 201
        league = response.json()
        league_id = league["id"]
        invite_code = league["invite_code"]
        assert len(invite_code) == 6

        # Step 4: User 2 joins the league
        response = client.post(
            "/leagues/join",
            json={"invite_code": invite_code},
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert response.status_code == 200

        # Step 5: Create a match (admin action)
        team1, team2 = test_teams
        match_data = {
            "tournament_id": test_tournament.id,
            "team_1_id": team1.id,
            "team_2_id": team2.id,
            "start_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        }
        response = client.post(
            "/admin/matches/",
            json=match_data,
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 201
        match = response.json()
        match_id = match["id"]

        # Step 6: Get match players for predictions
        response = client.get(f"/matches/{match_id}/players")
        assert response.status_code == 200
        match_players = response.json()
        team1_players = match_players["team_1_players"]
        team2_players = match_players["team_2_players"]

        # Step 7: User 1 makes predictions
        user1_prediction = {
            "match_id": match_id,
            "predicted_winner_id": team1.id,
            "predicted_most_runs_player_id": team1_players[0]["id"],
            "predicted_most_wickets_player_id": team2_players[4]["id"],
            "predicted_pom_player_id": team1_players[0]["id"]
        }
        response = client.post(
            "/predictions/",
            json=user1_prediction,
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 201

        # Step 8: User 2 makes different predictions
        user2_prediction = {
            "match_id": match_id,
            "predicted_winner_id": team2.id,
            "predicted_most_runs_player_id": team2_players[0]["id"],
            "predicted_most_wickets_player_id": team1_players[4]["id"],
            "predicted_pom_player_id": team2_players[0]["id"]
        }
        response = client.post(
            "/predictions/",
            json=user2_prediction,
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert response.status_code == 201

        # Step 9: Admin sets match result (Team 1 wins)
        match_result = {
            "result_winner_id": team1.id,
            "result_most_runs_player_id": team1_players[0]["id"],
            "result_most_wickets_player_id": team2_players[4]["id"],
            "result_pom_player_id": team1_players[0]["id"]
        }
        response = client.post(
            f"/admin/matches/{match_id}/result",
            json=match_result,
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        result_data = response.json()
        assert result_data["status"] == "COMPLETED"
        assert result_data["predictions_processed"] == 2

        # Step 10: Check leaderboard
        response = client.get(
            f"/leagues/{league_id}/leaderboard",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        leaderboard = response.json()

        # User 1 predicted all correctly: 10 + 20 + 20 + 50 = 100 points
        # User 2 predicted none correctly: 0 points
        entries = sorted(leaderboard["entries"], key=lambda x: x["rank"])

        assert len(entries) == 2
        assert entries[0]["username"] == "player1"
        assert entries[0]["total_points"] == 100
        assert entries[0]["rank"] == 1

        assert entries[1]["username"] == "player2"
        assert entries[1]["total_points"] == 0
        assert entries[1]["rank"] == 2

    def test_partial_correct_predictions(
        self, client, db_session, test_tournament, test_teams
    ):
        """Test scoring when predictions are partially correct."""
        # Setup users
        user1_data = {"username": "user1", "email": "user1@test.com", "password": "pass"}
        client.post("/auth/signup", json=user1_data)

        response = client.post("/auth/login", data={"username": "user1", "password": "pass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create league
        response = client.post("/leagues/", json={"name": "Test"}, headers=headers)
        league_id = response.json()["id"]

        # Create match
        team1, team2 = test_teams
        match_data = {
            "tournament_id": test_tournament.id,
            "team_1_id": team1.id,
            "team_2_id": team2.id,
            "start_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        response = client.post("/admin/matches/", json=match_data, headers=headers)
        match_id = response.json()["id"]

        # Get players
        response = client.get(f"/matches/{match_id}/players")
        match_players = response.json()
        team1_players = match_players["team_1_players"]
        team2_players = match_players["team_2_players"]

        # Make prediction - predict winner and most runs correctly only
        prediction = {
            "match_id": match_id,
            "predicted_winner_id": team1.id,  # Correct
            "predicted_most_runs_player_id": team1_players[0]["id"],  # Correct
            "predicted_most_wickets_player_id": team1_players[4]["id"],  # Wrong
            "predicted_pom_player_id": team2_players[0]["id"]  # Wrong
        }
        client.post("/predictions/", json=prediction, headers=headers)

        # Set result
        match_result = {
            "result_winner_id": team1.id,
            "result_most_runs_player_id": team1_players[0]["id"],
            "result_most_wickets_player_id": team2_players[4]["id"],
            "result_pom_player_id": team1_players[0]["id"]
        }
        client.post(f"/admin/matches/{match_id}/result", json=match_result, headers=headers)

        # Check score: 10 (winner) + 20 (most runs) = 30 points
        response = client.get(f"/leagues/{league_id}/leaderboard", headers=headers)
        leaderboard = response.json()

        assert leaderboard["entries"][0]["total_points"] == 30

    def test_prediction_deadline_enforcement(
        self, client, db_session, test_tournament, test_teams
    ):
        """Test that predictions cannot be made after match starts."""
        # Setup
        user_data = {"username": "user", "email": "user@test.com", "password": "pass"}
        client.post("/auth/signup", json=user_data)

        response = client.post("/auth/login", data={"username": "user", "password": "pass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create match that already started
        team1, team2 = test_teams
        match_data = {
            "tournament_id": test_tournament.id,
            "team_1_id": team1.id,
            "team_2_id": team2.id,
            "start_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        }
        response = client.post("/admin/matches/", json=match_data, headers=headers)
        match_id = response.json()["id"]

        # Get players
        response = client.get(f"/matches/{match_id}/players")
        team1_players = response.json()["team_1_players"]
        team2_players = response.json()["team_2_players"]

        # Try to make prediction after match started
        prediction = {
            "match_id": match_id,
            "predicted_winner_id": team1.id,
            "predicted_most_runs_player_id": team1_players[0]["id"],
            "predicted_most_wickets_player_id": team2_players[4]["id"],
            "predicted_pom_player_id": team1_players[0]["id"]
        }
        response = client.post("/predictions/", json=prediction, headers=headers)

        # Should be rejected
        assert response.status_code == 400
        assert "already started" in response.json()["detail"].lower()

    def test_update_prediction_before_match(
        self, client, db_session, test_tournament, test_teams
    ):
        """Test that users can update predictions before match starts."""
        # Setup
        user_data = {"username": "user", "email": "user@test.com", "password": "pass"}
        client.post("/auth/signup", json=user_data)

        response = client.post("/auth/login", data={"username": "user", "password": "pass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create future match
        team1, team2 = test_teams
        match_data = {
            "tournament_id": test_tournament.id,
            "team_1_id": team1.id,
            "team_2_id": team2.id,
            "start_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        }
        response = client.post("/admin/matches/", json=match_data, headers=headers)
        match_id = response.json()["id"]

        # Get players
        response = client.get(f"/matches/{match_id}/players")
        team1_players = response.json()["team_1_players"]
        team2_players = response.json()["team_2_players"]

        # Make initial prediction
        prediction = {
            "match_id": match_id,
            "predicted_winner_id": team1.id,
            "predicted_most_runs_player_id": team1_players[0]["id"],
            "predicted_most_wickets_player_id": team2_players[4]["id"],
            "predicted_pom_player_id": team1_players[0]["id"]
        }
        response = client.post("/predictions/", json=prediction, headers=headers)
        assert response.status_code == 201

        # Update prediction (change winner)
        updated_prediction = {
            **prediction,
            "predicted_winner_id": team2.id
        }
        response = client.post("/predictions/", json=updated_prediction, headers=headers)
        assert response.status_code == 200

        # Verify update
        response = client.get("/predictions/my", headers=headers)
        predictions = response.json()
        assert len(predictions) == 1
        assert predictions[0]["predicted_winner_id"] == team2.id

    def test_multiple_matches_leaderboard(
        self, client, db_session, test_tournament, test_teams
    ):
        """Test leaderboard with points from multiple matches."""
        # Setup two users
        for i in range(1, 3):
            user_data = {
                "username": f"user{i}",
                "email": f"user{i}@test.com",
                "password": "pass"
            }
            client.post("/auth/signup", json=user_data)

        # Login both users
        tokens = []
        for i in range(1, 3):
            response = client.post(
                "/auth/login",
                data={"username": f"user{i}", "password": "pass"}
            )
            tokens.append(response.json()["access_token"])

        # User 1 creates league
        response = client.post(
            "/leagues/",
            json={"name": "Multi-Match League"},
            headers={"Authorization": f"Bearer {tokens[0]}"}
        )
        league_id = response.json()["id"]
        invite_code = response.json()["invite_code"]

        # User 2 joins
        client.post(
            "/leagues/join",
            json={"invite_code": invite_code},
            headers={"Authorization": f"Bearer {tokens[1]}"}
        )

        # Create 3 matches
        team1, team2 = test_teams
        match_ids = []

        for i in range(3):
            match_data = {
                "tournament_id": test_tournament.id,
                "team_1_id": team1.id,
                "team_2_id": team2.id,
                "start_time": (
                    datetime.now(timezone.utc) + timedelta(hours=i+1)
                ).isoformat()
            }
            response = client.post(
                "/admin/matches/",
                json=match_data,
                headers={"Authorization": f"Bearer {tokens[0]}"}
            )
            match_ids.append(response.json()["id"])

        # Get players once
        response = client.get(f"/matches/{match_ids[0]}/players")
        team1_players = response.json()["team_1_players"]
        team2_players = response.json()["team_2_players"]

        # Both users make predictions for all matches
        # User 1 predicts all correctly for all matches
        # User 2 predicts winner correctly only
        for match_id in match_ids:
            # User 1 - perfect predictions
            prediction = {
                "match_id": match_id,
                "predicted_winner_id": team1.id,
                "predicted_most_runs_player_id": team1_players[0]["id"],
                "predicted_most_wickets_player_id": team2_players[4]["id"],
                "predicted_pom_player_id": team1_players[0]["id"]
            }
            client.post(
                "/predictions/",
                json=prediction,
                headers={"Authorization": f"Bearer {tokens[0]}"}
            )

            # User 2 - only winner correct
            prediction = {
                "match_id": match_id,
                "predicted_winner_id": team1.id,
                "predicted_most_runs_player_id": team2_players[0]["id"],
                "predicted_most_wickets_player_id": team1_players[4]["id"],
                "predicted_pom_player_id": team2_players[0]["id"]
            }
            client.post(
                "/predictions/",
                json=prediction,
                headers={"Authorization": f"Bearer {tokens[1]}"}
            )

        # Set results for all matches
        match_result = {
            "result_winner_id": team1.id,
            "result_most_runs_player_id": team1_players[0]["id"],
            "result_most_wickets_player_id": team2_players[4]["id"],
            "result_pom_player_id": team1_players[0]["id"]
        }

        for match_id in match_ids:
            client.post(
                f"/admin/matches/{match_id}/result",
                json=match_result,
                headers={"Authorization": f"Bearer {tokens[0]}"}
            )

        # Check final leaderboard
        response = client.get(
            f"/leagues/{league_id}/leaderboard",
            headers={"Authorization": f"Bearer {tokens[0]}"}
        )
        leaderboard = response.json()
        entries = sorted(leaderboard["entries"], key=lambda x: x["rank"])

        # User 1: 3 matches * 100 points = 300
        assert entries[0]["username"] == "user1"
        assert entries[0]["total_points"] == 300

        # User 2: 3 matches * 10 points = 30
        assert entries[1]["username"] == "user2"
        assert entries[1]["total_points"] == 30
