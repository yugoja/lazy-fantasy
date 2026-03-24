#!/usr/bin/env python3
"""
Seed mock predictions for match 13 (RCB vs CSK) so the Friends' Picks
feature can be tested locally.

What it does:
  - Backdates match 13 start_time to yesterday so it's "locked"
  - Creates predictions for 5 mock users (all in league 1 "Office Fantasy XI")
  - Each user picks slightly different players for variety

Usage:
    cd backend && source venv/bin/activate
    venv/bin/python seed_mock_predictions.py          # seed
    venv/bin/python seed_mock_predictions.py --reset  # wipe and reseed
"""
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import User, Match, Prediction

MATCH_ID = 13  # RCB (team 13) vs CSK (team 5)
RCB_ID = 13
CSK_ID = 5

# Player IDs (from ipl2026 seed)
# RCB batsmen/WK
VIRAT       = 251
PATIDAR     = 249
# RCB bowlers/AR
HAZLEWOOD   = 266
BHUVI       = 269
RASIKH      = 267
KRUNAL      = 255
TIM_DAVID   = 257
# CSK batsmen/WK
RUTURAJ     = 74
BREVIS      = 77
DHONI       = 75
# CSK bowlers/AR
NOOR_AHMAD  = 91
KHALEEL     = 90
MUKESH      = 92
SHIVAM_DUBE = 82

# (username, winner_team_id, rcb_runs, csk_runs, rcb_wkts, csk_wkts, pom)
PREDICTIONS = [
    ("rohit_sharma",   RCB_ID, VIRAT,    RUTURAJ, HAZLEWOOD, NOOR_AHMAD,  VIRAT),
    ("virat_kohli",    RCB_ID, PATIDAR,  BREVIS,  BHUVI,     KHALEEL,     KRUNAL),
    ("ms_dhoni",       CSK_ID, VIRAT,    RUTURAJ, RASIKH,    MUKESH,      DHONI),
    ("jasprit_bumrah", RCB_ID, VIRAT,    BREVIS,  HAZLEWOOD, NOOR_AHMAD,  TIM_DAVID),
    ("hardik_pandya",  CSK_ID, PATIDAR,  RUTURAJ, BHUVI,     NOOR_AHMAD,  SHIVAM_DUBE),
]


def reset(db):
    deleted = db.query(Prediction).filter(Prediction.match_id == MATCH_ID).delete()
    db.commit()
    print(f"  Deleted {deleted} predictions for match {MATCH_ID}.")


def seed(db):
    # Backdate match to yesterday so it's locked
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    match = db.query(Match).filter(Match.id == MATCH_ID).first()
    if not match:
        print(f"  ERROR: Match {MATCH_ID} not found. Run the IPL 2026 seed first.")
        return
    match.start_time = yesterday.replace(tzinfo=None)  # stored as naive UTC in SQLite
    db.flush()
    print(f"  Backdated match {MATCH_ID} start_time to {yesterday.date()}.")

    for username, winner_id, rcb_runs, csk_runs, rcb_wkts, csk_wkts, pom in PREDICTIONS:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"  SKIP: user '{username}' not found — run seed_mock_data.py first.")
            continue

        existing = db.query(Prediction).filter(
            Prediction.match_id == MATCH_ID,
            Prediction.user_id == user.id,
        ).first()
        if existing:
            print(f"  Prediction already exists for {username}, skipping.")
            continue

        pred = Prediction(
            user_id=user.id,
            match_id=MATCH_ID,
            predicted_winner_id=winner_id,
            predicted_most_runs_team1_player_id=rcb_runs,
            predicted_most_runs_team2_player_id=csk_runs,
            predicted_most_wickets_team1_player_id=rcb_wkts,
            predicted_most_wickets_team2_player_id=csk_wkts,
            predicted_pom_player_id=pom,
        )
        db.add(pred)
        winner_name = "RCB" if winner_id == RCB_ID else "CSK"
        print(f"  Created prediction for {username}: {winner_name} to win, POM={pom}")

    db.commit()
    print("\n✅ Mock predictions seeded.")
    print("   Visit /predictions → Live/Done tab → Friends' picks to test the feature.")
    print("   Login as rohit@test.com / password123 (or any mock user).")


def main():
    db = SessionLocal()
    try:
        if "--reset" in sys.argv:
            reset(db)
        seed(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
