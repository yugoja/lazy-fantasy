"""Integration tests for admin CricAPI sync endpoints."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.services.cricket_provider import ProviderMatchInfo, ProviderPlayer
from app.services.cricket_sync import set_provider


def make_admin(db_session, user_id: int):
    from app.models.user import User
    user = db_session.query(User).filter(User.id == user_id).first()
    user.is_admin = True
    db_session.commit()


def make_mock_provider(match_name="CSK vs MI", status="Match not started",
                       lineup_announced=False, team1_players=None, team2_players=None,
                       winner_name=None, pom_name=None):
    info = ProviderMatchInfo(
        provider_match_id="ext-test",
        name=match_name,
        status=status,
        team1_name="CSK",
        team2_name="MI",
        lineup_announced=lineup_announced,
        team1_players=team1_players or [],
        team2_players=team2_players or [],
        winner_name=winner_name,
        pom_name=pom_name,
        overs_completed=None,
    )
    provider = MagicMock()
    provider.get_match_info.return_value = info
    return provider, info


@pytest.fixture
def admin_client(client, db_session, test_user, auth_token):
    make_admin(db_session, test_user.id)
    return client, {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def linked_match(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        external_match_id="ext-test",
        sync_state="linked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


# ---------------------------------------------------------------------------
# POST /admin/matches/{id}/link
# ---------------------------------------------------------------------------

class TestLinkMatch:
    def test_link_sets_external_id_and_state(self, admin_client, db_session, test_match):
        client, headers = admin_client
        provider, _ = make_mock_provider()
        set_provider(provider)

        resp = client.post(
            f"/admin/matches/{test_match.id}/link",
            json={"external_match_id": "ext-test"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["external_match_id"] == "ext-test"
        assert data["sync_state"] == "linked"
        assert data["cricapi_preview"]["name"] == "CSK vs MI"

        db_session.refresh(test_match)
        assert test_match.external_match_id == "ext-test"
        assert test_match.sync_state == "linked"

        set_provider(None)

    def test_link_returns_400_when_cricapi_returns_no_data(self, admin_client, test_match):
        client, headers = admin_client
        provider = MagicMock()
        provider.get_match_info.return_value = None
        set_provider(provider)

        resp = client.post(
            f"/admin/matches/{test_match.id}/link",
            json={"external_match_id": "bad-id"},
            headers=headers,
        )
        assert resp.status_code == 400

        set_provider(None)

    def test_link_returns_503_when_no_provider(self, admin_client, test_match):
        client, headers = admin_client
        set_provider(None)

        resp = client.post(
            f"/admin/matches/{test_match.id}/link",
            json={"external_match_id": "ext-test"},
            headers=headers,
        )
        assert resp.status_code == 503

    def test_link_returns_404_for_unknown_match(self, admin_client):
        client, headers = admin_client
        provider, _ = make_mock_provider()
        set_provider(provider)

        resp = client.post(
            "/admin/matches/99999/link",
            json={"external_match_id": "ext-test"},
            headers=headers,
        )
        assert resp.status_code == 404

        set_provider(None)

    def test_link_requires_admin(self, client, test_match, auth_headers):
        # Regular (non-admin) user should get 403
        provider, _ = make_mock_provider()
        set_provider(provider)

        resp = client.post(
            f"/admin/matches/{test_match.id}/link",
            json={"external_match_id": "ext-test"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

        set_provider(None)


# ---------------------------------------------------------------------------
# DELETE /admin/matches/{id}/link
# ---------------------------------------------------------------------------

class TestUnlinkMatch:
    def test_unlink_clears_sync_fields(self, admin_client, db_session, linked_match):
        client, headers = admin_client

        resp = client.delete(
            f"/admin/matches/{linked_match.id}/link",
            headers=headers,
        )
        assert resp.status_code == 204

        db_session.refresh(linked_match)
        assert linked_match.external_match_id is None
        assert linked_match.sync_state == "unlinked"
        assert linked_match.sync_error is None
        assert linked_match.last_synced_at is None

    def test_unlink_returns_404_for_unknown_match(self, admin_client):
        client, headers = admin_client
        resp = client.delete("/admin/matches/99999/link", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /admin/matches/{id}/sync-status
# ---------------------------------------------------------------------------

class TestSyncStatus:
    def test_returns_status_without_preview_when_unlinked(self, admin_client, test_match):
        client, headers = admin_client

        resp = client.get(
            f"/admin/matches/{test_match.id}/sync-status",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sync_state"] == "unlinked"
        assert data["cricapi_preview"] is None

    def test_returns_preview_when_linked_and_provider_set(self, admin_client, linked_match):
        client, headers = admin_client
        provider, _ = make_mock_provider(lineup_announced=True)
        set_provider(provider)

        resp = client.get(
            f"/admin/matches/{linked_match.id}/sync-status",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["external_match_id"] == "ext-test"
        assert data["cricapi_preview"]["lineup_announced"] is True

        set_provider(None)

    def test_returns_no_preview_when_provider_not_set(self, admin_client, linked_match):
        client, headers = admin_client
        set_provider(None)

        resp = client.get(
            f"/admin/matches/{linked_match.id}/sync-status",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cricapi_preview"] is None


# ---------------------------------------------------------------------------
# POST /admin/matches/{id}/sync (force sync)
# ---------------------------------------------------------------------------

class TestForceSync:
    def test_force_sync_lineup_when_announced(
        self, admin_client, db_session, linked_match, test_teams
    ):
        client, headers = admin_client
        team1, team2 = test_teams
        t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
        t2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

        for p in t1_players + t2_players:
            p.cricapi_player_id = f"cric-{p.id}"
        db_session.commit()

        def make_pp(player):
            return ProviderPlayer(
                provider_id=f"cric-{player.id}", name=player.name, team_name=""
            )

        provider, _ = make_mock_provider(
            lineup_announced=True,
            team1_players=[make_pp(p) for p in t1_players],
            team2_players=[make_pp(p) for p in t2_players],
        )
        set_provider(provider)

        resp = client.post(
            f"/admin/matches/{linked_match.id}/sync",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "lineup_sync"

        db_session.refresh(linked_match)
        assert linked_match.sync_state == "lineup_synced"

        set_provider(None)

    def test_force_sync_result_when_match_over(
        self, admin_client, db_session, test_tournament, test_teams
    ):
        client, headers = admin_client
        team1, team2 = test_teams
        t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
        t2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

        for p in t1_players + t2_players:
            p.cricapi_player_id = f"cric-{p.id}"
        db_session.commit()

        match = Match(
            tournament_id=test_tournament.id,
            team_1_id=team1.id,
            team_2_id=team2.id,
            start_time=datetime.now(timezone.utc) - timedelta(hours=4),
            status=MatchStatus.SCHEDULED,
            external_match_id="ext-test",
            sync_state="lineup_synced",
        )
        db_session.add(match)
        db_session.commit()
        db_session.refresh(match)

        def make_pp(player, runs=0, wickets=0):
            pp = ProviderPlayer(provider_id=f"cric-{player.id}", name=player.name, team_name="")
            pp.batting_runs = runs
            pp.bowling_wickets = wickets
            return pp

        t1_pps = [make_pp(p, runs=50 if i == 0 else 5) for i, p in enumerate(t1_players)]
        t2_pps = [make_pp(p, runs=40 if i == 0 else 3, wickets=2 if i == 4 else 0)
                  for i, p in enumerate(t2_players)]
        t1_pps[4].bowling_wickets = 3

        info = ProviderMatchInfo(
            provider_match_id="ext-test",
            name="Team A vs Team B",
            status=f"{team1.name} won by 5 wickets",
            team1_name=team1.name,
            team2_name=team2.name,
            lineup_announced=True,
            team1_players=t1_pps,
            team2_players=t2_pps,
            winner_name=team1.name,
            pom_name=t1_players[0].name,
            overs_completed=20.0,
        )
        provider = MagicMock()
        provider.get_match_info.return_value = info
        set_provider(provider)

        resp = client.post(
            f"/admin/matches/{match.id}/sync",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "result_sync"

        db_session.refresh(match)
        assert match.status == MatchStatus.COMPLETED

        set_provider(None)

    def test_force_sync_returns_400_when_unlinked(self, admin_client, test_match):
        client, headers = admin_client
        resp = client.post(
            f"/admin/matches/{test_match.id}/sync",
            headers=headers,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /admin/matches/{id}/player-mapping
# ---------------------------------------------------------------------------

class TestPlayerMapping:
    def test_returns_resolved_and_unresolved_players(
        self, admin_client, db_session, linked_match, test_teams
    ):
        client, headers = admin_client
        team1, team2 = test_teams
        t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
        t2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

        # Give first player exact ID match, rest will be unmatched
        t1_players[0].cricapi_player_id = "cric-known"
        db_session.commit()

        provider = MagicMock()
        info = ProviderMatchInfo(
            provider_match_id="ext-test",
            name="Test",
            status="Match not started",
            team1_name=team1.name,
            team2_name=team2.name,
            lineup_announced=True,
            team1_players=[
                ProviderPlayer("cric-known", t1_players[0].name, ""),  # will resolve
                ProviderPlayer("", "Nobody Unknown", ""),               # won't resolve
            ],
            team2_players=[],
            winner_name=None,
            pom_name=None,
            overs_completed=None,
        )
        provider.get_match_info.return_value = info
        set_provider(provider)

        resp = client.get(
            f"/admin/matches/{linked_match.id}/player-mapping",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        players = data["players"]

        resolved = [p for p in players if p["resolved"]]
        unresolved = [p for p in players if not p["resolved"]]
        assert len(resolved) == 1
        assert resolved[0]["player_id"] == t1_players[0].id
        assert len(unresolved) == 1
        assert unresolved[0]["provider_name"] == "Nobody Unknown"
        assert len(unresolved[0]["suggestions"]) > 0

        set_provider(None)

    def test_returns_400_when_not_linked(self, admin_client, test_match):
        client, headers = admin_client
        resp = client.get(
            f"/admin/matches/{test_match.id}/player-mapping",
            headers=headers,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /admin/matches/{id}/player-mapping
# ---------------------------------------------------------------------------

class TestSavePlayerMapping:
    def test_saves_cricapi_player_id(self, admin_client, db_session, linked_match, test_teams):
        client, headers = admin_client
        team1, _ = test_teams
        player = db_session.query(Player).filter(Player.team_id == team1.id).first()
        assert player.cricapi_player_id is None

        resp = client.post(
            f"/admin/matches/{linked_match.id}/player-mapping",
            json={"mappings": [{"provider_id": "cric-abc", "player_id": player.id}]},
            headers=headers,
        )
        assert resp.status_code == 204

        db_session.refresh(player)
        assert player.cricapi_player_id == "cric-abc"

    def test_returns_400_for_unknown_player(self, admin_client, linked_match):
        client, headers = admin_client
        resp = client.post(
            f"/admin/matches/{linked_match.id}/player-mapping",
            json={"mappings": [{"provider_id": "cric-xyz", "player_id": 99999}]},
            headers=headers,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /admin/matches (sync fields present)
# ---------------------------------------------------------------------------

class TestAdminMatchList:
    def test_list_includes_sync_fields(self, admin_client, linked_match):
        client, headers = admin_client
        resp = client.get("/admin/matches", headers=headers)
        assert resp.status_code == 200
        matches = resp.json()
        match = next((m for m in matches if m["id"] == linked_match.id), None)
        assert match is not None
        assert match["external_match_id"] == "ext-test"
        assert match["sync_state"] == "linked"
        assert "sync_error" in match
        assert "last_synced_at" in match
