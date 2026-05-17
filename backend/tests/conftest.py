"""
Pytest configuration and shared fixtures for testing the Fantasy Cricket League API.

DB strategy:
  - If TEST_DATABASE_URL is set (CI / explicit local Postgres), connect directly.
  - Otherwise spin up a postgres:16 container via testcontainers (requires Docker).

Isolation: one engine per session, transaction rollback per test — no
schema drop/recreate between tests.
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.tournament import Tournament
from app.models.team import Team
from app.models.player import Player
from app.models.match import Match, MatchStatus
from app.models.league import League, LeagueMember
from app.models.prediction import Prediction
from app.services.auth import get_password_hash, create_access_token

_PG_IMAGE = "postgres:16"


# ---------------------------------------------------------------------------
# Session-scoped engine — one Postgres instance for the whole test run
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine():
    explicit_url = os.getenv("TEST_DATABASE_URL")
    if explicit_url:
        engine = create_engine(explicit_url)
        Base.metadata.create_all(bind=engine)
        yield engine
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
    else:
        from testcontainers.postgres import PostgresContainer
        with PostgresContainer(_PG_IMAGE) as pg:
            engine = create_engine(pg.get_connection_url())
            Base.metadata.create_all(bind=engine)
            yield engine
            Base.metadata.drop_all(bind=engine)
            engine.dispose()


# ---------------------------------------------------------------------------
# Function-scoped session — rolls back after every test, no schema churn
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session(db_engine):
    with db_engine.connect() as conn:
        conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        conn.rollback()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared data fixtures (unchanged API, now run on Postgres)
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user(db_session):
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user2(db_session):
    user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password=get_password_hash("password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def test_tournament(db_session):
    tournament = Tournament(
        name="Test Tournament 2025",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=30)).date(),
    )
    db_session.add(tournament)
    db_session.commit()
    db_session.refresh(tournament)
    return tournament


@pytest.fixture
def test_teams(db_session):
    team1 = Team(name="Team A", short_name="TMA")
    team2 = Team(name="Team B", short_name="TMB")
    db_session.add_all([team1, team2])
    db_session.commit()

    for i in range(11):
        role = "Batsman" if i < 4 else "Bowler" if i < 8 else "All-Rounder"
        db_session.add(Player(name=f"Team A Player {i+1}", team_id=team1.id, role=role))
    for i in range(11):
        role = "Batsman" if i < 4 else "Bowler" if i < 8 else "All-Rounder"
        db_session.add(Player(name=f"Team B Player {i+1}", team_id=team2.id, role=role))

    db_session.commit()
    db_session.refresh(team1)
    db_session.refresh(team2)
    return team1, team2


@pytest.fixture
def test_match(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


@pytest.fixture
def completed_match(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    team1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
    team2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=5),
        status=MatchStatus.COMPLETED,
        result_winner_id=team1.id,
        result_most_runs_team1_player_id=team1_players[0].id,
        result_most_runs_team2_player_id=team2_players[0].id,
        result_most_wickets_team1_player_id=team1_players[4].id,
        result_most_wickets_team2_player_id=team2_players[4].id,
        result_pom_player_id=team1_players[0].id,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


@pytest.fixture
def test_league(db_session, test_user):
    league = League(
        name="Test League",
        invite_code="ABC123",
        owner_id=test_user.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.add(LeagueMember(league_id=league.id, user_id=test_user.id))
    db_session.commit()
    db_session.refresh(league)
    return league


@pytest.fixture
def test_prediction(db_session, test_user, test_match, test_teams):
    team1, team2 = test_teams
    team1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
    team2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

    prediction = Prediction(
        user_id=test_user.id,
        match_id=test_match.id,
        predicted_winner_id=team1.id,
        predicted_most_runs_team1_player_id=team1_players[0].id,
        predicted_most_runs_team2_player_id=team2_players[0].id,
        predicted_most_wickets_team1_player_id=team1_players[4].id,
        predicted_most_wickets_team2_player_id=team2_players[4].id,
        predicted_pom_player_id=team1_players[0].id,
    )
    db_session.add(prediction)
    db_session.commit()
    db_session.refresh(prediction)
    return prediction
