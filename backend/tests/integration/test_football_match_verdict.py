"""Match Verdict must work for football (scoreline + football hits, draws allowed).

Previously the verdict gated on result_winner_id (never set by the football sync)
and rendered cricket categories. These tests lock in the football path.
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.football_prediction import FootballPrediction
from app.models.football_match_result import FootballMatchResult
from app.models.tournament import Tournament
from app.models.team import Team
from app.models.player import Player
from app.models.league import League, LeagueMember
from app.services.match_verdict import get_match_verdict


@pytest.fixture
def fb_setup(db_session, test_user, test_user2):
    t = Tournament(
        name="WC Verdict", sport="football",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=60)).date(),
    )
    db_session.add(t)
    db_session.commit()

    team1 = Team(name="Brazil", short_name="BRA")
    team2 = Team(name="France", short_name="FRA")
    db_session.add_all([team1, team2])
    db_session.commit()
    fwd1 = [Player(name=f"BRA F{i}", team_id=team1.id, role="Forward") for i in range(3)]
    fwd2 = [Player(name=f"FRA F{i}", team_id=team2.id, role="Forward") for i in range(3)]
    db_session.add_all(fwd1 + fwd2)
    db_session.commit()

    league = League(name="L", invite_code="FBV123", owner_id=test_user.id)
    db_session.add(league)
    db_session.commit()
    db_session.add_all([
        LeagueMember(league_id=league.id, user_id=test_user.id),
        LeagueMember(league_id=league.id, user_id=test_user2.id),
    ])
    db_session.commit()
    return t, team1, team2, fwd1, league


def _scored_pred(db_session, user_id, match, picks, t1, t2, points):
    p = Prediction(user_id=user_id, match_id=match.id, points_earned=points, is_processed=True)
    p.football = FootballPrediction(
        team1_goals=t1, team2_goals=t2, advance_winner_id=None,
        player_pick_1_id=picks[0], player_pick_2_id=picks[1], player_pick_3_id=picks[2],
    )
    db_session.add(p)
    db_session.commit()


def _completed_match(db_session, t, team1, team2, t1g, t2g, winner_id):
    m = Match(
        tournament_id=t.id, team_1_id=team1.id, team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=3),
        status=MatchStatus.COMPLETED, stage="GROUP", result_winner_id=winner_id,
    )
    db_session.add(m)
    db_session.commit()
    db_session.add(FootballMatchResult(
        match_id=m.id, team1_goals_reg=t1g, team2_goals_reg=t2g,
        team1_goals_et=None, team2_goals_et=None, shootout_winner_id=None,
    ))
    db_session.commit()
    db_session.refresh(m)
    return m


class TestFootballVerdict:
    def test_decisive_match_football_shaped(self, db_session, test_user, test_user2, fb_setup):
        t, team1, team2, fwds, league = fb_setup
        m = _completed_match(db_session, t, team1, team2, 2, 1, team1.id)
        pick_ids = [p.id for p in fwds]
        # me: exact 2-1; friend: 0-0 (wrong outcome)
        _scored_pred(db_session, test_user.id, m, pick_ids, 2, 1, points=60)
        _scored_pred(db_session, test_user2.id, m, pick_ids, 0, 0, points=5)

        v = get_match_verdict(db_session, league.id, m.id, test_user.id)

        assert v is not None
        assert v.sport == "football"
        assert (v.team1_goals, v.team2_goals) == (2, 1)
        assert v.is_draw is False
        assert v.winning_team_short == "BRA"
        assert v.pom_player_name is None
        # top winner is me (exact scoreline)
        winner = v.winners[0]
        assert winner.hits.exact_score is True
        assert winner.hits.outcome is True

    def test_draw_still_produces_verdict(self, db_session, test_user, test_user2, fb_setup):
        t, team1, team2, fwds, league = fb_setup
        # draw → result_winner_id None (the football sync leaves it null)
        m = _completed_match(db_session, t, team1, team2, 1, 1, None)
        pick_ids = [p.id for p in fwds]
        _scored_pred(db_session, test_user.id, m, pick_ids, 1, 1, points=40)

        v = get_match_verdict(db_session, league.id, m.id, test_user.id)

        assert v is not None  # used to return None (gated on result_winner_id)
        assert v.sport == "football"
        assert v.is_draw is True
        assert v.winning_team_short is None
        assert (v.team1_goals, v.team2_goals) == (1, 1)
        assert v.winners[0].hits.exact_score is True
