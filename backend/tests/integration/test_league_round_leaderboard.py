"""
Integration tests for the round-based leaderboard filter endpoint.

Tests the GET /leagues/{id}/leaderboard?round=... query param validation.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.match import Match, MatchStatus
from app.models.league import League, LeagueMember
from app.models.prediction import Prediction
from app.models.user import User
from app.models.tournament import Tournament
from app.models.team import Team
from app.services.auth import get_password_hash, create_access_token

pytestmark = pytest.mark.integration


@pytest.fixture
def round_league_setup(db_session):
    """Minimal setup: one user, one league, one GROUP_1 match with a scored prediction."""
    tournament = Tournament(
        name="WC 2026 Integration",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=60)).date(),
    )
    db_session.add(tournament)
    db_session.flush()

    t1 = Team(name="AlphaInt", short_name="ALI")
    t2 = Team(name="BetaInt", short_name="BEI")
    db_session.add_all([t1, t2])
    db_session.flush()

    user = User(username="round_user", email="round_user@test.com",
                hashed_password=get_password_hash("pw"))
    db_session.add(user)
    db_session.flush()

    league = League(name="Round Test League", invite_code="RND999", owner_id=user.id)
    db_session.add(league)
    db_session.flush()
    db_session.add(LeagueMember(league_id=league.id, user_id=user.id))
    db_session.flush()

    match = Match(
        tournament_id=tournament.id, team_1_id=t1.id, team_2_id=t2.id,
        start_time=league.created_at + timedelta(hours=1),
        status=MatchStatus.COMPLETED, stage="GROUP", group_round=1,
    )
    db_session.add(match)
    db_session.flush()

    db_session.add(Prediction(
        user_id=user.id, match_id=match.id, points_earned=15, is_processed=True,
    ))
    db_session.commit()

    token = create_access_token(data={"sub": str(user.id)})
    return {"league": league, "user": user, "token": token}


class TestLeaderboardRoundQueryParam:
    def test_no_round_returns_200(self, client, round_league_setup):
        league_id = round_league_setup["league"].id
        token = round_league_setup["token"]
        resp = client.get(
            f"/leagues/{league_id}/leaderboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_valid_group_round_returns_200(self, client, round_league_setup):
        league_id = round_league_setup["league"].id
        token = round_league_setup["token"]
        resp = client.get(
            f"/leagues/{league_id}/leaderboard?round=GROUP_1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_valid_knockout_round_returns_200(self, client, round_league_setup):
        league_id = round_league_setup["league"].id
        token = round_league_setup["token"]
        resp = client.get(
            f"/leagues/{league_id}/leaderboard?round=QF",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_invalid_round_returns_422(self, client, round_league_setup):
        league_id = round_league_setup["league"].id
        token = round_league_setup["token"]
        resp = client.get(
            f"/leagues/{league_id}/leaderboard?round=INVALID",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_group_1_points_match_only_round_1(self, client, round_league_setup):
        """Points returned for GROUP_1 should only reflect round-1 matches."""
        league_id = round_league_setup["league"].id
        token = round_league_setup["token"]
        resp = client.get(
            f"/leagues/{league_id}/leaderboard?round=GROUP_1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        entry = resp.json()["entries"][0]
        assert entry["total_points"] == 15

    def test_qf_round_with_no_matches_gives_zero(self, client, round_league_setup):
        """No QF matches in setup → all users score 0."""
        league_id = round_league_setup["league"].id
        token = round_league_setup["token"]
        resp = client.get(
            f"/leagues/{league_id}/leaderboard?round=QF",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        entry = resp.json()["entries"][0]
        assert entry["total_points"] == 0

    def test_available_rounds_included_in_response(self, client, round_league_setup):
        """available_rounds field should list completed round keys for this league."""
        league_id = round_league_setup["league"].id
        token = round_league_setup["token"]
        resp = client.get(
            f"/leagues/{league_id}/leaderboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "available_rounds" in data
        # The fixture has one completed GROUP_1 match
        assert "GROUP_1" in data["available_rounds"]

    def test_all_valid_round_keys_accepted(self, client, round_league_setup):
        league_id = round_league_setup["league"].id
        token = round_league_setup["token"]
        valid_keys = ["GROUP_1", "GROUP_2", "GROUP_3", "R32", "R16", "QF", "SF", "THIRD", "FINAL"]
        for key in valid_keys:
            resp = client.get(
                f"/leagues/{league_id}/leaderboard?round={key}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200, f"Expected 200 for round={key}, got {resp.status_code}"
