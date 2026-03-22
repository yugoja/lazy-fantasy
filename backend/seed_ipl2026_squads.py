#!/usr/bin/env python3
"""
Seed script for IPL 2026 player squads.

Reads from ipl2026_squads.json and upserts players into the DB,
linked to the teams already created by seed_ipl2026.py.

Usage:
    cd backend && source venv/bin/activate
    venv/bin/python seed_ipl2026_squads.py [/path/to/ipl2026_squads.json]
    venv/bin/python seed_ipl2026_squads.py --reset  # delete all players for IPL 2026 teams and reseed
"""
import json
import os
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Team
from app.models.player import Player

DEFAULT_JSON = os.path.join(os.path.dirname(__file__), "data", "ipl2026_squads.json")

# Map JSON roles → DB roles
ROLE_MAP = {
    "Batter":      "Batsman",
    "WK-Batter":   "Wicketkeeper",
    "All-Rounder": "All-Rounder",
    "Bowler":      "Bowler",
}

# JSON team_id codes that belong to IPL 2026 teams
IPL_TEAM_CODES = {"CSK", "DC", "GT", "KKR", "LSG", "MI", "PBKS", "RR", "RCB", "SRH"}


def reset_squads(db, team_map: dict):
    """Delete all players for IPL 2026 teams."""
    total = 0
    for team in team_map.values():
        deleted = db.query(Player).filter(Player.team_id == team.id).delete()
        total += deleted
    db.commit()
    print(f"Deleted {total} players from IPL 2026 teams.")


def seed_squads(db, squads_json: str):
    with open(squads_json) as f:
        data = json.load(f)

    # Build team_code → Team map
    team_map = {}
    for code in IPL_TEAM_CODES:
        team = db.query(Team).filter(Team.short_name == code).first()
        if not team:
            print(f"  WARNING: team '{code}' not found in DB — run seed_ipl2026.py first.")
        else:
            team_map[code] = team

    if not team_map:
        print("No IPL 2026 teams found. Run seed_ipl2026.py first.")
        return

    if "--reset" in sys.argv:
        reset_squads(db, team_map)

    total_added = total_skipped = 0

    for team_entry in data["teams"]:
        code = team_entry["team_id"]
        if code not in team_map:
            print(f"  Skipping unknown team: {code}")
            continue

        team = team_map[code]
        added = skipped = 0

        for player_data in team_entry["squad"]:
            name = player_data["name"]
            role = ROLE_MAP.get(player_data["role"], player_data["role"])

            existing = db.query(Player).filter(
                Player.team_id == team.id,
                Player.name == name,
            ).first()

            if existing:
                skipped += 1
            else:
                db.add(Player(name=name, team_id=team.id, role=role))
                added += 1

        db.flush()
        total_added += added
        total_skipped += skipped
        print(f"  {code:4s}  added={added:2d}  skipped={skipped:2d}  "
              f"({team_entry['team_name']})")

    db.commit()
    print(f"\n✅ Done. Added {total_added} players, skipped {total_skipped} already present.")


def main():
    json_path = DEFAULT_JSON
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            json_path = arg
            break

    db = SessionLocal()
    try:
        seed_squads(db, json_path)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
