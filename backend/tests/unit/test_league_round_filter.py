"""
Unit tests for round-based leaderboard filtering.

RED phase: all tests reference APIs / fields that don't exist yet.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.match import Match, MatchStatus
from app.models.league import League, LeagueMember
from app.models.prediction import Prediction
from app.models.user import User
from app.models.tournament import Tournament
from app.models.team import Team
from app.services.league import _round_filter_clause, get_league_leaderboard
from app.services.auth import get_password_hash

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _round_filter_clause
# ---------------------------------------------------------------------------

class TestRoundFilterClause:
    def test_group_1_returns_stage_and_round(self):
        clauses = _round_filter_clause("GROUP_1")
        assert len(clauses) == 2

    def test_group_2_has_correct_round_number(self):
        clauses = _round_filter_clause("GROUP_2")
        # Second clause should constrain group_round == 2
        assert len(clauses) == 2

    def test_group_3_has_correct_round_number(self):
        clauses = _round_filter_clause("GROUP_3")
        assert len(clauses) == 2

    def test_knockout_stage_returns_single_clause(self):
        for stage in ("R32", "R16", "QF", "SF", "THIRD", "FINAL"):
            clauses = _round_filter_clause(stage)
            assert len(clauses) == 1, f"Expected 1 clause for {stage}"


# ---------------------------------------------------------------------------
# get_league_leaderboard — round_key behaviour
# ---------------------------------------------------------------------------

@pytest.fixture
def round_scenario(db_session):
    """
    League with 2 users, 3 GROUP matches (rounds 1-2-3) + 1 QF match.
    Each user has scored predictions on every match (points_earned set directly).
    """
    # Tournament
    tournament = Tournament(
        name="WC 2026",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=60)).date(),
    )
    db_session.add(tournament)
    db_session.flush()

    # Teams
    t1 = Team(name="Alpha", short_name="ALP")
    t2 = Team(name="Beta", short_name="BET")
    t3 = Team(name="Gamma", short_name="GAM")
    db_session.add_all([t1, t2, t3])
    db_session.flush()

    # League (created before matches)
    owner = User(username="owner_r", email="owner_r@test.com",
                 hashed_password=get_password_hash("x"))
    user2 = User(username="player_r", email="player_r@test.com",
                 hashed_password=get_password_hash("x"))
    db_session.add_all([owner, user2])
    db_session.flush()

    league = League(name="Round League", invite_code="RND001", owner_id=owner.id)
    db_session.add(league)
    db_session.flush()
    db_session.add_all([
        LeagueMember(league_id=league.id, user_id=owner.id),
        LeagueMember(league_id=league.id, user_id=user2.id),
    ])
    db_session.flush()

    base_time = league.created_at + timedelta(hours=1)

    # GROUP matches: group_round 1, 2, 3
    m_g1 = Match(tournament_id=tournament.id, team_1_id=t1.id, team_2_id=t2.id,
                 start_time=base_time, status=MatchStatus.COMPLETED,
                 stage="GROUP", group_round=1)
    m_g2 = Match(tournament_id=tournament.id, team_1_id=t1.id, team_2_id=t3.id,
                 start_time=base_time + timedelta(days=5), status=MatchStatus.COMPLETED,
                 stage="GROUP", group_round=2)
    m_g3 = Match(tournament_id=tournament.id, team_1_id=t2.id, team_2_id=t3.id,
                 start_time=base_time + timedelta(days=10), status=MatchStatus.COMPLETED,
                 stage="GROUP", group_round=3)
    # QF match
    m_qf = Match(tournament_id=tournament.id, team_1_id=t1.id, team_2_id=t2.id,
                 start_time=base_time + timedelta(days=20), status=MatchStatus.COMPLETED,
                 stage="QF", group_round=None)

    db_session.add_all([m_g1, m_g2, m_g3, m_qf])
    db_session.flush()

    # Predictions: owner scores 10 per match, user2 scores 5 per match
    for match, owner_pts, u2_pts in [
        (m_g1, 10, 5),
        (m_g2, 10, 5),
        (m_g3, 10, 5),
        (m_qf, 20, 10),  # knockout multiplier already baked in
    ]:
        db_session.add(Prediction(
            user_id=owner.id, match_id=match.id,
            points_earned=owner_pts, is_processed=True,
        ))
        db_session.add(Prediction(
            user_id=user2.id, match_id=match.id,
            points_earned=u2_pts, is_processed=True,
        ))

    db_session.commit()

    return {"league": league, "owner": owner, "user2": user2,
            "m_g1": m_g1, "m_g2": m_g2, "m_g3": m_g3, "m_qf": m_qf}


class TestLeaderboardRoundFilter:
    def test_no_round_key_returns_cumulative(self, db_session, round_scenario):
        """Without round_key the leaderboard sums all matches."""
        league_id = round_scenario["league"].id
        rows = get_league_leaderboard(db_session, league_id)
        # owner: 10+10+10+20 = 50, user2: 5+5+5+10 = 25
        pts_map = {r[0]: r[3] for r in rows}
        assert pts_map[round_scenario["owner"].id] == 50
        assert pts_map[round_scenario["user2"].id] == 25

    def test_group_1_filter_only_counts_round_1(self, db_session, round_scenario):
        league_id = round_scenario["league"].id
        rows = get_league_leaderboard(db_session, league_id, round_key="GROUP_1")
        pts_map = {r[0]: r[3] for r in rows}
        assert pts_map[round_scenario["owner"].id] == 10
        assert pts_map[round_scenario["user2"].id] == 5

    def test_group_2_filter_only_counts_round_2(self, db_session, round_scenario):
        league_id = round_scenario["league"].id
        rows = get_league_leaderboard(db_session, league_id, round_key="GROUP_2")
        pts_map = {r[0]: r[3] for r in rows}
        assert pts_map[round_scenario["owner"].id] == 10
        assert pts_map[round_scenario["user2"].id] == 5

    def test_qf_filter_only_counts_qf(self, db_session, round_scenario):
        league_id = round_scenario["league"].id
        rows = get_league_leaderboard(db_session, league_id, round_key="QF")
        pts_map = {r[0]: r[3] for r in rows}
        assert pts_map[round_scenario["owner"].id] == 20
        assert pts_map[round_scenario["user2"].id] == 10

    def test_round_key_skips_tournament_pick_points(self, db_session, round_scenario):
        """When round_key is set, tp_points must NOT be added."""
        from app.models.tournament_pick import TournamentPick
        league_id = round_scenario["league"].id
        owner_id = round_scenario["owner"].id
        league = round_scenario["league"]

        # Add a tournament pick for the owner
        tp = TournamentPick(
            user_id=owner_id,
            tournament_id=round_scenario["m_g1"].tournament_id,
            points_earned=100,
            is_processed=True,
        )
        db_session.add(tp)
        db_session.commit()

        # With round_key: tp_points should NOT be included
        rows = get_league_leaderboard(db_session, league_id, round_key="GROUP_1")
        pts_map = {r[0]: r[3] for r in rows}
        assert pts_map[owner_id] == 10  # not 110

    def test_round_key_sets_prev_rank_none(self, db_session, round_scenario):
        """When round_key is set, prev_rank for all entries should be None."""
        league_id = round_scenario["league"].id
        # Give someone a prev_rank
        member = db_session.query(LeagueMember).filter(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == round_scenario["owner"].id
        ).first()
        member.prev_rank = 1
        db_session.commit()

        rows = get_league_leaderboard(db_session, league_id, round_key="GROUP_1")
        # All prev_ranks should be None when round_key is active
        for row in rows:
            prev_rank = row[4]
            assert prev_rank is None, f"Expected prev_rank=None, got {prev_rank}"

    def test_unknown_round_key_not_handled_by_service(self, db_session, round_scenario):
        """Service doesn't validate round keys — that's the router's job."""
        pass


