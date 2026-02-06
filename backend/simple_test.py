#!/usr/bin/env python3
"""
Simple Test Runner - No compilation required
Works without Xcode Command Line Tools
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from app.main import app
from app.database import get_db
from app.models.base import Base

TEST_DB = "sqlite:///./simple_test.db"

def print_step(msg, status="✓"):
    """Print test step with status."""
    print(f"{status} {msg}")

def test_complete_flow():
    """Test complete tournament flow without pytest."""
    print("\n" + "="*60)
    print("🏏 Fantasy Cricket League - Simple Test Runner")
    print("="*60 + "\n")

    # Setup
    engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    tests_passed = 0
    tests_failed = 0

    try:
        # Test 1: Health Check
        print("Test 1: API Health Check")
        response = client.get("/health")
        if response.status_code == 200:
            print_step("API is healthy")
            tests_passed += 1
        else:
            print_step(f"Health check failed: {response.status_code}", "✗")
            tests_failed += 1

        # Test 2: Create Test Data
        print("\nTest 2: Creating Test Data")
        from app.models.tournament import Tournament
        from app.models.team import Team
        from app.models.player import Player

        tournament = Tournament(
            name="Test Tournament 2025",
            start_date=datetime.now(timezone.utc).date(),
            end_date=(datetime.now(timezone.utc) + timedelta(days=30)).date()
        )
        session.add(tournament)

        team1 = Team(name="Mumbai Indians", short_name="MI")
        team2 = Team(name="Chennai Super Kings", short_name="CSK")
        session.add_all([team1, team2])
        session.commit()

        # Add players
        for i in range(11):
            session.add(Player(name=f"MI Player {i+1}", team_id=team1.id, role="Batsman"))
            session.add(Player(name=f"CSK Player {i+1}", team_id=team2.id, role="Bowler"))
        session.commit()

        print_step(f"Created tournament: {tournament.name}")
        print_step(f"Created teams: {team1.name} vs {team2.name}")
        print_step(f"Created 22 players (11 per team)")
        tests_passed += 1

        # Test 3: User Signup
        print("\nTest 3: User Registration")
        response = client.post("/auth/signup", json={
            "username": "testuser1",
            "email": "user1@test.com",
            "password": "password123"
        })
        if response.status_code == 201:
            user1_data = response.json()
            print_step(f"User 1 registered: {user1_data['username']}")
            tests_passed += 1
        else:
            print_step(f"User 1 signup failed: {response.text}", "✗")
            tests_failed += 1
            return

        response = client.post("/auth/signup", json={
            "username": "testuser2",
            "email": "user2@test.com",
            "password": "password123"
        })
        if response.status_code == 201:
            user2_data = response.json()
            print_step(f"User 2 registered: {user2_data['username']}")
            tests_passed += 1
        else:
            print_step(f"User 2 signup failed: {response.text}", "✗")
            tests_failed += 1
            return

        # Test 4: User Login
        print("\nTest 4: User Authentication")
        response = client.post("/auth/login", data={
            "username": "testuser1",
            "password": "password123"
        })
        if response.status_code == 200:
            token1 = response.json()["access_token"]
            headers1 = {"Authorization": f"Bearer {token1}"}
            print_step("User 1 logged in successfully")
            tests_passed += 1
        else:
            print_step(f"User 1 login failed", "✗")
            tests_failed += 1
            return

        response = client.post("/auth/login", data={
            "username": "testuser2",
            "password": "password123"
        })
        if response.status_code == 200:
            token2 = response.json()["access_token"]
            headers2 = {"Authorization": f"Bearer {token2}"}
            print_step("User 2 logged in successfully")
            tests_passed += 1
        else:
            print_step(f"User 2 login failed", "✗")
            tests_failed += 1
            return

        # Test 5: Create League
        print("\nTest 5: League Management")
        response = client.post("/leagues/",
            json={"name": "Premier League"},
            headers=headers1
        )
        if response.status_code == 201:
            league = response.json()
            league_id = league["id"]
            invite_code = league["invite_code"]
            print_step(f"League created: {league['name']}")
            print_step(f"Invite code generated: {invite_code}")
            tests_passed += 1
        else:
            print_step(f"League creation failed", "✗")
            tests_failed += 1
            return

        # Test 6: Join League
        response = client.post("/leagues/join",
            json={"invite_code": invite_code},
            headers=headers2
        )
        if response.status_code == 200:
            print_step(f"User 2 joined league with code: {invite_code}")
            tests_passed += 1
        else:
            print_step(f"Join league failed", "✗")
            tests_failed += 1
            return

        # Test 7: Create Match
        print("\nTest 7: Match Creation")
        match_data = {
            "tournament_id": tournament.id,
            "team_1_id": team1.id,
            "team_2_id": team2.id,
            "start_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        }
        response = client.post("/admin/matches/",
            json=match_data,
            headers=headers1
        )
        if response.status_code == 201:
            match = response.json()
            match_id = match["id"]
            print_step(f"Match created: {match['team_1']['name']} vs {match['team_2']['name']}")
            tests_passed += 1
        else:
            print_step(f"Match creation failed", "✗")
            tests_failed += 1
            return

        # Test 8: Get Match Players
        print("\nTest 8: Fetching Match Details")
        response = client.get(f"/matches/{match_id}/players")
        if response.status_code == 200:
            match_info = response.json()
            team1_players = match_info["team_1_players"]
            team2_players = match_info["team_2_players"]
            print_step(f"Retrieved {len(team1_players)} players from {match_info['team_1']['name']}")
            print_step(f"Retrieved {len(team2_players)} players from {match_info['team_2']['name']}")
            tests_passed += 1
        else:
            print_step(f"Get players failed", "✗")
            tests_failed += 1
            return

        # Test 9: Make Predictions
        print("\nTest 9: Making Predictions")

        # User 1 - Perfect predictions
        pred1 = {
            "match_id": match_id,
            "predicted_winner_id": team1.id,
            "predicted_most_runs_player_id": team1_players[0]["id"],
            "predicted_most_wickets_player_id": team2_players[0]["id"],
            "predicted_pom_player_id": team1_players[0]["id"]
        }
        response = client.post("/predictions/", json=pred1, headers=headers1)
        if response.status_code == 201:
            print_step(f"User 1 prediction submitted")
            tests_passed += 1
        else:
            print_step(f"User 1 prediction failed: {response.text}", "✗")
            tests_failed += 1

        # User 2 - Only winner correct
        pred2 = {
            "match_id": match_id,
            "predicted_winner_id": team1.id,
            "predicted_most_runs_player_id": team2_players[1]["id"],
            "predicted_most_wickets_player_id": team1_players[1]["id"],
            "predicted_pom_player_id": team2_players[1]["id"]
        }
        response = client.post("/predictions/", json=pred2, headers=headers2)
        if response.status_code == 201:
            print_step(f"User 2 prediction submitted")
            tests_passed += 1
        else:
            print_step(f"User 2 prediction failed", "✗")
            tests_failed += 1

        # Test 10: Set Match Results
        print("\nTest 10: Setting Match Results")
        result = {
            "result_winner_id": team1.id,
            "result_most_runs_player_id": team1_players[0]["id"],
            "result_most_wickets_player_id": team2_players[0]["id"],
            "result_pom_player_id": team1_players[0]["id"]
        }
        response = client.post(f"/admin/matches/{match_id}/result",
            json=result,
            headers=headers1
        )
        if response.status_code == 200:
            result_data = response.json()
            print_step(f"Match completed: {result_data['status']}")
            print_step(f"Predictions processed: {result_data['predictions_processed']}")
            tests_passed += 1
        else:
            print_step(f"Set result failed", "✗")
            tests_failed += 1
            return

        # Test 11: Check Leaderboard
        print("\nTest 11: Leaderboard Verification")
        response = client.get(f"/leagues/{league_id}/leaderboard", headers=headers1)
        if response.status_code == 200:
            leaderboard = response.json()
            entries = sorted(leaderboard["entries"], key=lambda x: x["rank"])

            print_step(f"Leaderboard retrieved for league: {leaderboard['league_name']}")
            print("\n" + "─"*60)
            print("📊 FINAL LEADERBOARD")
            print("─"*60)

            for entry in entries:
                rank_emoji = "🥇" if entry["rank"] == 1 else "🥈" if entry["rank"] == 2 else "🥉"
                print(f"{rank_emoji} Rank {entry['rank']}: {entry['username']:20s} {entry['total_points']:4d} points")

            print("─"*60)

            # Verify scores
            user1_score = next(e for e in entries if e["username"] == "testuser1")
            user2_score = next(e for e in entries if e["username"] == "testuser2")

            if user1_score["total_points"] == 100 and user2_score["total_points"] == 10:
                print_step("\nScore calculation correct!")
                print_step(f"  User 1: 100 points (all predictions correct)")
                print_step(f"  User 2: 10 points (only winner correct)")
                tests_passed += 1
            else:
                print_step(f"\nScore mismatch! Expected 100 & 10, got {user1_score['total_points']} & {user2_score['total_points']}", "✗")
                tests_failed += 1

        else:
            print_step(f"Leaderboard retrieval failed", "✗")
            tests_failed += 1

        # Summary
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        print(f"✅ Tests Passed: {tests_passed}")
        print(f"❌ Tests Failed: {tests_failed}")
        print(f"📊 Success Rate: {(tests_passed/(tests_passed+tests_failed)*100):.1f}%")
        print("="*60)

        if tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED! Your Fantasy Cricket League is working perfectly!\n")
        else:
            print(f"\n⚠️  Some tests failed. Please review the errors above.\n")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1

    finally:
        session.close()
        engine.dispose()
        if os.path.exists("simple_test.db"):
            os.remove("simple_test.db")

    return tests_failed == 0

if __name__ == "__main__":
    success = test_complete_flow()
    sys.exit(0 if success else 1)
