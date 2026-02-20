#!/usr/bin/env python3
"""
Quick Test Runner - Simulates the complete tournament flow
Run this to verify the entire system works correctly
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from app.main import app
from app.database import get_db
from app.models import Base

# Use a test database
TEST_DB = "sqlite:///./quick_test.db"

def run_complete_flow():
    """Run a complete tournament flow test."""
    print("🏏 Fantasy Cricket League - Quick Test")
    print("=" * 50)

    # Setup test database
    engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        # Step 1: Create tournament and teams
        print("\n✓ Creating tournament and teams...")
        from app.models.tournament import Tournament
        from app.models.team import Team
        from app.models.player import Player

        tournament = Tournament(
            name="Test Tournament",
            start_date=datetime.now(timezone.utc).date(),
            end_date=(datetime.now(timezone.utc) + timedelta(days=30)).date()
        )
        session.add(tournament)

        team1 = Team(name="Team A", short_name="TMA")
        team2 = Team(name="Team B", short_name="TMB")
        session.add_all([team1, team2])
        session.commit()

        # Add players
        for i in range(11):
            session.add(Player(name=f"TA Player {i+1}", team_id=team1.id, role="Batsman"))
            session.add(Player(name=f"TB Player {i+1}", team_id=team2.id, role="Bowler"))
        session.commit()

        # Step 2: Sign up users
        print("✓ Signing up users...")
        response = client.post("/auth/signup", json={
            "username": "player1",
            "email": "player1@test.com",
            "password": "test123"
        })
        assert response.status_code == 201, f"Signup failed: {response.text}"

        # Make player1 an admin
        from app.models.user import User
        admin_user = session.query(User).filter(User.username == "player1").first()
        admin_user.is_admin = True
        session.commit()

        response = client.post("/auth/signup", json={
            "username": "player2",
            "email": "player2@test.com",
            "password": "test123"
        })
        assert response.status_code == 201

        # Step 3: Login
        print("✓ Logging in users...")
        response = client.post("/auth/login", data={
            "username": "player1",
            "password": "test123"
        })
        assert response.status_code == 200
        token1 = response.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        response = client.post("/auth/login", data={
            "username": "player2",
            "password": "test123"
        })
        token2 = response.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Step 4: Create league
        print("✓ Creating league...")
        response = client.post("/leagues/", json={"name": "Test League"}, headers=headers1)
        assert response.status_code == 201
        league_id = response.json()["id"]
        invite_code = response.json()["invite_code"]
        print(f"  League created with code: {invite_code}")

        # Step 5: Join league
        print("✓ Joining league...")
        response = client.post("/leagues/join", json={"invite_code": invite_code}, headers=headers2)
        assert response.status_code == 200

        # Step 6: Create match
        print("✓ Creating match...")
        match_data = {
            "tournament_id": tournament.id,
            "team_1_id": team1.id,
            "team_2_id": team2.id,
            "start_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        response = client.post("/admin/matches/", json=match_data, headers=headers1)
        assert response.status_code == 201, f"Create match failed: {response.text}"
        match_id = response.json()["id"]

        # Step 7: Get players for predictions
        print("✓ Fetching match players...")
        response = client.get(f"/matches/{match_id}/players", headers=headers1)
        assert response.status_code == 200, f"Get players failed: {response.text}"
        match_data = response.json()
        team1_players = match_data["team_1_players"]
        team2_players = match_data["team_2_players"]

        # Step 8: Make predictions
        print("✓ Making predictions...")
        # Player 1 - all correct
        prediction1 = {
            "match_id": match_id,
            "predicted_winner_id": team1.id,
            "predicted_most_runs_player_id": team1_players[0]["id"],
            "predicted_most_wickets_player_id": team2_players[0]["id"],
            "predicted_pom_player_id": team1_players[0]["id"]
        }
        response = client.post("/predictions/", json=prediction1, headers=headers1)
        assert response.status_code == 201, f"Prediction 1 failed: {response.text}"

        # Player 2 - only winner correct
        prediction2 = {
            "match_id": match_id,
            "predicted_winner_id": team1.id,
            "predicted_most_runs_player_id": team2_players[1]["id"],
            "predicted_most_wickets_player_id": team1_players[1]["id"],
            "predicted_pom_player_id": team2_players[1]["id"]
        }
        response = client.post("/predictions/", json=prediction2, headers=headers2)
        assert response.status_code == 201, f"Prediction 2 failed: {response.text}"

        # Step 9: Set match results
        print("✓ Setting match results...")
        result = {
            "result_winner_id": team1.id,
            "result_most_runs_player_id": team1_players[0]["id"],
            "result_most_wickets_player_id": team2_players[0]["id"],
            "result_pom_player_id": team1_players[0]["id"]
        }
        response = client.post(f"/admin/matches/{match_id}/result", json=result, headers=headers1)
        assert response.status_code == 200, f"Set result failed: {response.text}"
        print(f"  Processed {response.json()['predictions_processed']} predictions")

        # Step 10: Check leaderboard
        print("✓ Checking leaderboard...")
        response = client.get(f"/leagues/{league_id}/leaderboard", headers=headers1)
        assert response.status_code == 200, f"Leaderboard failed: {response.text}"
        leaderboard = response.json()

        print("\n📊 Final Leaderboard:")
        print("-" * 50)
        for entry in sorted(leaderboard["entries"], key=lambda x: x["rank"]):
            print(f"  Rank {entry['rank']}: {entry['username']:15s} - {entry['total_points']:3d} points")

        # Verify results
        entries = {e["username"]: e["total_points"] for e in leaderboard["entries"]}
        assert entries["player1"] == 100, "Player 1 should have 100 points"
        assert entries["player2"] == 10, "Player 2 should have 10 points"

        print("\n" + "=" * 50)
        print("✅ All tests passed successfully!")
        print("=" * 50)

        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()
        engine.dispose()
        # Clean up test database
        if os.path.exists("quick_test.db"):
            os.remove("quick_test.db")

if __name__ == "__main__":
    success = run_complete_flow()
    sys.exit(0 if success else 1)