# ---------------------------------------------------------------------------
# _get_available_rounds
# ---------------------------------------------------------------------------

from app.services.league import _get_available_rounds
from app.models.match import MatchStatus


class TestGetAvailableRounds:
    def test_returns_only_completed_rounds(self, db_session, round_scenario):
        """Only rounds with at least one COMPLETED match should be returned."""
        league = round_scenario["league"]
        rounds = _get_available_rounds(db_session, league.created_at)
        # Fixture has completed GROUP_1, GROUP_2, GROUP_3, QF
        assert "GROUP_1" in rounds
        assert "GROUP_2" in rounds
        assert "GROUP_3" in rounds
        assert "QF" in rounds

    def test_does_not_include_stages_without_completed_matches(self, db_session, round_scenario):
        league = round_scenario["league"]
        rounds = _get_available_rounds(db_session, league.created_at)
        # No R16, SF, FINAL, THIRD, R32 in the fixture
        for absent in ("R16", "SF", "FINAL", "THIRD", "R32"):
            assert absent not in rounds, f"{absent} should not appear"

    def test_canonical_sort_order(self, db_session, round_scenario):
        league = round_scenario["league"]
        rounds = _get_available_rounds(db_session, league.created_at)
        # GROUP rounds must come before QF
        group_idx = [i for i, r in enumerate(rounds) if r.startswith("GROUP_")]
        qf_idx = rounds.index("QF")
        assert all(i < qf_idx for i in group_idx)

    def test_returns_empty_when_no_completed_matches(self, db_session):
        from datetime import datetime, timezone
        rounds = _get_available_rounds(db_session, datetime.now(timezone.utc))
        assert rounds == []

    def test_does_not_include_scheduled_matches(self, db_session, round_scenario):
        """A SCHEDULED match should not count as an available round."""
        from app.models.tournament import Tournament
        from app.models.team import Team
        from datetime import datetime, timedelta, timezone

        league = round_scenario["league"]
        # Add a scheduled SF match
        t = db_session.query(Tournament).first()
        teams = db_session.query(Team).all()
        sf_match = Match(
            tournament_id=t.id, team_1_id=teams[0].id, team_2_id=teams[1].id,
            start_time=league.created_at + timedelta(days=30),
            status=MatchStatus.SCHEDULED, stage="SF", group_round=None,
        )
        db_session.add(sf_match)
        db_session.commit()

        rounds = _get_available_rounds(db_session, league.created_at)
        assert "SF" not in rounds
