#!/usr/bin/env python3
"""
Seed script for ICC Men's T20 World Cup 2026.
Seeds the 4 semifinalists + SF1 (SA vs NZ) + SF2 (India vs England).

Usage:
    python seed_t20wc_2026.py [--reset]
"""

import sys
from datetime import datetime, timezone

from app.database import engine, SessionLocal
from app.models import Base, Tournament, Team, Player, Match, MatchStatus

TEAMS = {
    "India": {
        "short_name": "IND",
        "players": [
            ("Rohit Sharma", "batsman"),
            ("Yashasvi Jaiswal", "batsman"),
            ("Virat Kohli", "batsman"),
            ("Suryakumar Yadav", "batsman"),
            ("Tilak Varma", "batsman"),
            ("Rishabh Pant", "wicket_keeper"),
            ("KL Rahul", "wicket_keeper"),
            ("Hardik Pandya", "all_rounder"),
            ("Ravindra Jadeja", "all_rounder"),
            ("Axar Patel", "all_rounder"),
            ("Shivam Dube", "all_rounder"),
            ("Jasprit Bumrah", "bowler"),
            ("Arshdeep Singh", "bowler"),
            ("Mohammed Siraj", "bowler"),
            ("Kuldeep Yadav", "bowler"),
        ],
    },
    "England": {
        "short_name": "ENG",
        "players": [
            ("Jos Buttler", "wicket_keeper"),
            ("Phil Salt", "wicket_keeper"),
            ("Ben Duckett", "batsman"),
            ("Harry Brook", "batsman"),
            ("Joe Root", "batsman"),
            ("Dawid Malan", "batsman"),
            ("Liam Livingstone", "all_rounder"),
            ("Sam Curran", "all_rounder"),
            ("Chris Woakes", "all_rounder"),
            ("Moeen Ali", "all_rounder"),
            ("Jofra Archer", "bowler"),
            ("Mark Wood", "bowler"),
            ("Adil Rashid", "bowler"),
            ("Rehan Ahmed", "bowler"),
            ("Gus Atkinson", "bowler"),
        ],
    },
    "South Africa": {
        "short_name": "SA",
        "players": [
            ("Temba Bavuma", "batsman"),
            ("Reeza Hendricks", "batsman"),
            ("Rassie van der Dussen", "batsman"),
            ("David Miller", "batsman"),
            ("Tristan Stubbs", "batsman"),
            ("Ryan Rickelton", "batsman"),
            ("Heinrich Klaasen", "wicket_keeper"),
            ("Quinton de Kock", "wicket_keeper"),
            ("Marco Jansen", "all_rounder"),
            ("Wiaan Mulder", "all_rounder"),
            ("Keshav Maharaj", "bowler"),
            ("Tabraiz Shamsi", "bowler"),
            ("Kagiso Rabada", "bowler"),
            ("Lungi Ngidi", "bowler"),
            ("Anrich Nortje", "bowler"),
        ],
    },
    "New Zealand": {
        "short_name": "NZ",
        "players": [
            ("Kane Williamson", "batsman"),
            ("Finn Allen", "batsman"),
            ("Daryl Mitchell", "all_rounder"),
            ("Glenn Phillips", "batsman"),
            ("Mark Chapman", "batsman"),
            ("Devon Conway", "wicket_keeper"),
            ("Tom Latham", "wicket_keeper"),
            ("Mitchell Santner", "all_rounder"),
            ("Rachin Ravindra", "all_rounder"),
            ("James Neesham", "all_rounder"),
            ("Michael Bracewell", "all_rounder"),
            ("Trent Boult", "bowler"),
            ("Tim Southee", "bowler"),
            ("Lockie Ferguson", "bowler"),
            ("Matt Henry", "bowler"),
        ],
    },
}

# IST 19:00 = UTC 13:30
MATCHES = [
    {
        "label": "1st Semi-Final",
        "team_1": "South Africa",
        "team_2": "New Zealand",
        "start_time": datetime(2026, 3, 4, 13, 30, tzinfo=timezone.utc),
    },
    {
        "label": "2nd Semi-Final",
        "team_1": "India",
        "team_2": "England",
        "start_time": datetime(2026, 3, 5, 13, 30, tzinfo=timezone.utc),
    },
]


def main():
    reset = "--reset" in sys.argv

    if reset:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Tournament).first():
            print("Data already exists. Use --reset to wipe and reseed.")
            return

        # Tournament
        tournament = Tournament(
            name="ICC Men's T20 World Cup 2026",
            start_date=datetime(2026, 2, 7).date(),
            end_date=datetime(2026, 3, 8).date(),
        )
        db.add(tournament)
        db.flush()
        print(f"Created tournament: {tournament.name}")

        # Teams + Players
        team_map = {}
        for name, data in TEAMS.items():
            team = Team(name=name, short_name=data["short_name"])
            db.add(team)
            db.flush()
            team_map[name] = team
            for player_name, role in data["players"]:
                db.add(Player(name=player_name, team_id=team.id, role=role))
            print(f"  {name} ({data['short_name']}) — {len(data['players'])} players")

        db.flush()

        # Matches
        for m in MATCHES:
            match = Match(
                tournament_id=tournament.id,
                team_1_id=team_map[m["team_1"]].id,
                team_2_id=team_map[m["team_2"]].id,
                start_time=m["start_time"],
                status=MatchStatus.SCHEDULED,
            )
            db.add(match)
            print(f"  {m['label']}: {m['team_1']} vs {m['team_2']} @ {m['start_time'].strftime('%b %d %H:%M UTC')}")

        db.commit()
        print("\n✅ Seeded successfully!")
        print(f"  Teams: {db.query(Team).count()}")
        print(f"  Players: {db.query(Player).count()}")
        print(f"  Matches: {db.query(Match).count()}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
