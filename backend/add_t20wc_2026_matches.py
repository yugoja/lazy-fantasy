#!/usr/bin/env python3
"""
Additive seed script — ICC Men's T20 World Cup 2026 semi-finals.

Safe to run on production. Does NOT reset or delete any existing data.
Uses get-or-create for tournament, teams, players and matches.

Usage:
    python add_t20wc_2026_matches.py
"""

from datetime import datetime, timezone

from app.database import engine, SessionLocal
from app.models import Base, Tournament, Team, Player, Match, MatchStatus

TOURNAMENT_NAME = "ICC Men's T20 World Cup 2026"

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


def get_or_create_tournament(db) -> Tournament:
    t = db.query(Tournament).filter_by(name=TOURNAMENT_NAME).first()
    if t:
        print(f"  Tournament already exists: {t.name} (id={t.id})")
        return t
    t = Tournament(
        name=TOURNAMENT_NAME,
        start_date=datetime(2026, 2, 7).date(),
        end_date=datetime(2026, 3, 8).date(),
    )
    db.add(t)
    db.flush()
    print(f"  Created tournament: {t.name} (id={t.id})")
    return t


def get_or_create_team(db, name: str, short_name: str) -> Team:
    team = db.query(Team).filter_by(short_name=short_name).first()
    if team:
        print(f"    Team exists: {name} (id={team.id})")
        return team
    team = Team(name=name, short_name=short_name)
    db.add(team)
    db.flush()
    print(f"    Created team: {name} (id={team.id})")
    return team


def ensure_players(db, team: Team, players: list[tuple[str, str]]) -> int:
    existing_names = {p.name for p in db.query(Player).filter_by(team_id=team.id).all()}
    added = 0
    for name, role in players:
        if name not in existing_names:
            db.add(Player(name=name, team_id=team.id, role=role))
            added += 1
    if added:
        db.flush()
    return added


def get_or_create_match(db, tournament_id: int, team_1_id: int, team_2_id: int, start_time: datetime) -> tuple[Match, bool]:
    # Normalise to UTC naive for comparison (SQLite stores without tz)
    start_naive = start_time.replace(tzinfo=None)
    existing = (
        db.query(Match)
        .filter_by(tournament_id=tournament_id, team_1_id=team_1_id, team_2_id=team_2_id)
        .first()
    )
    if existing:
        return existing, False
    match = Match(
        tournament_id=tournament_id,
        team_1_id=team_1_id,
        team_2_id=team_2_id,
        start_time=start_naive,
        status=MatchStatus.SCHEDULED,
    )
    db.add(match)
    db.flush()
    return match, True


def main():
    print("Creating tables if missing...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("\n[Tournament]")
        tournament = get_or_create_tournament(db)

        print("\n[Teams & Players]")
        team_map = {}
        for name, data in TEAMS.items():
            team = get_or_create_team(db, name, data["short_name"])
            added = ensure_players(db, team, data["players"])
            print(f"      Players: {added} added, {len(data['players']) - added} already existed")
            team_map[name] = team

        print("\n[Matches]")
        for m in MATCHES:
            t1 = team_map[m["team_1"]]
            t2 = team_map[m["team_2"]]
            match, created = get_or_create_match(db, tournament.id, t1.id, t2.id, m["start_time"])
            status = "Created" if created else "Already exists"
            print(f"  {status}: {m['label']} — {m['team_1']} vs {m['team_2']} @ {m['start_time'].strftime('%b %d %H:%M UTC')}")

        db.commit()
        print("\n✅ Done — no existing data was modified.")
        print(f"  Total teams: {db.query(Team).count()}")
        print(f"  Total matches: {db.query(Match).count()}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
