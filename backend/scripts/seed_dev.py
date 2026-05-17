"""
Seed realistic dev data for local testing.

Creates (idempotently):
  - 10 fake users  (username: seed_user_0..9, password: devpass)
  - 3 leagues with overlapping membership
  - 1 dev tournament (if no tournaments exist) + minimal teams/players
  - 5 completed past matches with results and scored predictions
  - 3 upcoming scheduled matches with predictions (unprocessed)

Safe to re-run — existing seed rows are detected and skipped.

Usage (from backend/):
  python -m scripts.seed_dev
  # or
  python scripts/seed_dev.py
"""
import os
import sys
import random
import string
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.league import League, LeagueMember
from app.models.team import Team
from app.models.player import Player
from app.models.match import Match, MatchStatus
from app.models.tournament import Tournament
from app.models.prediction import Prediction
from app.services.auth import get_password_hash
from app.services.scoring import calculate_scores

fake = Faker("en_IN")
random.seed(42)

SEED_USER_PREFIX = "seed_user_"
SEED_LEAGUE_PREFIX = "Dev League "
SEED_MATCH_PREFIX = "seed_match_"
DEV_PASSWORD = "devpass"
NUM_USERS = 10
PAST_MATCHES = 5
FUTURE_MATCHES = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_invite_code(db: Session) -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not db.query(League).filter(League.invite_code == code).first():
            return code


def _ensure_tournament(db: Session) -> Tournament:
    t = db.query(Tournament).first()
    if t:
        return t
    t = Tournament(
        name="Dev IPL 2026",
        start_date=datetime(2026, 3, 22).date(),
        end_date=datetime(2026, 5, 25).date(),
        sport="cricket",
        picks_window="closed",
    )
    db.add(t)
    db.flush()
    return t


def _ensure_teams(db: Session) -> list[Team]:
    teams = db.query(Team).filter(Team.sport == "cricket").all()
    if teams:
        return teams

    ipl_teams = [
        ("Mumbai Indians", "MI"),
        ("Chennai Super Kings", "CSK"),
        ("Royal Challengers Bengaluru", "RCB"),
        ("Kolkata Knight Riders", "KKR"),
        ("Delhi Capitals", "DC"),
        ("Punjab Kings", "PBKS"),
        ("Rajasthan Royals", "RR"),
        ("Sunrisers Hyderabad", "SRH"),
        ("Gujarat Titans", "GT"),
        ("Lucknow Super Giants", "LSG"),
    ]
    created = []
    for name, short in ipl_teams:
        t = Team(name=name, short_name=short, sport="cricket")
        db.add(t)
        created.append(t)
    db.flush()
    return created


def _ensure_players(db: Session, teams: list[Team]) -> dict[int, list[Player]]:
    """Return {team_id: [players]}; creates 6 players per team if none exist."""
    result: dict[int, list[Player]] = {}
    for team in teams:
        existing = db.query(Player).filter(Player.team_id == team.id).all()
        if existing:
            result[team.id] = existing
            continue
        roles = ["Batsman"] * 3 + ["Bowler"] * 2 + ["All-Rounder"]
        created = []
        for role in roles:
            p = Player(name=fake.name(), team_id=team.id, role=role)
            db.add(p)
            created.append(p)
        db.flush()
        result[team.id] = created
    return result


def _random_player(players: list[Player], role_filter: str | None = None) -> Player:
    pool = [p for p in players if role_filter is None or p.role == role_filter] or players
    return random.choice(pool)


# ---------------------------------------------------------------------------
# Core seed functions
# ---------------------------------------------------------------------------

def seed_users(db: Session) -> list[User]:
    users = []
    for i in range(NUM_USERS):
        username = f"{SEED_USER_PREFIX}{i}"
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            users.append(existing)
            continue
        u = User(
            username=username,
            email=f"seed_user_{i}@dev.lazyfantasy.test",
            hashed_password=get_password_hash(DEV_PASSWORD),
            display_name=fake.name(),
            is_admin=False,
        )
        db.add(u)
        db.flush()
        users.append(u)
    print(f"  users: {NUM_USERS} ensured ({SEED_USER_PREFIX}0..{NUM_USERS - 1} / pw: {DEV_PASSWORD})")
    return users


def seed_leagues(db: Session, users: list[User]) -> list[League]:
    configs = [
        (f"{SEED_LEAGUE_PREFIX}A", users[:6]),
        (f"{SEED_LEAGUE_PREFIX}B", users[3:9]),
        (f"{SEED_LEAGUE_PREFIX}C", users[7:]),
    ]
    leagues = []
    for name, members in configs:
        league = db.query(League).filter(League.name == name).first()
        if not league:
            league = League(
                name=name,
                invite_code=_random_invite_code(db),
                owner_id=members[0].id,
                sport="cricket",
            )
            db.add(league)
            db.flush()

        existing_member_ids = {
            m.user_id for m in db.query(LeagueMember).filter(LeagueMember.league_id == league.id).all()
        }
        for user in members:
            if user.id not in existing_member_ids:
                db.add(LeagueMember(league_id=league.id, user_id=user.id))
        db.flush()
        leagues.append(league)

    print(f"  leagues: 3 ensured (A: users 0-5, B: users 3-8, C: users 7-9)")
    return leagues


