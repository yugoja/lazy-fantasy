"""Friends' Picks endpoint must support football matches.

Football predictions live in `football_predictions` (extension of `predictions`)
with null cricket fields, so the old cricket-only path 500'd on serialization.
These tests lock in the football-shaped payload.
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.football_prediction import FootballPrediction
from app.models.tournament import Tournament
from app.models.league import League, LeagueMember
from app.models.player import Player


@pytest.fixture
def football_tournament(db_session):
    t = Tournament(
        name="WC Friends 2026",
        sport="football",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=60)).date(),
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def locked_football_match(db_session, football_tournament, test_teams):
    team1, team2 = test_teams
    m = Match(
        tournament_id=football_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),  # locked
        status=MatchStatus.SCHEDULED,
        stage="GROUP",
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


def _add_football_pred(db_session, user_id, match, picks, t1=2, t2=1):
    p = Prediction(user_id=user_id, match_id=match.id, points_earned=0, is_processed=False)
    p.football = FootballPrediction(
        team1_goals=t1,
        team2_goals=t2,
        advance_winner_id=None,
        player_pick_1_id=picks[0],
        player_pick_2_id=picks[1],
        player_pick_3_id=picks[2],
    )
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture
def two_member_league(db_session, test_user, test_user2):
    league = League(name="Friends League", invite_code="FFP123", owner_id=test_user.id)
    db_session.add(league)
    db_session.commit()
    db_session.add_all([
        LeagueMember(league_id=league.id, user_id=test_user.id),
        LeagueMember(league_id=league.id, user_id=test_user2.id),
    ])
    db_session.commit()
    db_session.refresh(league)
    return league


class TestFootballFriendsPicks:
    def test_returns_football_shaped_predictions(
        self, client, db_session, test_user, test_user2, auth_headers,
        test_teams, locked_football_match, two_member_league,
    ):
        team1, _ = test_teams
        t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()

        _add_football_pred(
            db_session, test_user.id, locked_football_match,
            [t1_players[0].id, t1_players[1].id, t1_players[2].id], t1=2, t2=1,
        )
        _add_football_pred(
            db_session, test_user2.id, locked_football_match,
            [t1_players[3].id, t1_players[4].id, t1_players[5].id], t1=0, t2=0,
        )

        resp = client.get(
            f"/leagues/{two_member_league.id}/matches/{locked_football_match.id}/predictions",
            headers=auth_headers,
        )

        assert resp.status_code == 200  # used to 500 on null cricket fields
        data = resp.json()
        assert len(data) == 2
        assert all(d["sport"] == "football" for d in data)

        me = next(d for d in data if d["is_me"])
        assert (me["team1_goals"], me["team2_goals"]) == (2, 1)
        assert [pp["player"]["id"] for pp in me["player_picks"]] == [
            t1_players[0].id, t1_players[1].id, t1_players[2].id,
        ]
        # pending match → no per-pick points yet
        assert all(pp["points"] is None for pp in me["player_picks"])
        # current user is sorted first
        assert data[0]["is_me"] is True

    def test_empty_when_no_one_predicted(
        self, client, auth_headers, locked_football_match, two_member_league,
    ):
        resp = client.get(
            f"/leagues/{two_member_league.id}/matches/{locked_football_match.id}/predictions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []
