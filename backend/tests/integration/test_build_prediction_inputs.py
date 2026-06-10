"""
TDD tests for build_prediction_inputs_from_db.

Drives the implementation of the function that converts a Match + its DB
players into the PredictionInputs the auto-pick engine expects.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.services.fallback_job import build_prediction_inputs_from_db

pytestmark = pytest.mark.integration


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def wc_tournament(db_session):
    t = Tournament(
        name="WC 2026", sport="football",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=60)).date(),
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def football_match(db_session, wc_tournament):
    fra = Team(name="France", short_name="FRA", fifa_ranking=1)
    bra = Team(name="Brazil", short_name="BRA", fifa_ranking=15)
    db_session.add_all([fra, bra])
    db_session.commit()

    roles = ["Goalkeeper", "Defender", "Defender", "Defender", "Defender",
             "Midfielder", "Midfielder", "Midfielder", "Forward", "Forward", "Forward"]
    for role in roles:
        db_session.add(Player(name=f"FRA {role}", team_id=fra.id, role=role))
    for role in roles:
        db_session.add(Player(name=f"BRA {role}", team_id=bra.id, role=role))
    db_session.commit()

    match = Match(
        tournament_id=wc_tournament.id,
        team_1_id=fra.id, team_2_id=bra.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        status=MatchStatus.SCHEDULED, stage="GROUP",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    db_session.refresh(fra)
    db_session.refresh(bra)
    return match, fra, bra


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_returns_prediction_inputs(db_session, football_match):
    match, fra, bra = football_match
    from app.services.autopick import PredictionInputs
    inputs = build_prediction_inputs_from_db(db_session, match)
    assert isinstance(inputs, PredictionInputs)


def test_match_id_and_team_ids(db_session, football_match):
    match, fra, bra = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    assert inputs.match_id == str(match.id)
    assert inputs.home_team_id == str(fra.id)
    assert inputs.away_team_id == str(bra.id)


def test_includes_all_players_from_both_teams(db_session, football_match):
    match, fra, bra = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    db_player_ids = {
        str(p.id)
        for p in db_session.query(Player).filter(
            Player.team_id.in_([fra.id, bra.id])
        ).all()
    }
    input_player_ids = {p.player_id for p in inputs.players}
    assert input_player_ids == db_player_ids


def test_no_duplicate_player_ids(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    ids = [p.player_id for p in inputs.players]
    assert len(ids) == len(set(ids))


def test_role_mapping_goalkeeper(db_session, football_match):
    match, fra, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    gk_db_ids = {
        str(p.id)
        for p in db_session.query(Player).filter(
            Player.team_id == fra.id, Player.role == "Goalkeeper"
        ).all()
    }
    gk_inputs = [p for p in inputs.players if p.player_id in gk_db_ids]
    assert all(p.position == "GK" for p in gk_inputs)


def test_role_mapping_outfield(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    role_map = {"Defender": "DEF", "Midfielder": "MID", "Forward": "FWD"}
    all_players = db_session.query(Player).filter(
        Player.team_id.in_([
            int(inputs.home_team_id), int(inputs.away_team_id)
        ])
    ).all()
    db_role = {str(p.id): p.role for p in all_players}
    for sp in inputs.players:
        expected = {"Goalkeeper": "GK", "Defender": "DEF", "Midfielder": "MID", "Forward": "FWD"}.get(db_role[sp.player_id])
        if expected:
            assert sp.position == expected


def test_expected_points_are_positive(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    assert all(p.expected_points > 0 for p in inputs.players)


def test_forwards_have_higher_xp_than_goalkeepers(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    fwd_xp = [p.expected_points for p in inputs.players if p.position == "FWD"]
    gk_xp = [p.expected_points for p in inputs.players if p.position == "GK"]
    assert min(fwd_xp) > max(gk_xp)


def test_all_players_have_valid_floor(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    valid_floors = {"high", "mid", "low"}
    assert all(p.floor in valid_floors for p in inputs.players)


def test_all_players_have_valid_availability(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    valid = {"starter", "rotation", "doubt", "out"}
    assert all(p.availability in valid for p in inputs.players)


def test_scorelines_not_empty(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    assert len(inputs.scorelines) > 0


def test_scorelines_probabilities_sum_to_approx_1(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    total = sum(s.p for s in inputs.scorelines)
    assert 0.90 <= total <= 1.10


def test_scoreline_probabilities_are_positive(db_session, football_match):
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    assert all(s.p > 0 for s in inputs.scorelines)


def test_at_least_3_eligible_players_for_safe_strategy(db_session, football_match):
    """safe strategy needs ≥3 high-floor players — verify builder provides them."""
    match, _, _ = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    high_floor = [p for p in inputs.players if p.floor == "high" and p.availability != "out"]
    assert len(high_floor) >= 3


def test_stronger_team_players_get_high_floor(db_session, football_match):
    """France (#1) vs Brazil (#15): France players should be high, Brazil mid."""
    match, fra, bra = football_match
    inputs = build_prediction_inputs_from_db(db_session, match)
    fra_floors = {p.floor for p in inputs.players if p.team_id == str(fra.id)}
    bra_floors = {p.floor for p in inputs.players if p.team_id == str(bra.id)}
    assert fra_floors == {"high"}
    assert bra_floors == {"mid"}


def test_rank_adjusted_lambdas_favour_stronger_home_team(db_session, football_match):
    """Stronger team (#1 vs #15) should have higher lambda than the neutral base."""
    from app.services.fallback_job import BASE_LAMBDA, _rank_adjusted_lambdas
    home_lam, away_lam = _rank_adjusted_lambdas(home_rank=1, away_rank=15)
    assert home_lam > BASE_LAMBDA
    assert away_lam < BASE_LAMBDA


def test_equal_ranked_teams_use_default_lambdas(db_session):
    """Equal/unknown rankings fall back to equal BASE_LAMBDA on both sides (neutral venue)."""
    from app.services.fallback_job import BASE_LAMBDA, _rank_adjusted_lambdas
    home_lam, away_lam = _rank_adjusted_lambdas(home_rank=None, away_rank=None)
    assert home_lam == pytest.approx(BASE_LAMBDA)
    assert away_lam == pytest.approx(BASE_LAMBDA)