def seed_matches(
    db: Session,
    tournament: Tournament,
    teams: list[Team],
    players_by_team: dict[int, list[Player]],
    users: list[User],
) -> None:
    now = datetime.now(timezone.utc)

    # --- COMPLETED past matches ---
    for i in range(PAST_MATCHES):
        ext_id = f"{SEED_MATCH_PREFIX}past_{i}"
        if db.query(Match).filter(Match.external_match_id == ext_id).first():
            continue

        t1, t2 = teams[i % len(teams)], teams[(i + 1) % len(teams)]
        t1_players = players_by_team[t1.id]
        t2_players = players_by_team[t2.id]
        winner = random.choice([t1, t2])
        all_players = t1_players + t2_players
        pom = _random_player(all_players)

        match = Match(
            tournament_id=tournament.id,
            team_1_id=t1.id,
            team_2_id=t2.id,
            start_time=now - timedelta(days=PAST_MATCHES - i, hours=14),
            status=MatchStatus.COMPLETED,
            external_match_id=ext_id,
            sync_state="result_synced",
            result_winner_id=winner.id,
            result_most_runs_team1_player_id=_random_player(t1_players, "Batsman").id,
            result_most_runs_team2_player_id=_random_player(t2_players, "Batsman").id,
            result_most_wickets_team1_player_id=_random_player(t1_players, "Bowler").id,
            result_most_wickets_team2_player_id=_random_player(t2_players, "Bowler").id,
            result_pom_player_id=pom.id,
        )
        db.add(match)
        db.flush()

        # Predictions for every seed user
        for user in users:
            # Vary accuracy: first 5 users are 60% accurate, rest 40%
            accurate = random.random() < (0.6 if user.id % 2 == 0 else 0.4)
            pred = Prediction(
                user_id=user.id,
                match_id=match.id,
                predicted_winner_id=winner.id if accurate else (t2.id if winner == t1 else t1.id),
                predicted_most_runs_team1_player_id=(
                    match.result_most_runs_team1_player_id if accurate
                    else _random_player(t1_players, "Batsman").id
                ),
                predicted_most_runs_team2_player_id=(
                    match.result_most_runs_team2_player_id if accurate
                    else _random_player(t2_players, "Batsman").id
                ),
                predicted_most_wickets_team1_player_id=(
                    match.result_most_wickets_team1_player_id if accurate
                    else _random_player(t1_players, "Bowler").id
                ),
                predicted_most_wickets_team2_player_id=(
                    match.result_most_wickets_team2_player_id if accurate
                    else _random_player(t2_players, "Bowler").id
                ),
                predicted_pom_player_id=(
                    pom.id if accurate else _random_player(all_players).id
                ),
            )
            db.add(pred)
        db.flush()

        # Score all predictions for this match
        calculate_scores(db, match.id)

    # --- SCHEDULED future matches ---
    for i in range(FUTURE_MATCHES):
        ext_id = f"{SEED_MATCH_PREFIX}future_{i}"
        if db.query(Match).filter(Match.external_match_id == ext_id).first():
            continue

        t1 = teams[(PAST_MATCHES + i) % len(teams)]
        t2 = teams[(PAST_MATCHES + i + 1) % len(teams)]
        t1_players = players_by_team[t1.id]
        t2_players = players_by_team[t2.id]

        match = Match(
            tournament_id=tournament.id,
            team_1_id=t1.id,
            team_2_id=t2.id,
            start_time=now + timedelta(days=i + 1, hours=14),
            status=MatchStatus.SCHEDULED,
            external_match_id=ext_id,
            sync_state="unlinked",
        )
        db.add(match)
        db.flush()

        # Half the users have made predictions on upcoming matches
        for user in users[:NUM_USERS // 2]:
            all_players = t1_players + t2_players
            db.add(Prediction(
                user_id=user.id,
                match_id=match.id,
                predicted_winner_id=random.choice([t1, t2]).id,
                predicted_most_runs_team1_player_id=_random_player(t1_players, "Batsman").id,
                predicted_most_runs_team2_player_id=_random_player(t2_players, "Batsman").id,
                predicted_most_wickets_team1_player_id=_random_player(t1_players, "Bowler").id,
                predicted_most_wickets_team2_player_id=_random_player(t2_players, "Bowler").id,
                predicted_pom_player_id=_random_player(all_players).id,
            ))
        db.flush()

    print(f"  matches: {PAST_MATCHES} completed (with scored predictions) + {FUTURE_MATCHES} upcoming")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    db: Session = SessionLocal()
    try:
        print("Seeding dev data...")

        users = seed_users(db)
        seed_leagues(db, users)

        tournament = _ensure_tournament(db)
        teams = _ensure_teams(db)
        players_by_team = _ensure_players(db, teams)
        seed_matches(db, tournament, teams, players_by_team, users)

        db.commit()
        print("Done. Login with any seed_user_0..9 / devpass")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
