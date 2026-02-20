#!/usr/bin/env python3
"""
Tournament Simulation Script
=============================
Simulates 10 users playing through a full T20 World Cup tournament:
signup → league → predictions → results → scoring → leaderboard.

Prerequisites:
  - Backend running at http://localhost:8000
  - T20 WC data seeded (python seed_t20wc.py)

Usage:
  cd backend && source venv/bin/activate && python simulate_tournament.py
"""

import random
import sys

import httpx

BASE_URL = "http://localhost:8000"
NUM_USERS = 10

# Prediction strategies
ORACLE = "Oracle"          # All correct (matches results we set)
CONTRARIAN = "Contrarian"  # Always picks team_2 winner + team_2 players
RANDOM = "Random"          # Random picks
HALF_RIGHT = "Half-right"  # Correct winner, wrong players
CLUELESS = "Clueless"      # Always wrong

USER_STRATEGIES = {
    1: ORACLE,
    2: CONTRARIAN,
    3: RANDOM, 4: RANDOM, 5: RANDOM,
    6: HALF_RIGHT, 7: HALF_RIGHT, 8: HALF_RIGHT,
    9: CLUELESS, 10: CLUELESS,
}

# Scoring constants (must match backend/app/services/scoring.py)
PTS_WINNER = 10
PTS_MOST_RUNS = 20
PTS_MOST_WICKETS = 20
PTS_POM = 50
PTS_MAX = PTS_WINNER + PTS_MOST_RUNS + PTS_MOST_WICKETS + PTS_POM  # 100


def reset_matches_and_predictions():
    """Reset all matches to SCHEDULED with future start times, and delete
    predictions from sim_users so the simulation starts clean."""
    from datetime import datetime, timedelta, timezone

    from app.database import SessionLocal
    from app.models.match import Match, MatchStatus
    from app.models.prediction import Prediction
    from app.models.user import User

    db = SessionLocal()
    try:
        # Delete predictions from sim_users only (don't touch real users)
        sim_users = db.query(User).filter(User.username.like("sim_user_%")).all()
        sim_user_ids = [u.id for u in sim_users]
        if sim_user_ids:
            deleted = db.query(Prediction).filter(
                Prediction.user_id.in_(sim_user_ids)
            ).delete(synchronize_session="fetch")
            print(f"  Cleared {deleted} old simulation predictions")

        # Reset all matches to SCHEDULED with staggered future times
        matches = db.query(Match).all()
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        for i, match in enumerate(matches):
            match.status = MatchStatus.SCHEDULED
            match.result_winner_id = None
            match.result_most_runs_player_id = None
            match.result_most_wickets_player_id = None
            match.result_pom_player_id = None
            # Stagger by 1 hour each so they're all in the future
            match.start_time = tomorrow + timedelta(hours=i)

        db.commit()
        print(f"  Reset {len(matches)} matches to SCHEDULED (start times: tomorrow+)")
    finally:
        db.close()


