#!/usr/bin/env python3
"""
Seed mock users and leagues for local testing.

Usage:
    cd backend && source venv/bin/activate
    venv/bin/python seed_mock_data.py          # add data
    venv/bin/python seed_mock_data.py --reset  # wipe mock data and reseed
"""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import User
from app.models.league import League, LeagueMember
from app.services.auth import get_password_hash

# All mock users (password is "password123" for everyone)
MOCK_USERS = [
    ("rohit_sharma",   "rohit@test.com"),
    ("virat_kohli",    "virat@test.com"),
    ("ms_dhoni",       "dhoni@test.com"),
    ("jasprit_bumrah", "bumrah@test.com"),
    ("hardik_pandya",  "hardik@test.com"),
    ("rishabh_pant",   "pant@test.com"),
    ("shubman_gill",   "gill@test.com"),
    ("shreyas_iyer",   "shreyas@test.com"),
]

MOCK_LEAGUES = [
    # (name, invite_code, owner_username, member_usernames)
    (
        "Office Fantasy XI",
        "OFC001",
        "rohit_sharma",
        ["virat_kohli", "ms_dhoni", "jasprit_bumrah", "hardik_pandya"],
    ),
    (
        "Friends & Rivals",
        "FRD002",
        "virat_kohli",
        ["rohit_sharma", "rishabh_pant", "shubman_gill", "shreyas_iyer", "ms_dhoni"],
    ),
]


def reset_mock(db):
    for code in [l[1] for l in MOCK_LEAGUES]:
        league = db.query(League).filter(League.invite_code == code).first()
        if league:
            db.query(LeagueMember).filter(LeagueMember.league_id == league.id).delete()
            db.delete(league)
    for _, email in MOCK_USERS:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
    db.commit()
    print("Cleared mock data.")


def seed(db):
    password_hash = get_password_hash("password123")

    # Upsert users
    user_map = {}
    for username, email in MOCK_USERS:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(username=username, email=email, hashed_password=password_hash)
            db.add(user)
            db.flush()
            print(f"  Created user: {username}")
        else:
            print(f"  Reusing user: {username} (id={user.id})")
        user_map[username] = user

    # Create leagues
    for name, code, owner_username, member_usernames in MOCK_LEAGUES:
        if db.query(League).filter(League.invite_code == code).first():
            print(f"  League '{name}' already exists, skipping.")
            continue

        owner = user_map[owner_username]
        league = League(name=name, invite_code=code, owner_id=owner.id, sport="cricket")
        db.add(league)
        db.flush()

        # Add owner as member
        db.add(LeagueMember(league_id=league.id, user_id=owner.id))

        # Add other members
        for username in member_usernames:
            member = user_map.get(username)
            if member:
                db.add(LeagueMember(league_id=league.id, user_id=member.id))

        member_count = 1 + len(member_usernames)
        print(f"  Created league: '{name}' ({code}) — {member_count} members")

    db.commit()
    print("\n✅ Mock data seeded. Login with any test user, password: password123")
    print("   e.g. rohit@test.com / password123")


def main():
    db = SessionLocal()
    try:
        if "--reset" in sys.argv:
            reset_mock(db)
        seed(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
