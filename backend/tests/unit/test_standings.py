"""Unit tests for league standings / ranking logic."""
from datetime import datetime, timedelta, timezone

from app.models.league import League, LeagueMember
from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.prediction import Prediction
from app.models.user import User
from app.services.league import _compute_standings


def _user(db, username):
    u = User(username=username, email=f"{username}@t.com", hashed_password="x")
    db.add(u)
    db.flush()
    return u


def _league(db, owner_id, *member_ids):
    league = League(
        name="L",
        invite_code="ZZZZZZ",
        owner_id=owner_id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30),
    )
    db.add(league)
    db.flush()
    for uid in (owner_id, *member_ids):
        db.add(LeagueMember(league_id=league.id, user_id=uid))
    db.flush()
    return league


def _prediction_with_points(db, user_id, match_id, winner_id, points, players1, players2):
    p = Prediction(
        user_id=user_id,
        match_id=match_id,
        predicted_winner_id=winner_id,
        predicted_most_runs_team1_player_id=players1[0].id,
        predicted_most_runs_team2_player_id=players2[0].id,
        predicted_most_wickets_team1_player_id=players1[4].id,
        predicted_most_wickets_team2_player_id=players2[4].id,
        predicted_pom_player_id=players1[0].id,
        is_processed=True,
        points_earned=points,
    )
    db.add(p)
    db.flush()
    return p


class TestStandingsTiedRanks:
    def test_tied_users_share_same_rank(self, db_session, test_tournament, test_teams):
        """Users with equal points must receive the same rank (1,2,2,4 not 1,2,3,4)."""
        team1, _ = test_teams

        u1 = _user(db_session, "alpha")
        u2 = _user(db_session, "beta")
        u3 = _user(db_session, "gamma")
        u4 = _user(db_session, "delta")
        league = _league(db_session, u1.id, u2.id, u3.id, u4.id)

        match = Match(
            tournament_id=test_tournament.id,
            team_1_id=test_teams[0].id,
            team_2_id=test_teams[1].id,
            start_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
            status=MatchStatus.COMPLETED,
            result_winner_id=team1.id,
        )
        db_session.add(match)
        db_session.flush()

        players1 = db_session.query(Player).filter_by(team_id=test_teams[0].id).all()
        players2 = db_session.query(Player).filter_by(team_id=test_teams[1].id).all()

        # Points: u1=100, u2=80, u3=80, u4=50
        _prediction_with_points(db_session, u1.id, match.id, team1.id, 100, players1, players2)
        _prediction_with_points(db_session, u2.id, match.id, team1.id, 80, players1, players2)
        _prediction_with_points(db_session, u3.id, match.id, team1.id, 80, players1, players2)
        _prediction_with_points(db_session, u4.id, match.id, team1.id, 50, players1, players2)
        db_session.commit()

        standings = _compute_standings(db_session, league.id)
        rank_map = dict(standings)  # user_id -> rank

        assert rank_map[u1.id] == 1          # sole leader
        assert rank_map[u2.id] == rank_map[u3.id] == 2  # tied at 2nd
        assert rank_map[u4.id] == 4          # skipped 3 because two people tied at 2

    def test_all_tied_all_rank_one(self, db_session, test_tournament, test_teams):
        """When everyone has the same points, everyone gets rank 1."""
        team1, _ = test_teams

        u1 = _user(db_session, "p1")
        u2 = _user(db_session, "p2")
        u3 = _user(db_session, "p3")
        league = _league(db_session, u1.id, u2.id, u3.id)

        match = Match(
            tournament_id=test_tournament.id,
            team_1_id=test_teams[0].id,
            team_2_id=test_teams[1].id,
            start_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
            status=MatchStatus.COMPLETED,
            result_winner_id=team1.id,
        )
        db_session.add(match)
        db_session.flush()

        players1 = db_session.query(Player).filter_by(team_id=test_teams[0].id).all()
        players2 = db_session.query(Player).filter_by(team_id=test_teams[1].id).all()

        for uid in (u1.id, u2.id, u3.id):
            _prediction_with_points(db_session, uid, match.id, team1.id, 60, players1, players2)
        db_session.commit()

        standings = _compute_standings(db_session, league.id)
        rank_map = dict(standings)

        assert rank_map[u1.id] == rank_map[u2.id] == rank_map[u3.id] == 1
