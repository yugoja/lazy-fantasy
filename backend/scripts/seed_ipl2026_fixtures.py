"""
Seed IPL 2026 fixtures (matches 21–70, April 13 – May 24).

Usage:
  # Local: clears all scheduled matches then inserts matches 21–70
  python scripts/seed_ipl2026_fixtures.py --mode local

  # Droplet: only inserts matches not already present (safe to re-run)
  python scripts/seed_ipl2026_fixtures.py --mode prod

Times are stored as UTC (IST = UTC+5:30):
  19:30 IST → 14:00 UTC
  15:30 IST → 10:00 UTC
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from app.database import SessionLocal
from app.models import Match, MatchStatus

TOURNAMENT_ID = 2

# Team code → DB id
TEAM_ID = {
    "CSK": 5, "DC": 6, "GT": 7, "KKR": 8, "LSG": 9,
    "MI": 10, "PBKS": 11, "RR": 12, "RCB": 13, "SRH": 14,
}

# IST time string → UTC hour (minutes always 0)
IST_TO_UTC = {
    "15:30 IST": (10, 0),
    "19:30 IST": (14, 0),
}

FIXTURES = [
    {"match_number": 21, "date": "2026-04-13", "time": "19:30 IST", "team1": "SRH", "team2": "RR"},
    {"match_number": 22, "date": "2026-04-14", "time": "19:30 IST", "team1": "CSK", "team2": "KKR"},
    {"match_number": 23, "date": "2026-04-15", "time": "19:30 IST", "team1": "RCB", "team2": "LSG"},
    {"match_number": 24, "date": "2026-04-16", "time": "19:30 IST", "team1": "MI",  "team2": "PBKS"},
    {"match_number": 25, "date": "2026-04-17", "time": "19:30 IST", "team1": "GT",  "team2": "KKR"},
    {"match_number": 26, "date": "2026-04-18", "time": "15:30 IST", "team1": "RCB", "team2": "DC"},
    {"match_number": 27, "date": "2026-04-18", "time": "19:30 IST", "team1": "SRH", "team2": "CSK"},
    {"match_number": 28, "date": "2026-04-19", "time": "15:30 IST", "team1": "KKR", "team2": "RR"},
    {"match_number": 29, "date": "2026-04-19", "time": "19:30 IST", "team1": "PBKS","team2": "LSG"},
    {"match_number": 30, "date": "2026-04-20", "time": "19:30 IST", "team1": "GT",  "team2": "MI"},
    {"match_number": 31, "date": "2026-04-21", "time": "19:30 IST", "team1": "SRH", "team2": "DC"},
    {"match_number": 32, "date": "2026-04-22", "time": "19:30 IST", "team1": "LSG", "team2": "RR"},
    {"match_number": 33, "date": "2026-04-23", "time": "19:30 IST", "team1": "MI",  "team2": "CSK"},
    {"match_number": 34, "date": "2026-04-24", "time": "19:30 IST", "team1": "RCB", "team2": "GT"},
    {"match_number": 35, "date": "2026-04-25", "time": "15:30 IST", "team1": "DC",  "team2": "PBKS"},
    {"match_number": 36, "date": "2026-04-25", "time": "19:30 IST", "team1": "RR",  "team2": "SRH"},
    {"match_number": 37, "date": "2026-04-26", "time": "15:30 IST", "team1": "GT",  "team2": "CSK"},
    {"match_number": 38, "date": "2026-04-26", "time": "19:30 IST", "team1": "LSG", "team2": "KKR"},
    {"match_number": 39, "date": "2026-04-27", "time": "19:30 IST", "team1": "DC",  "team2": "RCB"},
    {"match_number": 40, "date": "2026-04-28", "time": "19:30 IST", "team1": "PBKS","team2": "RR"},
    {"match_number": 41, "date": "2026-04-29", "time": "19:30 IST", "team1": "MI",  "team2": "SRH"},
    {"match_number": 42, "date": "2026-04-30", "time": "19:30 IST", "team1": "GT",  "team2": "RCB"},
    {"match_number": 43, "date": "2026-05-01", "time": "19:30 IST", "team1": "RR",  "team2": "DC"},
    {"match_number": 44, "date": "2026-05-02", "time": "19:30 IST", "team1": "CSK", "team2": "MI"},
    {"match_number": 45, "date": "2026-05-03", "time": "15:30 IST", "team1": "SRH", "team2": "KKR"},
    {"match_number": 46, "date": "2026-05-03", "time": "19:30 IST", "team1": "GT",  "team2": "PBKS"},
    {"match_number": 47, "date": "2026-05-04", "time": "19:30 IST", "team1": "MI",  "team2": "LSG"},
    {"match_number": 48, "date": "2026-05-05", "time": "19:30 IST", "team1": "DC",  "team2": "CSK"},
    {"match_number": 49, "date": "2026-05-06", "time": "19:30 IST", "team1": "SRH", "team2": "PBKS"},
    {"match_number": 50, "date": "2026-05-07", "time": "19:30 IST", "team1": "LSG", "team2": "RCB"},
    {"match_number": 51, "date": "2026-05-08", "time": "19:30 IST", "team1": "DC",  "team2": "KKR"},
    {"match_number": 52, "date": "2026-05-09", "time": "19:30 IST", "team1": "RR",  "team2": "GT"},
    {"match_number": 53, "date": "2026-05-10", "time": "15:30 IST", "team1": "CSK", "team2": "LSG"},
    {"match_number": 54, "date": "2026-05-10", "time": "19:30 IST", "team1": "RCB", "team2": "MI"},
    {"match_number": 55, "date": "2026-05-11", "time": "19:30 IST", "team1": "PBKS","team2": "DC"},
    {"match_number": 56, "date": "2026-05-12", "time": "19:30 IST", "team1": "GT",  "team2": "SRH"},
    {"match_number": 57, "date": "2026-05-13", "time": "19:30 IST", "team1": "RCB", "team2": "KKR"},
    {"match_number": 58, "date": "2026-05-14", "time": "19:30 IST", "team1": "PBKS","team2": "MI"},
    {"match_number": 59, "date": "2026-05-15", "time": "19:30 IST", "team1": "LSG", "team2": "CSK"},
    {"match_number": 60, "date": "2026-05-16", "time": "19:30 IST", "team1": "KKR", "team2": "GT"},
    {"match_number": 61, "date": "2026-05-17", "time": "15:30 IST", "team1": "PBKS","team2": "RCB"},
    {"match_number": 62, "date": "2026-05-17", "time": "19:30 IST", "team1": "DC",  "team2": "RR"},
    {"match_number": 63, "date": "2026-05-18", "time": "19:30 IST", "team1": "CSK", "team2": "SRH"},
    {"match_number": 64, "date": "2026-05-19", "time": "19:30 IST", "team1": "RR",  "team2": "LSG"},
    {"match_number": 65, "date": "2026-05-20", "time": "19:30 IST", "team1": "KKR", "team2": "MI"},
    {"match_number": 66, "date": "2026-05-21", "time": "19:30 IST", "team1": "CSK", "team2": "GT"},
    {"match_number": 67, "date": "2026-05-22", "time": "19:30 IST", "team1": "SRH", "team2": "RCB"},
    {"match_number": 68, "date": "2026-05-23", "time": "19:30 IST", "team1": "LSG", "team2": "PBKS"},
    {"match_number": 69, "date": "2026-05-24", "time": "15:30 IST", "team1": "MI",  "team2": "RR"},
    {"match_number": 70, "date": "2026-05-24", "time": "19:30 IST", "team1": "KKR", "team2": "DC"},
]


def make_start_time(date_str: str, time_str: str) -> datetime:
    hour, minute = IST_TO_UTC[time_str]
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.replace(hour=hour, minute=minute)


def run(mode: str):
    db = SessionLocal()

    if mode == "local":
        deleted = db.query(Match).filter(
            Match.tournament_id == TOURNAMENT_ID,
            Match.status == MatchStatus.SCHEDULED,
        ).delete()
        db.commit()
        print(f"Deleted {deleted} existing scheduled matches")

    # Build set of existing (team1, team2, date) to avoid dupes in prod mode
    existing = db.query(Match).filter(Match.tournament_id == TOURNAMENT_ID).all()
    existing_keys = {
        (m.team_1_id, m.team_2_id, m.start_time.date())
        for m in existing
    }

    inserted = 0
    skipped = 0
    for f in FIXTURES:
        t1 = TEAM_ID[f["team1"]]
        t2 = TEAM_ID[f["team2"]]
        start = make_start_time(f["date"], f["time"])
        key = (t1, t2, start.date())

        if key in existing_keys:
            skipped += 1
            continue

        db.add(Match(
            tournament_id=TOURNAMENT_ID,
            team_1_id=t1,
            team_2_id=t2,
            start_time=start,
            status=MatchStatus.SCHEDULED,
        ))
        inserted += 1

    db.commit()
    db.close()
    print(f"Inserted {inserted} matches, skipped {skipped} duplicates")
    print(f"Season runs: 2026-04-13 → 2026-05-24")


if __name__ == "__main__":
    mode = "local"
    if len(sys.argv) > 1 and sys.argv[1] in ("--mode", "-m") and len(sys.argv) > 2:
        mode = sys.argv[2]
    elif len(sys.argv) > 1 and sys.argv[1] in ("local", "prod"):
        mode = sys.argv[1]

    if mode not in ("local", "prod"):
        print("Usage: python scripts/seed_ipl2026_fixtures.py [local|prod]")
        sys.exit(1)

    print(f"Mode: {mode}")
    run(mode)
