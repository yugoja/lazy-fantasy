"""
Seed realistic dev data for local testing.

Creates (idempotently):
  - 10 fake users  (username: seed_user_0..9, password: devpass)
  - 3 cricket leagues with overlapping membership
  - 1 dev cricket tournament + minimal teams/players
  - 5 completed past matches with results and scored predictions
  - 3 upcoming scheduled matches with predictions (unprocessed)

--with-history also creates:
  - 1 football mini-tournament (4 teams, WC-style)
  - 3 GROUP matchdays (6 matches) + 1 QF — all completed and scored
  - 1 upcoming SF match
  - A "WC Dev League" with all seed users
  - Football predictions + player picks + results → full leaderboard with round filter data

Safe to re-run — existing seed rows are detected and skipped.

Usage (from backend/):
  python -m scripts.seed_dev
  python -m scripts.seed_dev --with-history
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
# Football history seed
# ---------------------------------------------------------------------------

WC_TOURNAMENT_NAME = "Dev WC 2026 Mini"
WC_LEAGUE_NAME = "WC Dev League"

_WC_TEAMS = [
    ("Brazil",    "BRA", "Forward"),
    ("France",    "FRA", "Forward"),
    ("Argentina", "ARG", "Forward"),
    ("England",   "ENG", "Forward"),
]

# (team1_idx, team2_idx, group_round, result_1, result_2)
# result_X = goals scored by that team in regulation
_GROUP_FIXTURES = [
    # Matchday 1
    (0, 1, 1, 2, 1),  # Brazil 2-1 France
    (2, 3, 1, 0, 0),  # Argentina 0-0 England
    # Matchday 2
    (0, 2, 2, 3, 2),  # Brazil 3-2 Argentina
    (1, 3, 2, 1, 1),  # France 1-1 England
    # Matchday 3
    (0, 3, 3, 1, 0),  # Brazil 1-0 England
    (1, 2, 3, 2, 0),  # France 2-0 Argentina
]

# QF: Brazil vs France (Brazil wins 2-1)
_QF_FIXTURE = (0, 1, 2, 1)  # team1_idx, team2_idx, goals1, goals2


def _ensure_football_teams(db: Session) -> list[Team]:
    teams = []
    for name, short, _ in _WC_TEAMS:
        t = db.query(Team).filter(Team.name == name, Team.sport == "football").first()
        if not t:
            t = Team(name=name, short_name=short, sport="football")
            db.add(t)
            db.flush()
        teams.append(t)
    return teams


def _ensure_football_players(db: Session, teams: list[Team]) -> dict[int, list[Player]]:
    """1 GK, 2 DEF, 2 MID, 2 FWD per team — roles match Position enum values."""
    roles = ["Goalkeeper", "Defender", "Defender", "Midfielder", "Midfielder", "Forward", "Forward"]
    result: dict[int, list[Player]] = {}
    for team in teams:
        existing = db.query(Player).filter(Player.team_id == team.id).all()
        if existing:
            result[team.id] = existing
            continue
        created = []
        for role in roles:
            p = Player(name=fake.name(), team_id=team.id, role=role, sport="football")
            db.add(p)
            created.append(p)
        db.flush()
        result[team.id] = created
    return result


def _players_by_role(players: list[Player]) -> dict[str, list[Player]]:
    d: dict[str, list[Player]] = {}
    for p in players:
        d.setdefault(p.role, []).append(p)
    return d


def _seed_football_match_result(
    db: Session,
    match: Match,
    goals1: int,
    goals2: int,
    t1_players: list[Player],
    t2_players: list[Player],
) -> None:
    from app.models.football_match_result import FootballMatchResult, FootballPlayerMatchEvent

    if db.query(FootballMatchResult).filter(FootballMatchResult.match_id == match.id).first():
        return

    result = FootballMatchResult(
        match_id=match.id,
        team1_goals_reg=goals1,
        team2_goals_reg=goals2,
    )
    db.add(result)
    db.flush()

    # Give each player minimal events so scoring has something to work with
    team1_conceded = goals2
    team2_conceded = goals1
    all_sides = [(t1_players, team1_conceded), (t2_players, team2_conceded)]
    for players, conceded in all_sides:
        for p in players:
            goals = 1 if p.role == "Forward" and random.random() < 0.4 else 0
            assists = 1 if p.role == "Midfielder" and random.random() < 0.3 else 0
            db.add(FootballPlayerMatchEvent(
                match_id=match.id,
                player_id=p.id,
                minutes_played=90,
                goals=goals,
                assists=assists,
                team_goals_conceded=conceded,
            ))
    db.flush()


def _seed_football_prediction(
    db: Session,
    user: User,
    match: Match,
    t1: Team,
    t2: Team,
    actual_goals1: int,
    actual_goals2: int,
    t1_players: list[Player],
    t2_players: list[Player],
    accurate: bool,
) -> None:
    from app.models.football_prediction import FootballPrediction

    if db.query(Prediction).filter(
        Prediction.user_id == user.id, Prediction.match_id == match.id
    ).first():
        return

    if accurate:
        pg1, pg2 = actual_goals1, actual_goals2
    else:
        pg1 = max(0, actual_goals1 + random.choice([-1, 1]))
        pg2 = max(0, actual_goals2 + random.choice([-1, 1]))

    # Pick 3 players (one from each position tier)
    by_role_t1 = _players_by_role(t1_players)
    by_role_t2 = _players_by_role(t2_players)
    pick1 = random.choice(by_role_t1.get("Forward", t1_players))
    pick2 = random.choice(by_role_t2.get("Midfielder", t2_players) or t2_players)
    pick3 = random.choice(by_role_t1.get("Defender", t1_players) or t1_players)

    pred = Prediction(user_id=user.id, match_id=match.id)
    db.add(pred)
    db.flush()

    fp = FootballPrediction(
        prediction_id=pred.id,
        team1_goals=pg1,
        team2_goals=pg2,
        player_pick_1_id=pick1.id,
        player_pick_2_id=pick2.id,
        player_pick_3_id=pick3.id,
    )
    db.add(fp)
    db.flush()


def seed_football_history(db: Session, users: list[User]) -> None:
    # --- Tournament ---
    tournament = db.query(Tournament).filter(Tournament.name == WC_TOURNAMENT_NAME).first()
    if not tournament:
        tournament = Tournament(
            name=WC_TOURNAMENT_NAME,
            start_date=datetime(2026, 5, 1).date(),
            end_date=datetime(2026, 6, 30).date(),
            sport="football",
            picks_window="closed",
        )
        db.add(tournament)
        db.flush()

    teams = _ensure_football_teams(db)
    players_by_team = _ensure_football_players(db, teams)

    now = datetime.now(timezone.utc)
    # League was created 40 days ago; all matches fall after that so the
    # leaderboard query (Match.start_time >= league.created_at) includes them.
    league_created_at = now - timedelta(days=40)
    base_time = league_created_at + timedelta(days=1)  # first match 39 days ago

    # --- League ---
    league = db.query(League).filter(League.name == WC_LEAGUE_NAME).first()
    if not league:
        league = League(
            name=WC_LEAGUE_NAME,
            invite_code=_random_invite_code(db),
            owner_id=users[0].id,
            sport="football",
            created_at=league_created_at,
        )
        db.add(league)
        db.flush()

    existing_members = {m.user_id for m in db.query(LeagueMember).filter(LeagueMember.league_id == league.id).all()}
    for u in users:
        if u.id not in existing_members:
            db.add(LeagueMember(league_id=league.id, user_id=u.id))
    db.flush()

    # --- Group stage matches ---
    completed_matches = []
    for i, (t1_idx, t2_idx, group_round, goals1, goals2) in enumerate(_GROUP_FIXTURES):
        ext_id = f"wc_seed_group_{i}"
        match = db.query(Match).filter(Match.external_match_id == ext_id).first()
        if not match:
            match = Match(
                tournament_id=tournament.id,
                team_1_id=teams[t1_idx].id,
                team_2_id=teams[t2_idx].id,
                start_time=base_time + timedelta(days=i * 4),
                status=MatchStatus.COMPLETED,
                stage="GROUP",
                group_round=group_round,
                external_match_id=ext_id,
                sync_state="result_synced",
            )
            db.add(match)
            db.flush()

            _seed_football_match_result(
                db, match, goals1, goals2,
                players_by_team[teams[t1_idx].id],
                players_by_team[teams[t2_idx].id],
            )

        completed_matches.append((match, teams[t1_idx], teams[t2_idx], goals1, goals2))

    # --- QF ---
    t1_idx, t2_idx, goals1, goals2 = _QF_FIXTURE
    ext_id = "wc_seed_qf"
    qf_match = db.query(Match).filter(Match.external_match_id == ext_id).first()
    if not qf_match:
        qf_match = Match(
            tournament_id=tournament.id,
            team_1_id=teams[t1_idx].id,
            team_2_id=teams[t2_idx].id,
            start_time=base_time + timedelta(days=28),
            status=MatchStatus.COMPLETED,
            stage="QF",
            external_match_id=ext_id,
            sync_state="result_synced",
        )
        db.add(qf_match)
        db.flush()
        _seed_football_match_result(
            db, qf_match, goals1, goals2,
            players_by_team[teams[t1_idx].id],
            players_by_team[teams[t2_idx].id],
        )
    completed_matches.append((qf_match, teams[t1_idx], teams[t2_idx], goals1, goals2))

    # --- Upcoming SF ---
    ext_id = "wc_seed_sf"
    if not db.query(Match).filter(Match.external_match_id == ext_id).first():
        sf = Match(
            tournament_id=tournament.id,
            team_1_id=teams[0].id,
            team_2_id=teams[2].id,
            start_time=datetime.now(timezone.utc) + timedelta(days=3),
            status=MatchStatus.SCHEDULED,
            stage="SF",
            external_match_id=ext_id,
            sync_state="unlinked",
        )
        db.add(sf)
        db.flush()

    # --- Predictions for completed matches ---
    for idx, (match, t1, t2, goals1, goals2) in enumerate(completed_matches):
        t1_players = players_by_team[t1.id]
        t2_players = players_by_team[t2.id]
        for u_idx, user in enumerate(users):
            # Vary accuracy: first 3 users are good, last 3 are bad, rest middling
            accurate = random.random() < (0.7 if u_idx < 3 else 0.3 if u_idx >= 7 else 0.5)
            _seed_football_prediction(
                db, user, match, t1, t2, goals1, goals2,
                t1_players, t2_players, accurate,
            )
        db.flush()
        calculate_scores(db, match.id)

    n_group = len(_GROUP_FIXTURES)
    print(f"  football: {n_group} GROUP matches + 1 QF (completed+scored) + 1 SF upcoming")
    print(f"  league:   '{WC_LEAGUE_NAME}' with all {len(users)} seed users")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(with_history: bool = False) -> None:
    db: Session = SessionLocal()
    try:
        print("Seeding dev data...")

        users = seed_users(db)
        seed_leagues(db, users)

        tournament = _ensure_tournament(db)
        teams = _ensure_teams(db)
        players_by_team = _ensure_players(db, teams)
        seed_matches(db, tournament, teams, players_by_team, users)

        if with_history:
            print("Seeding football history...")
            seed_football_history(db, users)

        db.commit()
        print("Done. Login with any seed_user_0..9 / devpass")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-history", action="store_true", help="Seed completed football WC history for UI testing")
    args = parser.parse_args()
    run(with_history=args.with_history)
