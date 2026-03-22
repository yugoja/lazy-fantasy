#!/usr/bin/env python3
"""
Seed script for TATA IPL 2026.

Creates the tournament, 10 teams, and match fixtures.
Players can be added separately once squads are confirmed.

Usage:
    cd backend && source venv/bin/activate
    venv/bin/python seed_ipl2026.py          # add data
    venv/bin/python seed_ipl2026.py --reset  # wipe IPL 2026 data and reseed
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Tournament, Team, Match, MatchStatus

TOURNAMENT_NAME = "TATA IPL 2026"

TEAMS = [
    ("Chennai Super Kings",        "CSK"),
    ("Delhi Capitals",             "DC"),
    ("Gujarat Titans",             "GT"),
    ("Kolkata Knight Riders",      "KKR"),
    ("Lucknow Super Giants",       "LSG"),
    ("Mumbai Indians",             "MI"),
    ("Punjab Kings",               "PBKS"),
    ("Rajasthan Royals",           "RR"),
    ("Royal Challengers Bengaluru","RCB"),
    ("Sunrisers Hyderabad",        "SRH"),
]

# All times already in UTC (converted from IST in the official schedule)
MATCHES = [
    # (utc_timestamp,               home_code, away_code, venue)
    ("2026-03-28T14:00:00Z", "RCB",  "SRH",  "M. Chinnaswamy Stadium, Bengaluru"),
    ("2026-03-29T14:00:00Z", "MI",   "KKR",  "Wankhede Stadium, Mumbai"),
    ("2026-03-30T14:00:00Z", "RR",   "CSK",  "ACA Stadium, Guwahati"),
    ("2026-03-31T14:00:00Z", "PBKS", "GT",   "PCA International Cricket Stadium, New Chandigarh"),
    ("2026-04-01T14:00:00Z", "LSG",  "DC",   "BRSABV Ekana Cricket Stadium, Lucknow"),
    ("2026-04-02T14:00:00Z", "KKR",  "SRH",  "Eden Gardens, Kolkata"),
    ("2026-04-03T14:00:00Z", "CSK",  "PBKS", "MA Chidambaram Stadium, Chennai"),
    ("2026-04-04T10:00:00Z", "DC",   "MI",   "Arun Jaitley Stadium, Delhi"),
    ("2026-04-04T14:00:00Z", "GT",   "RR",   "Narendra Modi Stadium, Ahmedabad"),
    ("2026-04-05T10:00:00Z", "SRH",  "LSG",  "Rajiv Gandhi International Stadium, Hyderabad"),
    ("2026-04-05T14:00:00Z", "RCB",  "CSK",  "M. Chinnaswamy Stadium, Bengaluru"),
    ("2026-04-06T14:00:00Z", "KKR",  "PBKS", "Eden Gardens, Kolkata"),
    ("2026-04-07T14:00:00Z", "RR",   "MI",   "ACA Stadium, Guwahati"),
    ("2026-04-08T14:00:00Z", "DC",   "GT",   "Arun Jaitley Stadium, Delhi"),
    ("2026-04-09T14:00:00Z", "KKR",  "LSG",  "Eden Gardens, Kolkata"),
    ("2026-04-10T14:00:00Z", "RR",   "RCB",  "ACA Stadium, Guwahati"),
    ("2026-04-11T10:00:00Z", "PBKS", "SRH",  "PCA International Cricket Stadium, New Chandigarh"),
    ("2026-04-11T14:00:00Z", "CSK",  "DC",   "MA Chidambaram Stadium, Chennai"),
    ("2026-04-12T10:00:00Z", "LSG",  "GT",   "BRSABV Ekana Cricket Stadium, Lucknow"),
    ("2026-04-12T14:00:00Z", "MI",   "RCB",  "Wankhede Stadium, Mumbai"),
]


def reset_ipl2026(db):
    """Remove existing IPL 2026 tournament and all its matches."""
    t = db.query(Tournament).filter(Tournament.name == TOURNAMENT_NAME).first()
    if not t:
        return
    db.query(Match).filter(Match.tournament_id == t.id).delete()
    db.delete(t)
    db.commit()
    print(f"Cleared existing '{TOURNAMENT_NAME}' data.")


def seed(db):
    existing = db.query(Tournament).filter(Tournament.name == TOURNAMENT_NAME).first()
    if existing:
        print(f"'{TOURNAMENT_NAME}' already exists (id={existing.id}). Use --reset to reseed.")
        return

    # Tournament
    tournament = Tournament(
        name=TOURNAMENT_NAME,
        start_date=datetime(2026, 3, 28).date(),
        end_date=datetime(2026, 6, 1).date(),
        sport="cricket",
    )
    db.add(tournament)
    db.flush()
    print(f"Created tournament: {tournament.name} (id={tournament.id})")

    # Teams (upsert by short_name)
    team_map = {}
    for name, short in TEAMS:
        team = db.query(Team).filter(Team.short_name == short).first()
        if not team:
            team = Team(name=name, short_name=short, sport="cricket")
            db.add(team)
            db.flush()
            print(f"  Created team: {name} ({short})")
        else:
            print(f"  Reusing team: {name} ({short}, id={team.id})")
        team_map[short] = team

    # Matches
    print(f"\nCreating {len(MATCHES)} matches...")
    for ts, home_code, away_code, venue in MATCHES:
        start_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        match = Match(
            tournament_id=tournament.id,
            team_1_id=team_map[home_code].id,
            team_2_id=team_map[away_code].id,
            start_time=start_time,
            status=MatchStatus.SCHEDULED,
        )
        db.add(match)
        print(f"  {home_code} vs {away_code}  —  {start_time.strftime('%b %d %H:%M UTC')}")

    db.commit()
    print(f"\n✅ Seeded {len(MATCHES)} IPL 2026 matches.")
    print("   Next: add players per team via the admin API or a separate squad seed script.")


def main():
    db = SessionLocal()
    try:
        if "--reset" in sys.argv:
            reset_ipl2026(db)
        seed(db)
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
