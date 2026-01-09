#!/usr/bin/env python3
"""
Seed script for Fantasy Cricket League database.

This script reads initial_data.json and populates the database with:
- 1 Tournament (World Cup 2025)
- 2 Teams with ~15 players each
- 1 Upcoming Match

Usage:
    python seed.py [--reset]

Options:
    --reset    Drop all tables and recreate them before seeding
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.database import engine, SessionLocal
from app.models import (
    Base,
    Tournament,
    Team,
    Player,
    Match,
    MatchStatus,
)


def load_initial_data() -> dict:
    """Load seed data from initial_data.json."""
    data_file = Path(__file__).parent / "initial_data.json"
    if not data_file.exists():
        print(f"Error: {data_file} not found!")
        sys.exit(1)

    with open(data_file, "r") as f:
        return json.load(f)


def reset_database():
    """Drop all tables and recreate them."""
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database reset complete!")


def create_tables():
    """Create tables if they don't exist."""
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created!")


def seed_database():
    """Seed the database with initial data."""
    data = load_initial_data()
    db = SessionLocal()

    try:
        # Check if data already exists
        existing_tournament = db.query(Tournament).first()
        if existing_tournament:
            print("Database already contains data. Use --reset to clear and reseed.")
            return

        # Create Tournament
        print("Creating tournament...")
        tournament_data = data["tournament"]
        tournament = Tournament(
            name=tournament_data["name"],
            start_date=datetime.strptime(tournament_data["start_date"], "%Y-%m-%d").date(),
            end_date=datetime.strptime(tournament_data["end_date"], "%Y-%m-%d").date(),
        )
        db.add(tournament)
        db.flush()  # Get the tournament ID
        print(f"  Created: {tournament.name}")

        # Create Teams and Players
        print("Creating teams and players...")
        team_map = {}  # name -> Team object
        for team_data in data["teams"]:
            team = Team(
                name=team_data["name"],
                short_name=team_data["short_name"],
                logo_url=team_data.get("logo_url"),
            )
            db.add(team)
            db.flush()  # Get the team ID
            team_map[team.name] = team
            print(f"  Created team: {team.name} ({team.short_name})")

            # Create players for this team
            for player_data in team_data["players"]:
                player = Player(
                    name=player_data["name"],
                    team_id=team.id,
                    role=player_data["role"],
                )
                db.add(player)
            print(f"    Added {len(team_data['players'])} players")

        db.flush()

        # Create Matches
        print("Creating matches...")
        for match_data in data["matches"]:
            team_1 = team_map[match_data["team_1"]]
            team_2 = team_map[match_data["team_2"]]
            start_time = datetime.fromisoformat(match_data["start_time"].replace("Z", "+00:00"))

            match = Match(
                tournament_id=tournament.id,
                team_1_id=team_1.id,
                team_2_id=team_2.id,
                start_time=start_time,
                status=MatchStatus.SCHEDULED,
            )
            db.add(match)
            print(f"  Created match: {team_1.short_name} vs {team_2.short_name} at {start_time}")

        db.commit()
        print("\n✅ Database seeded successfully!")

        # Print summary
        print("\n📊 Summary:")
        print(f"  Tournaments: {db.query(Tournament).count()}")
        print(f"  Teams: {db.query(Team).count()}")
        print(f"  Players: {db.query(Player).count()}")
        print(f"  Matches: {db.query(Match).count()}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


def main():
    """Main entry point."""
    reset = "--reset" in sys.argv

    if reset:
        reset_database()
    else:
        create_tables()

    seed_database()


if __name__ == "__main__":
    main()
