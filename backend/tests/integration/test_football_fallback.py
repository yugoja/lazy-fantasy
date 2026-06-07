"""
Integration tests for the M2 football fallback job.

TDD — written before the implementation. These tests drive the design of
app.services.fallback_job.run_football_fallback.

Every test uses a real (testcontainer) Postgres DB via the shared db_session
fixture. PredictionInputs are built with real DB player IDs so FK constraints
are satisfied.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.league import League, LeagueMember
from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.prediction import Prediction
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import User
from app.services.auth import get_password_hash
from app.services.autopick import (
    DataQuality,
    PredictionInputs,
    ScorelineProb,
    ScoredPlayer,
)
from app.services.fallback_job import FallbackSummary, run_football_fallback

pytestmark = pytest.mark.integration

# ── Helpers ───────────────────────────────────────────────────────────────────

_ROLE_MAP = {
    "Goalkeeper": "GK", "Defender": "DEF", "Midfielder": "MID", "Forward": "FWD",
}


def _role_to_pos(role: str) -> str:
    return _ROLE_MAP.get(role, "MID")


def _make_inputs(match: Match, players: list[Player]) -> PredictionInputs:
    """Build a PredictionInputs using real DB player IDs."""
    scored = tuple(
        ScoredPlayer(
            player_id=str(p.id),
            team_id=str(p.team_id),
            position=_role_to_pos(p.role),  # type: ignore[arg-type]
            expected_points=float(idx + 1),  # distinct scores so picks vary
            floor="mid",
            availability="starter",
        )
        for idx, p in enumerate(players)
    )
    return PredictionInputs(
        match_id=str(match.id),
        home_team_id=str(match.team_1_id),
        away_team_id=str(match.team_2_id),
        players=scored,
        scorelines=(ScorelineProb(1, 0, 0.5), ScorelineProb(1, 1, 0.3), ScorelineProb(2, 1, 0.2)),
        data_quality=DataQuality(lineups_confirmed=False, odds_source="fallback"),
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def wc_tournament(db_session):
    t = Tournament(
        name="WC 2026",
        sport="football",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=60)).date(),
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def football_teams(db_session):
    fra = Team(name="France", short_name="FRA")
    bra = Team(name="Brazil", short_name="BRA")
    db_session.add_all([fra, bra])
    db_session.commit()

    roles = ["Goalkeeper", "Defender", "Defender", "Defender", "Defender",
             "Midfielder", "Midfielder", "Midfielder", "Forward", "Forward", "Forward"]
    for role in roles:
        db_session.add(Player(name=f"FRA {role}", team_id=fra.id, role=role))
    for role in roles:
        db_session.add(Player(name=f"BRA {role}", team_id=bra.id, role=role))

    db_session.commit()
    db_session.refresh(fra)
    db_session.refresh(bra)
    return fra, bra


@pytest.fixture
def upcoming_match(db_session, wc_tournament, football_teams):
    fra, bra = football_teams
    match = Match(
        tournament_id=wc_tournament.id,
        team_1_id=fra.id,
        team_2_id=bra.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        status=MatchStatus.SCHEDULED,
        stage="GROUP",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


def _make_user(db_session, suffix: str) -> User:
    u = User(
        username=f"fb_user_{suffix}",
        email=f"fb_{suffix}@test.com",
        hashed_password=get_password_hash("pw"),
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _make_football_league(db_session, owner: User, suffix: str) -> League:
    league = League(name=f"FB League {suffix}", invite_code=f"FB{suffix}", owner_id=owner.id, sport="football")
    db_session.add(league)
    db_session.commit()
    db_session.add(LeagueMember(league_id=league.id, user_id=owner.id))
    db_session.commit()
    db_session.refresh(league)
    return league


def _make_cricket_league(db_session, owner: User, suffix: str) -> League:
    league = League(name=f"CR League {suffix}", invite_code=f"CR{suffix}", owner_id=owner.id, sport="cricket")
    db_session.add(league)
    db_session.commit()
    db_session.add(LeagueMember(league_id=league.id, user_id=owner.id))
    db_session.commit()
    db_session.refresh(league)
    return league


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestFallbackFillsMissingUsers:
    def test_fills_users_in_football_league_with_no_prediction(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        user1 = _make_user(db_session, "a1")
        user2 = _make_user(db_session, "a2")
        league = _make_football_league(db_session, user1, "A1")
        db_session.add(LeagueMember(league_id=league.id, user_id=user2.id))
        db_session.commit()

        summary = run_football_fallback(db_session, upcoming_match, inputs)

        assert summary.filled == 2
        assert summary.skipped == 0
        assert set(summary.user_ids_filled) == {user1.id, user2.id}

    def test_creates_prediction_and_football_child_rows(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        user = _make_user(db_session, "b1")
        _make_football_league(db_session, user, "B1")

        run_football_fallback(db_session, upcoming_match, inputs)

        prediction = (
            db_session.query(Prediction)
            .filter_by(user_id=user.id, match_id=upcoming_match.id)
            .first()
        )
        assert prediction is not None
        assert prediction.football is not None
        fp = prediction.football
        assert fp.player_pick_1_id is not None
        assert fp.player_pick_2_id is not None
        assert fp.player_pick_3_id is not None
        # All 3 picks must be distinct
        assert len({fp.player_pick_1_id, fp.player_pick_2_id, fp.player_pick_3_id}) == 3


class TestFallbackSkipsExistingPredictions:
    def test_skips_users_who_already_predicted(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        user = _make_user(db_session, "c1")
        _make_football_league(db_session, user, "C1")

        # Pre-submit a prediction for this user
        fra_players = [p for p in players if p.team_id == fra.id]
        bra_players = [p for p in players if p.team_id == bra.id]
        existing = Prediction(user_id=user.id, match_id=upcoming_match.id, points_earned=0, is_processed=False)
        from app.models.football_prediction import FootballPrediction
        existing.football = FootballPrediction(
            team1_goals=2, team2_goals=1, advance_winner_id=None,
            player_pick_1_id=fra_players[8].id,
            player_pick_2_id=fra_players[9].id,
            player_pick_3_id=bra_players[8].id,
        )
        db_session.add(existing)
        db_session.commit()

        summary = run_football_fallback(db_session, upcoming_match, inputs)

        assert summary.skipped == 1
        assert summary.filled == 0
        # Original prediction must be unchanged
        db_session.refresh(existing)
        assert existing.football.team1_goals == 2

    def test_mixed_some_have_predictions(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        user_with = _make_user(db_session, "d1")
        user_without = _make_user(db_session, "d2")
        league = _make_football_league(db_session, user_with, "D1")
        db_session.add(LeagueMember(league_id=league.id, user_id=user_without.id))
        db_session.commit()

        fra_players = [p for p in players if p.team_id == fra.id]
        bra_players = [p for p in players if p.team_id == bra.id]
        existing = Prediction(user_id=user_with.id, match_id=upcoming_match.id, points_earned=0, is_processed=False)
        from app.models.football_prediction import FootballPrediction
        existing.football = FootballPrediction(
            team1_goals=1, team2_goals=1, advance_winner_id=None,
            player_pick_1_id=fra_players[8].id,
            player_pick_2_id=fra_players[9].id,
            player_pick_3_id=bra_players[8].id,
        )
        db_session.add(existing)
        db_session.commit()

        summary = run_football_fallback(db_session, upcoming_match, inputs)

        assert summary.filled == 1
        assert summary.skipped == 1
        assert summary.user_ids_filled == [user_without.id]


class TestFallbackSportFilter:
    def test_ignores_cricket_league_members(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        cricket_user = _make_user(db_session, "e1")
        _make_cricket_league(db_session, cricket_user, "E1")

        summary = run_football_fallback(db_session, upcoming_match, inputs)

        assert summary.filled == 0

    def test_fills_football_but_not_cricket_members(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        fb_user = _make_user(db_session, "f1")
        cr_user = _make_user(db_session, "f2")
        _make_football_league(db_session, fb_user, "F1")
        _make_cricket_league(db_session, cr_user, "F2")

        summary = run_football_fallback(db_session, upcoming_match, inputs)

        assert summary.filled == 1
        assert summary.user_ids_filled == [fb_user.id]


class TestFallbackIdempotency:
    def test_second_run_creates_no_new_predictions(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        user = _make_user(db_session, "g1")
        _make_football_league(db_session, user, "G1")

        first = run_football_fallback(db_session, upcoming_match, inputs)
        second = run_football_fallback(db_session, upcoming_match, inputs)

        assert first.filled == 1
        assert second.filled == 0
        assert second.skipped == 1

        count = (
            db_session.query(Prediction)
            .filter_by(user_id=user.id, match_id=upcoming_match.id)
            .count()
        )
        assert count == 1


class TestFallbackDeterminism:
    def test_same_user_same_match_produces_same_picks(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        user = _make_user(db_session, "h1")
        _make_football_league(db_session, user, "H1")

        run_football_fallback(db_session, upcoming_match, inputs)

        fp1 = (
            db_session.query(Prediction)
            .filter_by(user_id=user.id, match_id=upcoming_match.id)
            .first()
            .football
        )
        picks1 = (fp1.player_pick_1_id, fp1.player_pick_2_id, fp1.player_pick_3_id)

        # Derive what the engine would produce deterministically
        from app.services.autopick import auto_pick, Identity, DEFAULT_STRATEGY
        result = auto_pick(inputs, DEFAULT_STRATEGY, Identity(str(user.id), str(upcoming_match.id)))
        expected_ids = tuple(int(pid) for pid in result.player_ids)

        assert set(picks1) == set(expected_ids)


class TestFallbackSourceField:
    def test_autopick_predictions_have_source_autopick(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        user = _make_user(db_session, "i1")
        _make_football_league(db_session, user, "I1")

        run_football_fallback(db_session, upcoming_match, inputs)

        fp = (
            db_session.query(Prediction)
            .filter_by(user_id=user.id, match_id=upcoming_match.id)
            .first()
            .football
        )
        assert fp.source == "autopick"

    def test_manual_predictions_have_source_user(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()

        user = _make_user(db_session, "j1")
        fra_players = [p for p in players if p.team_id == fra.id]
        bra_players = [p for p in players if p.team_id == bra.id]

        from app.models.football_prediction import FootballPrediction
        pred = Prediction(user_id=user.id, match_id=upcoming_match.id, points_earned=0, is_processed=False)
        pred.football = FootballPrediction(
            team1_goals=1, team2_goals=0, advance_winner_id=None,
            player_pick_1_id=fra_players[8].id,
            player_pick_2_id=fra_players[9].id,
            player_pick_3_id=bra_players[8].id,
        )
        db_session.add(pred)
        db_session.commit()

        db_session.refresh(pred)
        # default source should be 'user'
        assert pred.football.source == "user"


class TestFallbackPicksValidPlayers:
    def test_all_picks_belong_to_match_teams(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)
        valid_player_ids = {p.id for p in players}

        users = [_make_user(db_session, f"k{i}") for i in range(5)]
        league = _make_football_league(db_session, users[0], "K1")
        for u in users[1:]:
            db_session.add(LeagueMember(league_id=league.id, user_id=u.id))
        db_session.commit()

        run_football_fallback(db_session, upcoming_match, inputs)

        for u in users:
            fp = (
                db_session.query(Prediction)
                .filter_by(user_id=u.id, match_id=upcoming_match.id)
                .first()
                .football
            )
            for pid in (fp.player_pick_1_id, fp.player_pick_2_id, fp.player_pick_3_id):
                assert pid in valid_player_ids


class TestFallbackEdgeCases:
    def test_no_football_league_members(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        summary = run_football_fallback(db_session, upcoming_match, inputs)

        assert summary.filled == 0
        assert summary.skipped == 0

    def test_returns_fallback_summary_dataclass(
        self, db_session, upcoming_match, football_teams
    ):
        fra, bra = football_teams
        players = db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
        inputs = _make_inputs(upcoming_match, players)

        summary = run_football_fallback(db_session, upcoming_match, inputs)

        assert isinstance(summary, FallbackSummary)
        assert isinstance(summary.filled, int)
        assert isinstance(summary.skipped, int)
        assert isinstance(summary.user_ids_filled, list)
