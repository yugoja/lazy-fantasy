"""
Integration tests for the /dugout endpoints.
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.league import League, LeagueMember
from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.prediction import Prediction
from app.models.dugout_dismissal import DugoutDismissal
from app.services.auth import create_access_token


def _auth(user):
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def _locked_match(db, tournament, team1, team2):
    m = Match(
        tournament_id=tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        status=MatchStatus.SCHEDULED,
    )
    db.add(m)
    db.flush()
    return m


@pytest.mark.integration
class TestDugoutEndpoints:
    def test_get_dugout_requires_auth(self, client):
        resp = client.get("/dugout/")
        assert resp.status_code == 401

    def test_get_dugout_empty_when_no_league(self, client, db_session, test_user):
        resp = client.get("/dugout/", headers=_auth(test_user))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_dugout_returns_contrarian_event(
        self, client, db_session, test_user, test_user2, test_tournament, test_teams
    ):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        # Create league with both users
        league = League(name="TestLeague", invite_code="TL0001", owner_id=test_user.id)
        db_session.add(league)
        db_session.flush()
        db_session.add(LeagueMember(league_id=league.id, user_id=test_user.id))
        db_session.add(LeagueMember(league_id=league.id, user_id=test_user2.id))

        # Create a third user to make it 3 total (avoids all-lone-wolf edge case)
        from app.models.user import User
        from app.services.auth import get_password_hash
        u3 = User(username="u3int", email="u3int@t.com", hashed_password=get_password_hash("x"))
        db_session.add(u3)
        db_session.flush()
        db_session.add(LeagueMember(league_id=league.id, user_id=u3.id))

        match = _locked_match(db_session, test_tournament, team1, team2)

        # test_user + u3 pick team1; test_user2 lone wolf picks team2
        for uid in (test_user.id, u3.id):
            db_session.add(Prediction(
                user_id=uid, match_id=match.id,
                predicted_winner_id=team1.id,
                predicted_most_runs_team1_player_id=players1[0].id,
                predicted_most_runs_team2_player_id=players2[0].id,
                predicted_most_wickets_team1_player_id=players1[4].id,
                predicted_most_wickets_team2_player_id=players2[4].id,
                predicted_pom_player_id=players1[0].id,
            ))
        db_session.add(Prediction(
            user_id=test_user2.id, match_id=match.id,
            predicted_winner_id=team2.id,
            predicted_most_runs_team1_player_id=players1[1].id,
            predicted_most_runs_team2_player_id=players2[1].id,
            predicted_most_wickets_team1_player_id=players1[5].id,
            predicted_most_wickets_team2_player_id=players2[5].id,
            predicted_pom_player_id=players2[0].id,
        ))
        db_session.commit()

        resp = client.get("/dugout/", headers=_auth(test_user))
        assert resp.status_code == 200
        events = resp.json()
        contrarian = [e for e in events if e["type"] == "contrarian"]
        assert len(contrarian) == 1
        assert contrarian[0]["username"] == "testuser2"
        assert contrarian[0]["team_short_name"] == team2.short_name

    def test_dismiss_requires_auth(self, client):
        resp = client.post("/dugout/dismiss", json={
            "type": "contrarian", "league_id": 1, "match_id": 1, "subject_username": "x"
        })
        assert resp.status_code == 401

    def test_dismiss_removes_event_from_feed(
        self, client, db_session, test_user, test_user2, test_tournament, test_teams
    ):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        from app.models.user import User
        from app.services.auth import get_password_hash
        u3 = User(username="u3dis", email="u3dis@t.com", hashed_password=get_password_hash("x"))
        db_session.add(u3)
        db_session.flush()

        league = League(name="DisLeague", invite_code="DIS001", owner_id=test_user.id)
        db_session.add(league)
        db_session.flush()
        for uid in (test_user.id, test_user2.id, u3.id):
            db_session.add(LeagueMember(league_id=league.id, user_id=uid))

        match = _locked_match(db_session, test_tournament, team1, team2)
        for uid in (test_user.id, u3.id):
            db_session.add(Prediction(
                user_id=uid, match_id=match.id,
                predicted_winner_id=team1.id,
                predicted_most_runs_team1_player_id=players1[0].id,
                predicted_most_runs_team2_player_id=players2[0].id,
                predicted_most_wickets_team1_player_id=players1[4].id,
                predicted_most_wickets_team2_player_id=players2[4].id,
                predicted_pom_player_id=players1[0].id,
            ))
        db_session.add(Prediction(
            user_id=test_user2.id, match_id=match.id,
            predicted_winner_id=team2.id,
            predicted_most_runs_team1_player_id=players1[1].id,
            predicted_most_runs_team2_player_id=players2[1].id,
            predicted_most_wickets_team1_player_id=players1[5].id,
            predicted_most_wickets_team2_player_id=players2[5].id,
            predicted_pom_player_id=players2[0].id,
        ))
        db_session.commit()

        # Confirm event is present
        resp = client.get("/dugout/", headers=_auth(test_user))
        assert any(e["type"] == "contrarian" for e in resp.json())

        # Dismiss it
        resp = client.post("/dugout/dismiss", headers=_auth(test_user), json={
            "type": "contrarian",
            "league_id": league.id,
            "match_id": match.id,
            "subject_username": "testuser2",
        })
        assert resp.status_code == 204

        # Confirm it's gone
        resp = client.get("/dugout/", headers=_auth(test_user))
        assert not any(e["type"] == "contrarian" for e in resp.json())

    def test_dismiss_is_idempotent(
        self, client, db_session, test_user, test_tournament, test_teams
    ):
        team1, team2 = test_teams
        league = League(name="IdemLeague", invite_code="IDM001", owner_id=test_user.id)
        db_session.add(league)
        db_session.flush()
        db_session.add(LeagueMember(league_id=league.id, user_id=test_user.id))
        db_session.commit()

        body = {"type": "rank_shift", "league_id": league.id, "match_id": None, "subject_username": "testuser"}

        resp1 = client.post("/dugout/dismiss", headers=_auth(test_user), json=body)
        resp2 = client.post("/dugout/dismiss", headers=_auth(test_user), json=body)
        assert resp1.status_code == 204
        assert resp2.status_code == 204

        # Should only be one row in DB
        count = db_session.query(DugoutDismissal).filter(
            DugoutDismissal.user_id == test_user.id,
            DugoutDismissal.type == "rank_shift",
            DugoutDismissal.league_id == league.id,
        ).count()
        assert count == 1

    def test_match_verdict_event_surfaces_after_scoring(
        self, client, db_session, test_user, test_user2, test_tournament, test_teams
    ):
        """A scored match produces a match_verdict event in the feed and an endpoint hit."""
        from app.services.scoring import calculate_scores
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        # League with two members
        league = League(name="VerdictLeague", invite_code="VRD001", owner_id=test_user.id)
        db_session.add(league)
        db_session.flush()
        for uid in (test_user.id, test_user2.id):
            db_session.add(LeagueMember(league_id=league.id, user_id=uid))

        # Completed match with results
        match = Match(
            tournament_id=test_tournament.id,
            team_1_id=team1.id, team_2_id=team2.id,
            start_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=4),
            status=MatchStatus.COMPLETED,
            result_winner_id=team1.id,
            result_most_runs_team1_player_id=players1[0].id,
            result_most_runs_team2_player_id=players2[0].id,
            result_most_wickets_team1_player_id=players1[4].id,
            result_most_wickets_team2_player_id=players2[4].id,
            result_pom_player_id=players1[0].id,
        )
        db_session.add(match)
        db_session.flush()

        # test_user2 gets flawless; test_user gets winner-only
        db_session.add(Prediction(
            user_id=test_user2.id, match_id=match.id,
            predicted_winner_id=team1.id,
            predicted_most_runs_team1_player_id=players1[0].id,
            predicted_most_runs_team2_player_id=players2[0].id,
            predicted_most_wickets_team1_player_id=players1[4].id,
            predicted_most_wickets_team2_player_id=players2[4].id,
            predicted_pom_player_id=players1[0].id,
        ))
        db_session.add(Prediction(
            user_id=test_user.id, match_id=match.id,
            predicted_winner_id=team1.id,
            predicted_most_runs_team1_player_id=players1[1].id,
            predicted_most_runs_team2_player_id=players2[1].id,
            predicted_most_wickets_team1_player_id=players1[5].id,
            predicted_most_wickets_team2_player_id=players2[5].id,
            predicted_pom_player_id=players2[2].id,
        ))
        db_session.commit()
        calculate_scores(db_session, match.id)

        # Feed surfaces the verdict
        resp = client.get("/dugout/", headers=_auth(test_user))
        assert resp.status_code == 200
        events = resp.json()
        verdicts = [e for e in events if e["type"] == "match_verdict"]
        assert len(verdicts) == 1
        v = verdicts[0]
        assert v["league_id"] == league.id
        assert v["match_id"] == match.id
        assert v["top_score"] == 140
        assert v["pom_player_name"] == players1[0].name
        assert len(v["winners"]) == 1
        assert v["winners"][0]["username"] == test_user2.username

        # Direct endpoint also returns the same verdict
        resp2 = client.get(
            f"/leagues/{league.id}/matches/{match.id}/verdict",
            headers=_auth(test_user),
        )
        assert resp2.status_code == 200
        body = resp2.json()
        assert body["top_score"] == 140
        assert body["match_id"] == match.id

    def test_match_verdict_endpoint_404_when_no_data(
        self, client, db_session, test_user, test_tournament, test_teams
    ):
        team1, team2 = test_teams
        league = League(name="EmptyVerdict", invite_code="EVR001", owner_id=test_user.id)
        db_session.add(league)
        db_session.flush()
        db_session.add(LeagueMember(league_id=league.id, user_id=test_user.id))
        # SCHEDULED match — no verdict yet
        m = Match(
            tournament_id=test_tournament.id,
            team_1_id=team1.id, team_2_id=team2.id,
            start_time=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=2),
            status=MatchStatus.SCHEDULED,
        )
        db_session.add(m)
        db_session.commit()
        resp = client.get(
            f"/leagues/{league.id}/matches/{m.id}/verdict",
            headers=_auth(test_user),
        )
        assert resp.status_code == 404
