"""Integration tests for admin football sync endpoints."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.tournament import Tournament
from app.models.football_match_result import FootballMatchResult
from app.services.football_provider import FootballFixtureResult, FootballPlayerStat
from app.services.football_sync import set_provider


def make_admin(db_session, user_id: int):
    from app.models.user import User
    user = db_session.query(User).filter(User.id == user_id).first()
    user.is_admin = True
    db_session.commit()


@pytest.fixture
def football_tournament(db_session):
    t = Tournament(
        name="FIFA WC 2026",
        sport="football",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=60)).date(),
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def football_match(db_session, football_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=football_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        sync_state="unlinked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


@pytest.fixture
def linked_football_match(db_session, football_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=football_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        external_match_id="12345",
        sync_state="linked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


@pytest.fixture
def admin_client(client, db_session, test_user, auth_token):
    make_admin(db_session, test_user.id)
    return client, {"Authorization": f"Bearer {auth_token}"}


# ---------------------------------------------------------------------------
# POST /admin/matches/{id}/link-football
# ---------------------------------------------------------------------------

class TestLinkFootball:
    def test_sets_external_match_id_and_state(self, admin_client, db_session, football_match):
        client, headers = admin_client

        resp = client.post(
            f"/admin/matches/{football_match.id}/link-football",
            json={"fixture_id": 99001},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sync_state"] == "linked"
        assert data["status"] == "linked"

        db_session.refresh(football_match)
        assert football_match.external_match_id == "99001"
        assert football_match.sync_state == "linked"
        assert football_match.sync_error is None

    def test_overwrites_existing_fixture_id(self, admin_client, db_session, linked_football_match):
        client, headers = admin_client

        resp = client.post(
            f"/admin/matches/{linked_football_match.id}/link-football",
            json={"fixture_id": 99002},
            headers=headers,
        )
        assert resp.status_code == 200

        db_session.refresh(linked_football_match)
        assert linked_football_match.external_match_id == "99002"

    def test_returns_404_for_unknown_match(self, admin_client):
        client, headers = admin_client
        resp = client.post(
            "/admin/matches/99999/link-football",
            json={"fixture_id": 1},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_requires_admin(self, client, football_match, auth_headers):
        resp = client.post(
            f"/admin/matches/{football_match.id}/link-football",
            json={"fixture_id": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /admin/matches/{id}/sync-football
# ---------------------------------------------------------------------------

class TestSyncFootball:
    def test_returns_400_when_no_external_id(self, admin_client, football_match):
        client, headers = admin_client
        resp = client.post(
            f"/admin/matches/{football_match.id}/sync-football",
            headers=headers,
        )
        assert resp.status_code == 400

    def test_returns_503_when_provider_not_configured(self, admin_client, linked_football_match):
        client, headers = admin_client
        set_provider(None)

        resp = client.post(
            f"/admin/matches/{linked_football_match.id}/sync-football",
            headers=headers,
        )
        assert resp.status_code == 503

    def test_returns_not_finished_when_api_says_so(self, admin_client, linked_football_match):
        client, headers = admin_client

        mock_provider = MagicMock()
        mock_provider.get_fixture_result.return_value = None
        set_provider(mock_provider)

        resp = client.post(
            f"/admin/matches/{linked_football_match.id}/sync-football",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_finished"
        assert data["predictions_processed"] == 0

        set_provider(None)

    def test_syncs_result_and_scores_predictions(
        self, admin_client, db_session, linked_football_match, test_teams, test_user
    ):
        client, headers = admin_client
        team1, team2 = test_teams
        t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
        t2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

        football_roles = ["Goalkeeper", "Defender", "Defender", "Defender", "Midfielder",
                          "Midfielder", "Midfielder", "Forward", "Forward", "Forward", "Forward"]
        for i, p in enumerate(t1_players):
            p.role = football_roles[i % len(football_roles)]
            p.api_football_player_id = str(p.id)
        for i, p in enumerate(t2_players):
            p.role = football_roles[i % len(football_roles)]
            p.api_football_player_id = str(p.id)
        db_session.commit()

        # Create a football prediction to verify scoring runs
        from app.models.prediction import Prediction
        from app.models.football_prediction import FootballPrediction

        pred = Prediction(user_id=test_user.id, match_id=linked_football_match.id)
        db_session.add(pred)
        db_session.flush()
        fp = FootballPrediction(
            prediction_id=pred.id,
            team1_goals=2,
            team2_goals=1,
            player_pick_1_id=t1_players[0].id,
            player_pick_2_id=t1_players[1].id,
            player_pick_3_id=t2_players[0].id,
        )
        db_session.add(fp)
        db_session.commit()

        fixture_result = FootballFixtureResult(
            fixture_id=12345,
            status_short="FT",
            home_team_api_id=100,
            away_team_api_id=200,
            team1_goals_reg=2,
            team2_goals_reg=1,
            team1_goals_et=None,
            team2_goals_et=None,
            penalty_team1=None,
            penalty_team2=None,
        )
        player_stats = [
            FootballPlayerStat(
                api_player_id=t1_players[0].id,
                name=t1_players[0].name,
                team_api_id=100,
                minutes_played=90, goals=2, assists=0,
                red_card=False, own_goals=0,
                ingame_pen_saves=0, shootout_pen_saves=0, ingame_pen_misses=0,
            ),
        ]

        mock_provider = MagicMock()
        mock_provider.get_fixture_result.return_value = fixture_result
        mock_provider.get_player_stats.return_value = player_stats
        set_provider(mock_provider)

        resp = client.post(
            f"/admin/matches/{linked_football_match.id}/sync-football",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "synced"
        assert data["predictions_processed"] == 1
        assert data["sync_state"] == "result_synced"

        db_session.refresh(linked_football_match)
        assert linked_football_match.status == MatchStatus.COMPLETED
        assert linked_football_match.sync_state == "result_synced"

        fr = db_session.query(FootballMatchResult).filter_by(
            match_id=linked_football_match.id
        ).first()
        assert fr is not None
        assert fr.team1_goals_reg == 2

        set_provider(None)

    def test_unresolved_players_reported_in_response(
        self, admin_client, linked_football_match
    ):
        client, headers = admin_client

        fixture_result = FootballFixtureResult(
            fixture_id=12345,
            status_short="FT",
            home_team_api_id=100,
            away_team_api_id=200,
            team1_goals_reg=1,
            team2_goals_reg=0,
            team1_goals_et=None,
            team2_goals_et=None,
            penalty_team1=None,
            penalty_team2=None,
        )
        player_stats = [
            FootballPlayerStat(
                api_player_id=0,
                name="ZZZXXX Nobody",
                team_api_id=100,
                minutes_played=90, goals=1, assists=0,
                red_card=False, own_goals=0,
                ingame_pen_saves=0, shootout_pen_saves=0, ingame_pen_misses=0,
            ),
        ]

        mock_provider = MagicMock()
        mock_provider.get_fixture_result.return_value = fixture_result
        mock_provider.get_player_stats.return_value = player_stats
        set_provider(mock_provider)

        resp = client.post(
            f"/admin/matches/{linked_football_match.id}/sync-football",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["unresolved_players"]) == 1
        assert "ZZZXXX Nobody" in data["unresolved_players"][0]

        set_provider(None)

    def test_returns_404_for_unknown_match(self, admin_client):
        client, headers = admin_client
        mock_provider = MagicMock()
        set_provider(mock_provider)

        resp = client.post(
            "/admin/matches/99999/sync-football",
            headers=headers,
        )
        assert resp.status_code == 404

        set_provider(None)

    def test_requires_admin(self, client, linked_football_match, auth_headers):
        mock_provider = MagicMock()
        set_provider(mock_provider)

        resp = client.post(
            f"/admin/matches/{linked_football_match.id}/sync-football",
            headers=auth_headers,
        )
        assert resp.status_code == 403

        set_provider(None)


# ---------------------------------------------------------------------------
# GET /admin/matches — tournament_sport field
# ---------------------------------------------------------------------------

class TestAdminMatchListFootballSport:
    def test_tournament_sport_included_in_list(self, admin_client, linked_football_match):
        client, headers = admin_client

        resp = client.get("/admin/matches", headers=headers)
        assert resp.status_code == 200
        matches = resp.json()
        match = next((m for m in matches if m["id"] == linked_football_match.id), None)
        assert match is not None
        assert match["tournament_sport"] == "football"
