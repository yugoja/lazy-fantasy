"""Guard: `match_lineups` is cricket-only.

Football's predict flow expects the full squad (it derives the pitch/bench split
itself); honouring a stray lineup row would silently truncate the squad. These
tests lock in that football ignores match_lineups and that the admin set-lineup
endpoint refuses non-cricket matches.
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.match import Match, MatchStatus
from app.models.match_lineup import MatchLineup
from app.models.player import Player
from app.models.tournament import Tournament
from app.services.match import get_match_players


@pytest.fixture
def football_tournament(db_session):
    t = Tournament(
        name="FIFA WC 2026 Guard",
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
        start_time=datetime.now(timezone.utc) + timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


@pytest.fixture
def admin_client(client, db_session, test_user, auth_token):
    from app.models.user import User
    user = db_session.query(User).filter(User.id == test_user.id).first()
    user.is_admin = True
    db_session.commit()
    return client, {"Authorization": f"Bearer {auth_token}"}


def _add_partial_lineup(db_session, match, team_id, n=3):
    players = db_session.query(Player).filter(Player.team_id == team_id).all()[:n]
    for p in players:
        db_session.add(MatchLineup(match_id=match.id, player_id=p.id))
    db_session.commit()
    return players


class TestGetMatchPlayersSportGuard:
    def test_football_ignores_match_lineups_returns_full_squad(self, db_session, football_match):
        # Stray lineup rows on a football match must NOT restrict the squad.
        _add_partial_lineup(db_session, football_match, football_match.team_1_id, n=3)

        t1, t2, lineup_announced, _, _ = get_match_players(db_session, football_match.id)

        assert len(t1) == 11  # full squad, not the 3 lineup rows
        assert len(t2) == 11
        assert lineup_announced is False

    def test_cricket_still_honors_match_lineups(self, db_session, test_match):
        # test_match defaults to a cricket tournament — lineups should restrict the squad.
        _add_partial_lineup(db_session, test_match, test_match.team_1_id, n=3)
        _add_partial_lineup(db_session, test_match, test_match.team_2_id, n=3)

        t1, t2, lineup_announced, _, _ = get_match_players(db_session, test_match.id)

        assert len(t1) == 3
        assert len(t2) == 3
        assert lineup_announced is True


class TestSetLineupEndpointGuard:
    def test_rejects_football_match(self, admin_client, db_session, football_match):
        client, headers = admin_client
        player_ids = [p.id for p in db_session.query(Player).all()[:22]]

        resp = client.post(
            f"/admin/matches/{football_match.id}/lineup",
            json={"player_ids": player_ids},
            headers=headers,
        )

        assert resp.status_code == 400
        assert "football" in resp.json()["detail"].lower()
        # And no rows were written.
        assert db_session.query(MatchLineup).filter(
            MatchLineup.match_id == football_match.id
        ).count() == 0

    def test_allows_cricket_match(self, admin_client, db_session, test_match, test_teams):
        client, headers = admin_client
        team1, team2 = test_teams
        t1_ids = [p.id for p in db_session.query(Player).filter(Player.team_id == team1.id).all()[:11]]
        t2_ids = [p.id for p in db_session.query(Player).filter(Player.team_id == team2.id).all()[:11]]

        resp = client.post(
            f"/admin/matches/{test_match.id}/lineup",
            json={"player_ids": t1_ids + t2_ids},
            headers=headers,
        )

        assert resp.status_code == 200
        assert db_session.query(MatchLineup).filter(
            MatchLineup.match_id == test_match.id
        ).count() == 22