def api(method: str, path: str, token: str | None = None, **kwargs) -> httpx.Response:
    """Make an API call and return the response."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = httpx.request(method, f"{BASE_URL}{path}", headers=headers, timeout=30, follow_redirects=True, **kwargs)
    return resp


# ── Phase 1: Setup ──────────────────────────────────────────────────────────

def create_users() -> list[dict]:
    """Create 10 users and return their info with JWT tokens."""
    users = []
    for i in range(1, NUM_USERS + 1):
        username = f"sim_user_{i}"
        email = f"sim_user_{i}@example.com"
        password = f"SimPass{i}!"

        # Signup
        resp = api("POST", "/auth/signup", json={
            "username": username,
            "email": email,
            "password": password,
        })
        if resp.status_code == 201:
            print(f"  Created {username}")
        elif resp.status_code == 400 and "already" in resp.text.lower():
            print(f"  {username} already exists, logging in")
        else:
            print(f"  WARNING: signup {username} returned {resp.status_code}: {resp.text}")

        # Login (OAuth2 form)
        resp = api("POST", "/auth/login", data={
            "username": username,
            "password": password,
        })
        if resp.status_code != 200:
            print(f"  ERROR: login failed for {username}: {resp.status_code} {resp.text}")
            sys.exit(1)

        token_data = resp.json()
        users.append({
            "index": i,
            "username": username,
            "token": token_data["access_token"],
            "strategy": USER_STRATEGIES[i],
        })

    return users


def make_admin(username: str):
    """Promote a user to admin via direct DB call."""
    from app.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"  ERROR: user {username} not found in DB")
            sys.exit(1)
        user.is_admin = True
        db.commit()
        print(f"  Made {username} admin")
    finally:
        db.close()


def create_and_join_league(users: list[dict]) -> dict:
    """Create a league as user 1, have all others join it."""
    admin_token = users[0]["token"]

    # Create league
    resp = api("POST", "/leagues/", token=admin_token, json={"name": "Simulation League"})
    if resp.status_code != 201:
        print(f"  ERROR: create league failed: {resp.status_code} {resp.text}")
        sys.exit(1)

    league = resp.json()
    invite_code = league["invite_code"]
    print(f"  Created league '{league['name']}' (invite: {invite_code})")

    # All other users join
    for user in users[1:]:
        resp = api("POST", "/leagues/join", token=user["token"], json={
            "invite_code": invite_code,
        })
        if resp.status_code == 200:
            pass  # joined
        elif resp.status_code == 400 and "already" in resp.text.lower():
            pass  # already a member
        else:
            print(f"  WARNING: {user['username']} join failed: {resp.status_code} {resp.text}")

    print(f"  All {NUM_USERS} users in league")
    return league


# ── Phase 2: Predictions ────────────────────────────────────────────────────

def fetch_matches() -> list[dict]:
    """Fetch all matches (including completed for idempotency)."""
    resp = api("GET", "/matches?include_completed=true")
    if resp.status_code != 200:
        print(f"  ERROR: fetch matches failed: {resp.status_code}")
        sys.exit(1)
    matches = resp.json()
    return matches


def fetch_match_players(match_id: int, token: str) -> dict:
    """Fetch players for both teams in a match."""
    resp = api("GET", f"/matches/{match_id}/players", token=token)
    if resp.status_code != 200:
        print(f"  ERROR: fetch players for match {match_id} failed: {resp.status_code}")
        return {}
    return resp.json()


def pick_prediction(strategy: str, match: dict, players_data: dict) -> dict | None:
    """Generate a prediction based on the user's strategy.

    Returns the prediction payload or None if not enough data.
    """
    team_1 = match["team_1"]
    team_2 = match["team_2"]
    t1_players = players_data.get("team_1_players", [])
    t2_players = players_data.get("team_2_players", [])

    if not t1_players or not t2_players:
        return None

    # Find first batsman/bowler per team for deterministic picks
    t1_batsmen = [p for p in t1_players if p["role"] in ("Batsman", "Wicketkeeper", "All-Rounder")]
    t2_batsmen = [p for p in t2_players if p["role"] in ("Batsman", "Wicketkeeper", "All-Rounder")]
    t1_bowlers = [p for p in t1_players if p["role"] in ("Bowler", "All-Rounder")]
    t2_bowlers = [p for p in t2_players if p["role"] in ("Bowler", "All-Rounder")]

    # Fallback: if no role-specific players found, use any player
    if not t1_batsmen:
        t1_batsmen = t1_players
    if not t2_batsmen:
        t2_batsmen = t2_players
    if not t1_bowlers:
        t1_bowlers = t1_players
    if not t2_bowlers:
        t2_bowlers = t2_players

    # The "correct" result will always be:
    #   winner=team_1, most_runs=t1_batsmen[0], most_wickets=t2_bowlers[0], pom=t1_batsmen[0]
    correct_winner = team_1["id"]
    correct_runs = t1_batsmen[0]["id"]
    correct_wickets = t2_bowlers[0]["id"]
    correct_pom = t1_batsmen[0]["id"]

    wrong_winner = team_2["id"]
    wrong_runs = t2_batsmen[0]["id"]
    wrong_wickets = t1_bowlers[0]["id"]
    wrong_pom = t2_batsmen[0]["id"]

    all_players = t1_players + t2_players

    if strategy == ORACLE:
        return {
            "predicted_winner_id": correct_winner,
            "predicted_most_runs_player_id": correct_runs,
            "predicted_most_wickets_player_id": correct_wickets,
            "predicted_pom_player_id": correct_pom,
        }
    elif strategy == CONTRARIAN:
        return {
            "predicted_winner_id": wrong_winner,
            "predicted_most_runs_player_id": wrong_runs,
            "predicted_most_wickets_player_id": wrong_wickets,
            "predicted_pom_player_id": wrong_pom,
        }
    elif strategy == RANDOM:
        return {
            "predicted_winner_id": random.choice([team_1["id"], team_2["id"]]),
            "predicted_most_runs_player_id": random.choice(all_players)["id"],
            "predicted_most_wickets_player_id": random.choice(all_players)["id"],
            "predicted_pom_player_id": random.choice(all_players)["id"],
        }
    elif strategy == HALF_RIGHT:
        # Correct winner, wrong everything else
        return {
            "predicted_winner_id": correct_winner,
            "predicted_most_runs_player_id": wrong_runs,
            "predicted_most_wickets_player_id": wrong_wickets,
            "predicted_pom_player_id": wrong_pom,
        }
    elif strategy == CLUELESS:
        return {
            "predicted_winner_id": wrong_winner,
            "predicted_most_runs_player_id": wrong_runs,
            "predicted_most_wickets_player_id": wrong_wickets,
            "predicted_pom_player_id": wrong_pom,
        }

    return None


def submit_predictions(users: list[dict], matches: list[dict]) -> tuple[int, int]:
    """Submit predictions for all users across all matches.

    Returns (total_submitted, total_skipped).
    """
    submitted = 0
    skipped = 0

    # Cache players per match (shared across users)
    players_cache: dict[int, dict] = {}

    for match in matches:
        mid = match["id"]
        t1_short = match["team_1"]["short_name"]
        t2_short = match["team_2"]["short_name"]

        if match["status"] == "COMPLETED":
            print(f"  Match {mid} ({t1_short} vs {t2_short}): already completed, skipping")
            skipped += 1
            continue

        # Fetch players once per match
        if mid not in players_cache:
            players_cache[mid] = fetch_match_players(mid, users[0]["token"])

        players_data = players_cache[mid]
        if not players_data:
            skipped += 1
            continue

        match_submitted = 0
        for user in users:
            prediction = pick_prediction(user["strategy"], match, players_data)
            if not prediction:
                continue

            prediction["match_id"] = mid
            resp = api("POST", "/predictions/", token=user["token"], json=prediction)

            if resp.status_code in (200, 201):
                match_submitted += 1
            elif resp.status_code == 400 and "started" in resp.text.lower():
                # Match already started — skip all remaining users for this match
                print(f"  Match {mid} ({t1_short} vs {t2_short}): already started, skipping")
                skipped += 1
                break
            else:
                print(f"  WARNING: prediction by {user['username']} for match {mid}: "
                      f"{resp.status_code} {resp.text}")

        submitted += match_submitted

    return submitted, skipped


# ── Phase 3: Results & Scoring ──────────────────────────────────────────────

def set_results(admin_token: str, matches: list[dict]) -> int:
    """Set results for all scheduled matches. Returns count of results set."""
    results_set = 0

    for match in matches:
        mid = match["id"]
        t1_short = match["team_1"]["short_name"]
        t2_short = match["team_2"]["short_name"]

        if match["status"] == "COMPLETED":
            results_set += 1  # already done
            continue

        # Fetch players to determine result
        players_data = fetch_match_players(mid, admin_token)
        if not players_data:
            print(f"  Match {mid}: no players data, skipping result")
            continue

        t1_players = players_data.get("team_1_players", [])
        t2_players = players_data.get("team_2_players", [])

        t1_batsmen = [p for p in t1_players if p["role"] in ("Batsman", "Wicketkeeper", "All-Rounder")]
        t2_bowlers = [p for p in t2_players if p["role"] in ("Bowler", "All-Rounder")]

        if not t1_batsmen:
            t1_batsmen = t1_players
        if not t2_bowlers:
            t2_bowlers = t2_players

        if not t1_batsmen or not t2_bowlers:
            print(f"  Match {mid}: insufficient players, skipping")
            continue

        result = {
            "result_winner_id": match["team_1"]["id"],
            "result_most_runs_player_id": t1_batsmen[0]["id"],
            "result_most_wickets_player_id": t2_bowlers[0]["id"],
            "result_pom_player_id": t1_batsmen[0]["id"],
        }

        resp = api("POST", f"/admin/matches/{mid}/result", token=admin_token, json=result)
        if resp.status_code == 200:
            data = resp.json()
            processed = data.get("predictions_processed", 0)
            print(f"  Match {mid} ({t1_short} vs {t2_short}): result set, {processed} predictions scored")
            results_set += 1
        else:
            print(f"  WARNING: set result match {mid}: {resp.status_code} {resp.text}")

    return results_set


# ── Phase 4: Verification ──────────────────────────────────────────────────

def verify_leaderboard(league_id: int, token: str, matches_count: int, users: list[dict]):
    """Fetch leaderboard and verify scoring correctness."""
    resp = api("GET", f"/leagues/{league_id}/leaderboard", token=token)
    if resp.status_code != 200:
        print(f"  ERROR: fetch leaderboard failed: {resp.status_code}")
        return

    data = resp.json()
    entries = data["entries"]

    # Build lookup
    strategy_by_username = {u["username"]: u["strategy"] for u in users}

    print(f"\n{'=' * 55}")
    print(f"  FINAL LEADERBOARD — {data['league_name']}")
    print(f"{'=' * 55}")

    for entry in entries:
        username = entry["username"]
        strategy = strategy_by_username.get(username, "?")
        pts = entry["total_points"]
        print(f"  #{entry['rank']:<3} {username:<18} ({strategy:<11}) — {pts:>5} pts")

    print(f"{'=' * 55}")

    # Verification checks
    print(f"\n{'=' * 55}")
    print("  VERIFICATION")
    print(f"{'=' * 55}")

    points_by_strategy: dict[str, list[int]] = {}
    for entry in entries:
        username = entry["username"]
        strategy = strategy_by_username.get(username, "?")
        points_by_strategy.setdefault(strategy, []).append(entry["total_points"])

    all_pass = True

    # Oracle should have max points
    oracle_pts = points_by_strategy.get(ORACLE, [0])
    expected_oracle = PTS_MAX * matches_count
    if oracle_pts[0] == expected_oracle:
        print(f"  OK  Oracle has max points ({oracle_pts[0]})")
    elif oracle_pts[0] > 0 and oracle_pts[0] == max(e["total_points"] for e in entries):
        print(f"  OK  Oracle has highest points ({oracle_pts[0]}, expected {expected_oracle} for {matches_count} matches)")
    else:
        print(f"  FAIL  Oracle has {oracle_pts[0]} pts, expected {expected_oracle}")
        all_pass = False

    # Clueless should have 0
    clueless_pts = points_by_strategy.get(CLUELESS, [0])
    if all(p == 0 for p in clueless_pts):
        print(f"  OK  Clueless users have 0 points")
    else:
        print(f"  FAIL  Clueless users have {clueless_pts} (expected all 0)")
        all_pass = False

    # Half-right should have exactly 10 pts per match (winner only)
    half_right_pts = points_by_strategy.get(HALF_RIGHT, [])
    expected_half = PTS_WINNER * matches_count
    if half_right_pts and all(p == expected_half for p in half_right_pts):
        print(f"  OK  Half-right users have {expected_half} pts each ({PTS_WINNER}/match)")
    elif half_right_pts:
        print(f"  FAIL  Half-right users have {half_right_pts} (expected {expected_half} each)")
        all_pass = False
    else:
        print(f"  SKIP  No half-right data")

    # Contrarian should have 0 (all wrong)
    contrarian_pts = points_by_strategy.get(CONTRARIAN, [0])
    if all(p == 0 for p in contrarian_pts):
        print(f"  OK  Contrarian has 0 points")
    else:
        print(f"  FAIL  Contrarian has {contrarian_pts} (expected 0)")
        all_pass = False

    # Random should be somewhere in between
    random_pts = points_by_strategy.get(RANDOM, [])
    if random_pts:
        print(f"  INFO  Random users have {random_pts} pts (varied, as expected)")

    if all_pass:
        print(f"\n  ALL CHECKS PASSED")
    else:
        print(f"\n  SOME CHECKS FAILED")

    print(f"{'=' * 55}")


def print_per_match_breakdown(users: list[dict]):
    """Print per-match prediction details for each user."""
    print(f"\n{'=' * 55}")
    print("  PER-USER PREDICTION BREAKDOWN")
    print(f"{'=' * 55}")

    for user in users:
        resp = api("GET", "/predictions/my/detailed", token=user["token"])
        if resp.status_code != 200:
            print(f"  {user['username']}: failed to fetch predictions")
            continue

        predictions = resp.json()
        processed = [p for p in predictions if p["is_processed"]]
        total_pts = sum(p["points_earned"] for p in processed)

        print(f"\n  {user['username']} ({user['strategy']}) — {total_pts} pts from {len(processed)} matches")
        for p in processed:
            t1 = p["team_1"]["short_name"]
            t2 = p["team_2"]["short_name"]
            pts = p["points_earned"]
            print(f"    Match {p['match_id']} ({t1} vs {t2}): {pts} pts")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  TOURNAMENT SIMULATION")
    print("=" * 55)

    # Check server is up
    try:
        resp = httpx.get(f"{BASE_URL}/docs", timeout=5)
    except httpx.ConnectError:
        print(f"\nERROR: Cannot connect to {BASE_URL}")
        print("Start the backend first: uvicorn app.main:app --reload")
        sys.exit(1)

    # Phase 0: Reset
    print("\n--- Phase 0: Reset ---")
    reset_matches_and_predictions()

    # Phase 1: Setup
    print("\n--- Phase 1: Setup ---")
    users = create_users()
    make_admin(users[0]["username"])
    league = create_and_join_league(users)

    # Phase 2: Predictions
    print("\n--- Phase 2: Predictions ---")
    matches = fetch_matches()
    scheduled = [m for m in matches if m["status"] == "SCHEDULED"]
    print(f"  Found {len(matches)} matches ({len(scheduled)} scheduled)")

    if not scheduled:
        print("  ERROR: No scheduled matches found. Seed data first: python seed_t20wc.py")
        sys.exit(1)

    submitted, skipped = submit_predictions(users, matches)
    print(f"  Submitted {submitted} predictions ({skipped} matches skipped)")

    # Phase 3: Results & Scoring
    print("\n--- Phase 3: Results & Scoring ---")
    results_set = set_results(users[0]["token"], matches)
    print(f"  Set results for {results_set} matches")

    # Phase 4: Verification
    print("\n--- Phase 4: Verification ---")
    # Re-fetch matches to count how many were actually processed
    all_matches = fetch_matches()
    completed = [m for m in all_matches if m["status"] == "COMPLETED"]
    print(f"  {len(completed)} matches completed")

    verify_leaderboard(league["id"], users[0]["token"], len(completed), users)
    print_per_match_breakdown(users)

    print(f"\n{'=' * 55}")
    print("  SIMULATION COMPLETE")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
