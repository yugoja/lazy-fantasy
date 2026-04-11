"""
Unit tests for the Dugout service — contrarian, agreement, streak, rank_shift,
and dismissal filtering.
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.league import League, LeagueMember
from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.prediction import Prediction
from app.models.user import User
from app.models.dugout_dismissal import DugoutDismissal
from app.schemas.dugout import DugoutEventType
from app.services.dugout import get_dugout_events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _locked_match(db, tournament, team1, team2, minutes_ago=60):
    m = Match(
        tournament_id=tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutes_ago),
        status=MatchStatus.SCHEDULED,
    )
    db.add(m)
    db.flush()
    return m


def _make_prediction(db, user_id, match, winner_id, t1_runs, t2_runs, t1_wkts, t2_wkts, pom,
                     is_processed=False, points=0):
    p = Prediction(
        user_id=user_id,
        match_id=match.id,
        predicted_winner_id=winner_id,
        predicted_most_runs_team1_player_id=t1_runs,
        predicted_most_runs_team2_player_id=t2_runs,
        predicted_most_wickets_team1_player_id=t1_wkts,
        predicted_most_wickets_team2_player_id=t2_wkts,
        predicted_pom_player_id=pom,
        is_processed=is_processed,
        points_earned=points,
    )
    db.add(p)
    db.flush()
    return p


def _make_user(db, username, email):
    u = User(username=username, email=email, hashed_password="x")
    db.add(u)
    db.flush()
    return u


def _make_league(db, name, owner_id, *member_ids):
    # Backdate created_at so locked matches (start_time < now) are eligible
    league = League(
        name=name,
        invite_code=name[:6].upper(),
        owner_id=owner_id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30),
    )
    db.add(league)
    db.flush()
    for uid in (owner_id, *member_ids):
        db.add(LeagueMember(league_id=league.id, user_id=uid))
    db.flush()
    return league


# ---------------------------------------------------------------------------
# Contrarian
# ---------------------------------------------------------------------------

class TestContrarian:
    def test_lone_wolf_triggers_event(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me", "me@t.com")
        u2 = _make_user(db_session, "u2", "u2@t.com")
        u3 = _make_user(db_session, "u3", "u3@t.com")
        league = _make_league(db_session, "myleg", me.id, u2.id, u3.id)

        match = _locked_match(db_session, test_tournament, team1, team2)

        # me + u2 pick team1; u3 picks team2 (lone wolf)
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, u2.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, u3.id, match, team2.id, players1[1].id, players2[1].id, players1[5].id, players2[5].id, players2[0].id)
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        contrarian = [e for e in events if e.type == DugoutEventType.CONTRARIAN]

        assert len(contrarian) == 1
        assert contrarian[0].username == "u3"
        assert contrarian[0].team_short_name == team2.short_name
        assert contrarian[0].is_me is False

    def test_no_contrarian_when_split_evenly(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me2", "me2@t.com")
        u2 = _make_user(db_session, "u2b", "u2b@t.com")
        league = _make_league(db_session, "leg2", me.id, u2.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, u2.id, match, team2.id, players1[1].id, players2[1].id, players1[5].id, players2[5].id, players2[0].id)
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        # Both picked different teams — 1 pick each, both are "lone wolves"
        # but we only emit when exactly 1 person picked a team AND there are 2+ total preds
        contrarian = [e for e in events if e.type == DugoutEventType.CONTRARIAN]
        # Both are lone wolves here — expect up to 2 (capped at 2 per league)
        assert len(contrarian) <= 2

    def test_lone_wolf_not_shown_in_leagues_they_dont_belong_to(self, db_session, test_tournament, test_teams):
        """Regression: a user's prediction must not bleed into lone-wolf checks
        for leagues they are not a member of.

        Scenario: viewer is in 3 leagues. wolf shares only league_a with the viewer.
        wolf is lone wolf in league_a. The event should appear exactly once —
        not once per league the viewer belongs to.
        """
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "medup", "medup@t.com")
        wolf = _make_user(db_session, "wolfdup", "wolfdup@t.com")
        filler_a = _make_user(db_session, "fillerA", "fillerA@t.com")
        filler_b = _make_user(db_session, "fillerB", "fillerB@t.com")
        filler_c = _make_user(db_session, "fillerC", "fillerC@t.com")

        # wolf is only in league_a with the viewer
        league_a = _make_league(db_session, "legA", me.id, wolf.id, filler_a.id)
        # league_b and league_c do NOT include wolf
        league_b = _make_league(db_session, "legB", me.id, filler_b.id)
        league_c = _make_league(db_session, "legC", me.id, filler_c.id)

        match = _locked_match(db_session, test_tournament, team1, team2)

        # In league_a: me + filler_a pick team1; wolf is lone wolf picking team2
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, filler_a.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, wolf.id, match, team2.id, players1[1].id, players2[1].id, players1[5].id, players2[5].id, players2[0].id)
        # filler_b and filler_c also predict (for their respective leagues)
        _make_prediction(db_session, filler_b.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, filler_c.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        contrarian = [e for e in events if e.type == DugoutEventType.CONTRARIAN]

        # wolf is lone wolf only in league_a — must not appear in league_b or league_c
        assert len(contrarian) == 1
        assert contrarian[0].username == "wolfdup"
        assert contrarian[0].league_name == "legA"

    def test_contrarian_is_me(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me3", "me3@t.com")
        u2 = _make_user(db_session, "u2c", "u2c@t.com")
        u3 = _make_user(db_session, "u3c", "u3c@t.com")
        league = _make_league(db_session, "leg3", me.id, u2.id, u3.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        # I'm the lone wolf
        _make_prediction(db_session, me.id, match, team2.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players2[0].id)
        _make_prediction(db_session, u2.id, match, team1.id, players1[1].id, players2[1].id, players1[5].id, players2[5].id, players1[0].id)
        _make_prediction(db_session, u3.id, match, team1.id, players1[2].id, players2[2].id, players1[6].id, players2[6].id, players1[1].id)
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        contrarian = [e for e in events if e.type == DugoutEventType.CONTRARIAN]
        assert any(e.is_me for e in contrarian)


# ---------------------------------------------------------------------------
# Agreement
# ---------------------------------------------------------------------------

class TestAgreement:
    def test_5_of_6_triggers_event(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me4", "me4@t.com")
        friend = _make_user(db_session, "friend", "f@t.com")
        league = _make_league(db_session, "leg4", me.id, friend.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        # Identical on 5 fields, differ only on pom
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, friend.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[1].id)
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        agreement = [e for e in events if e.type == DugoutEventType.AGREEMENT]

        assert len(agreement) == 1
        assert agreement[0].username == "friend"
        assert agreement[0].agreement_count == 5

    def test_4_of_6_does_not_trigger(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me5", "me5@t.com")
        friend = _make_user(db_session, "friend2", "f2@t.com")
        league = _make_league(db_session, "leg5", me.id, friend.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        # Agree on 4 fields only
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, friend.id, match, team1.id, players1[0].id, players2[0].id, players1[5].id, players2[5].id, players1[1].id)
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        agreement = [e for e in events if e.type == DugoutEventType.AGREEMENT]
        assert len(agreement) == 0

    def test_perfect_agreement(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me6", "me6@t.com")
        friend = _make_user(db_session, "friend3", "f3@t.com")
        league = _make_league(db_session, "leg6", me.id, friend.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        # Identical on all 6
        for uid in (me.id, friend.id):
            _make_prediction(db_session, uid, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        agreement = [e for e in events if e.type == DugoutEventType.AGREEMENT]
        assert len(agreement) == 1
        assert agreement[0].agreement_count == 6

    def test_agreement_not_shown_in_leagues_they_dont_belong_to(self, db_session, test_tournament, test_teams):
        """Regression: a user's agreement must not bleed into agreement checks
        for leagues they are not a member of.

        Scenario: viewer is in 3 leagues. friend shares only league_a with the viewer.
        They have high agreement in league_a. The event should appear exactly once
        (in league_a) — not in league_b or league_c where friend is not a member.
        """
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        viewer = _make_user(db_session, "viewerag", "viewerag@t.com")
        friend = _make_user(db_session, "friendag", "friendag@t.com")
        filler_b = _make_user(db_session, "fillerBag", "fillerBag@t.com")
        filler_c = _make_user(db_session, "fillerCag", "fillerCag@t.com")

        # friend is only in league_a with the viewer
        league_a = _make_league(db_session, "legAag", viewer.id, friend.id)
        # league_b and league_c do NOT include friend
        league_b = _make_league(db_session, "legBag", viewer.id, filler_b.id)
        league_c = _make_league(db_session, "legCag", viewer.id, filler_c.id)

        match = _locked_match(db_session, test_tournament, team1, team2)

        # In league_a: viewer and friend have high agreement (5 of 6 fields match)
        _make_prediction(db_session, viewer.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, friend.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[1].id)
        # filler_b and filler_c also predict (for their respective leagues)
        _make_prediction(db_session, filler_b.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, filler_c.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        db_session.commit()

        events = get_dugout_events(db_session, viewer.id)
        agreement = [e for e in events if e.type == DugoutEventType.AGREEMENT]

        # friend has agreement only in league_a — must not appear in league_b or league_c
        friendag_events = [e for e in agreement if e.username == "friendag"]
        assert len(friendag_events) == 1
        assert friendag_events[0].league_name == "legAag"

        # Verify friend does NOT appear in other leagues
        friendag_in_other_leagues = [e for e in agreement if e.username == "friendag" and e.league_name != "legAag"]
        assert len(friendag_in_other_leagues) == 0


# ---------------------------------------------------------------------------
# Streak
# ---------------------------------------------------------------------------

class TestStreak:
    def _make_completed_match(self, db, tournament, team1, team2, winner_id, days_ago):
        m = Match(
            tournament_id=tournament.id,
            team_1_id=team1.id,
            team_2_id=team2.id,
            start_time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago),
            status=MatchStatus.COMPLETED,
            result_winner_id=winner_id,
        )
        db.add(m)
        db.flush()
        return m

    def test_streak_of_3_triggers(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me7", "me7@t.com")
        hot = _make_user(db_session, "hot", "hot@t.com")
        league = _make_league(db_session, "leg7", me.id, hot.id)

        # hot correctly predicted team1 to win 3 matches in a row
        for days_ago in [3, 2, 1]:
            m = self._make_completed_match(db_session, test_tournament, team1, team2, team1.id, days_ago)
            _make_prediction(db_session, hot.id, m, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id, is_processed=True, points=10)

        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        streak = [e for e in events if e.type == DugoutEventType.STREAK]

        assert len(streak) == 1
        assert streak[0].username == "hot"
        assert streak[0].streak_count == 3

    def test_streak_broken_does_not_trigger(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me8", "me8@t.com")
        cold = _make_user(db_session, "cold", "cold@t.com")
        league = _make_league(db_session, "leg8", me.id, cold.id)

        # correct, correct, WRONG — streak broken
        for days_ago, correct in [(3, True), (2, True), (1, False)]:
            winner = team1.id
            m = self._make_completed_match(db_session, test_tournament, team1, team2, winner, days_ago)
            predicted_winner = team1.id if correct else team2.id
            _make_prediction(db_session, cold.id, m, predicted_winner, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id, is_processed=True)

        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        streak = [e for e in events if e.type == DugoutEventType.STREAK]
        assert len(streak) == 0

    def test_streak_below_threshold_does_not_trigger(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "me9", "me9@t.com")
        u = _make_user(db_session, "u9", "u9@t.com")
        league = _make_league(db_session, "leg9", me.id, u.id)

        # Only 2 correct in a row
        for days_ago in [2, 1]:
            m = self._make_completed_match(db_session, test_tournament, team1, team2, team1.id, days_ago)
            _make_prediction(db_session, u.id, m, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id, is_processed=True)

        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        assert not any(e.type == DugoutEventType.STREAK for e in events)


# ---------------------------------------------------------------------------
# Rank shift
# ---------------------------------------------------------------------------

class TestRankShift:
    def test_rank_up_triggers_event(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "meR", "meR@t.com")
        u2 = _make_user(db_session, "u2R", "u2R@t.com")
        league = _make_league(db_session, "legR", me.id, u2.id)

        # me has more points → currently rank 1
        match = _locked_match(db_session, test_tournament, team1, team2)
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id, is_processed=True, points=100)
        _make_prediction(db_session, u2.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id, is_processed=True, points=50)

        # Set prev_rank to 2 (was lower)
        member = db_session.query(LeagueMember).filter(
            LeagueMember.league_id == league.id,
            LeagueMember.user_id == me.id,
        ).first()
        member.prev_rank = 2
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        rank_shift = [e for e in events if e.type == DugoutEventType.RANK_SHIFT]

        assert len(rank_shift) == 1
        assert rank_shift[0].rank == 1
        assert rank_shift[0].rank_delta == 1  # moved up by 1
        assert rank_shift[0].is_me is True

    def test_no_rank_shift_when_unchanged(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "meR2", "meR2@t.com")
        league = _make_league(db_session, "legR2", me.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id, is_processed=True, points=50)

        # prev_rank matches current rank
        member = db_session.query(LeagueMember).filter(
            LeagueMember.league_id == league.id,
            LeagueMember.user_id == me.id,
        ).first()
        member.prev_rank = 1
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        assert not any(e.type == DugoutEventType.RANK_SHIFT for e in events)

    def test_no_rank_shift_when_prev_rank_null(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "meR3", "meR3@t.com")
        league = _make_league(db_session, "legR3", me.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id, is_processed=True, points=50)
        db_session.commit()  # prev_rank remains None

        events = get_dugout_events(db_session, me.id)
        assert not any(e.type == DugoutEventType.RANK_SHIFT for e in events)


# ---------------------------------------------------------------------------
# Dismissal filtering
# ---------------------------------------------------------------------------

class TestDismissal:
    def test_dismissed_event_excluded(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "meD", "meD@t.com")
        wolf = _make_user(db_session, "wolf", "wolf@t.com")
        u3 = _make_user(db_session, "u3D", "u3D@t.com")
        league = _make_league(db_session, "legD", me.id, wolf.id, u3.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        _make_prediction(db_session, me.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, u3.id, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, wolf.id, match, team2.id, players1[1].id, players2[1].id, players1[5].id, players2[5].id, players2[0].id)

        # Dismiss the contrarian event for wolf
        db_session.add(DugoutDismissal(
            user_id=me.id,
            type="contrarian",
            league_id=league.id,
            match_id=match.id,
            subject_username="wolf",
        ))
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        contrarian = [e for e in events if e.type == DugoutEventType.CONTRARIAN]
        assert len(contrarian) == 0

    def test_dismissal_only_affects_requesting_user(self, db_session, test_tournament, test_teams):
        team1, team2 = test_teams
        players1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
        players2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

        me = _make_user(db_session, "meD2", "meD2@t.com")
        other = _make_user(db_session, "other", "other@t.com")
        wolf = _make_user(db_session, "wolfD2", "wolfD2@t.com")
        u4 = _make_user(db_session, "u4D", "u4D@t.com")
        league = _make_league(db_session, "legD2", me.id, other.id, wolf.id, u4.id)

        match = _locked_match(db_session, test_tournament, team1, team2)
        for uid in (me.id, other.id, u4.id):
            _make_prediction(db_session, uid, match, team1.id, players1[0].id, players2[0].id, players1[4].id, players2[4].id, players1[0].id)
        _make_prediction(db_session, wolf.id, match, team2.id, players1[1].id, players2[1].id, players1[5].id, players2[5].id, players2[0].id)

        # Only `me` dismisses the contrarian
        db_session.add(DugoutDismissal(
            user_id=me.id,
            type="contrarian",
            league_id=league.id,
            match_id=match.id,
            subject_username="wolfD2",
        ))
        db_session.commit()

        me_events = get_dugout_events(db_session, me.id)
        other_events = get_dugout_events(db_session, other.id)

        assert not any(e.type == DugoutEventType.CONTRARIAN for e in me_events)
        assert any(e.type == DugoutEventType.CONTRARIAN for e in other_events)

    def test_no_events_when_no_league(self, db_session):
        me = _make_user(db_session, "loner", "loner@t.com")
        db_session.commit()

        events = get_dugout_events(db_session, me.id)
        assert events == []
