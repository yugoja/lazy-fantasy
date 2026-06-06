"""
Integration tests for auto-computing group_round when admin creates GROUP matches.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.user import User
from app.models.tournament import Tournament
from app.models.team import Team
from app.services.auth import get_password_hash, create_access_token

pytestmark = pytest.mark.integration


@pytest.fixture
def admin_user(db_session):
    user = User(
        username="adminround",
        email="adminround@test.com",
        hashed_password=get_password_hash("pw"),
        is_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return user, token


@pytest.fixture
def tournament_and_teams(db_session):
    t = Tournament(
        name="WC Admin Round Test",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=60)).date(),
    )
    db_session.add(t)

    t1 = Team(name="TeamX", short_name="TMX")
    t2 = Team(name="TeamY", short_name="TMY")
    t3 = Team(name="TeamZ", short_name="TMZ")
    db_session.add_all([t1, t2, t3])
    db_session.commit()
    db_session.refresh(t)
    db_session.refresh(t1)
    db_session.refresh(t2)
    db_session.refresh(t3)
    return t, t1, t2, t3


def _post_match(client, token, tournament_id, team_1_id, team_2_id, stage, offset_days=0):
    start = (datetime.now(timezone.utc) + timedelta(days=offset_days)).isoformat()
    return client.post(
        "/admin/matches/",
        json={
            "tournament_id": tournament_id,
            "team_1_id": team_1_id,
            "team_2_id": team_2_id,
            "start_time": start,
            "stage": stage,
        },
        headers={"Authorization": f"Bearer {token}"},
    )


class TestAdminGroupRound:
    def test_first_group_match_gets_round_1(self, client, admin_user, tournament_and_teams):
        _, token = admin_user
        t, t1, t2, t3 = tournament_and_teams
        resp = _post_match(client, token, t.id, t1.id, t2.id, "GROUP", offset_days=1)
        assert resp.status_code == 201
        assert resp.json()["group_round"] == 1

    def test_second_group_match_gets_round_2(self, client, admin_user, tournament_and_teams):
        _, token = admin_user
        t, t1, t2, t3 = tournament_and_teams
        _post_match(client, token, t.id, t1.id, t2.id, "GROUP", offset_days=1)
        resp = _post_match(client, token, t.id, t1.id, t3.id, "GROUP", offset_days=5)
        assert resp.status_code == 201
        assert resp.json()["group_round"] == 2

    def test_fourth_group_match_raises_400(self, client, admin_user, tournament_and_teams):
        _, token = admin_user
        t, t1, t2, t3 = tournament_and_teams
        _post_match(client, token, t.id, t1.id, t2.id, "GROUP", offset_days=1)
        _post_match(client, token, t.id, t1.id, t3.id, "GROUP", offset_days=5)
        _post_match(client, token, t.id, t1.id, t2.id, "GROUP", offset_days=10)
        resp = _post_match(client, token, t.id, t1.id, t3.id, "GROUP", offset_days=15)
        assert resp.status_code == 400

    def test_knockout_match_has_no_group_round(self, client, admin_user, tournament_and_teams):
        _, token = admin_user
        t, t1, t2, t3 = tournament_and_teams
        resp = _post_match(client, token, t.id, t1.id, t2.id, "QF", offset_days=30)
        assert resp.status_code == 201
        assert resp.json()["group_round"] is None

    def test_match_without_stage_has_no_group_round(self, client, admin_user, tournament_and_teams):
        _, token = admin_user
        t, t1, t2, t3 = tournament_and_teams
        start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        resp = client.post(
            "/admin/matches/",
            json={
                "tournament_id": t.id,
                "team_1_id": t1.id,
                "team_2_id": t2.id,
                "start_time": start,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["group_round"] is None
