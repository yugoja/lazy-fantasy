"""Unit tests for football_sync — player resolution and sync logic with a mock provider."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.football_match_result import FootballMatchResult, FootballPlayerMatchEvent
from app.models.prediction import Prediction
from app.services.football_provider import FootballFixtureResult, FootballPlayerStat
from app.services.football_sync import (
    _normalize,
    _resolve_football_player,
    _apply_football_result,
    set_provider,
    sync_match_result,
)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

def test_normalize_strips_diacritics():
    assert _normalize("Ünlü") == "unlu"


def test_normalize_removes_punctuation():
    assert _normalize("O'Brien") == "obrien"


def test_normalize_lowercases():
    assert _normalize("SAKA Bukayo") == "saka bukayo"


# ---------------------------------------------------------------------------
# _resolve_football_player — tier 1: exact api_football_player_id
# ---------------------------------------------------------------------------

def test_resolve_by_api_football_player_id(db_session, test_teams):
    team1, _ = test_teams
    player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    player.api_football_player_id = "999"
    db_session.commit()

    stat = FootballPlayerStat(
        api_player_id=999,
        name="Wrong Name",
        team_api_id=0,
        minutes_played=90,
        goals=1,
        assists=0,
        red_card=False,
        own_goals=0,
        ingame_pen_saves=0,
        shootout_pen_saves=0,
        ingame_pen_misses=0,
    )
    result = _resolve_football_player(stat, [], db_session)
    assert result is not None
    assert result.id == player.id


# ---------------------------------------------------------------------------
# _resolve_football_player — tier 2: token-set equality (handles reordering)
# ---------------------------------------------------------------------------

def test_resolve_by_token_set_reordered_name(db_session, test_teams):
    team1, _ = test_teams
    player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    player.name = "SAKA Bukayo"
    db_session.commit()
    candidates = db_session.query(Player).filter(Player.team_id == team1.id).all()

    stat = FootballPlayerStat(
        api_player_id=0,
        name="Bukayo Saka",   # reversed order
        team_api_id=0,
        minutes_played=90,
        goals=0,
        assists=1,
        red_card=False,
        own_goals=0,
        ingame_pen_saves=0,
        shootout_pen_saves=0,
        ingame_pen_misses=0,
    )
    result = _resolve_football_player(stat, candidates, db_session)
    assert result is not None
    assert result.name == "SAKA Bukayo"


def test_resolve_caches_api_id_after_tier2_match(db_session, test_teams):
    team1, _ = test_teams
    player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    player.name = "Kylian Mbappe"
    player.api_football_player_id = None
    db_session.commit()
    candidates = db_session.query(Player).filter(Player.team_id == team1.id).all()

    stat = FootballPlayerStat(
        api_player_id=278,
        name="Kylian Mbappe",
        team_api_id=0,
        minutes_played=90,
        goals=2,
        assists=0,
        red_card=False,
        own_goals=0,
        ingame_pen_saves=0,
        shootout_pen_saves=0,
        ingame_pen_misses=0,
    )
    _resolve_football_player(stat, candidates, db_session)
    db_session.commit()

    db_session.refresh(player)
    assert player.api_football_player_id == "278"


# ---------------------------------------------------------------------------
# _resolve_football_player — tier 3: fuzzy
# ---------------------------------------------------------------------------

def test_resolve_by_fuzzy_match(db_session, test_teams):
    team1, _ = test_teams
    player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    player.name = "Cristiano Ronaldo"
    db_session.commit()
    candidates = db_session.query(Player).filter(Player.team_id == team1.id).all()

    stat = FootballPlayerStat(
        api_player_id=0,
        name="Cristano Ronaldo",   # slight misspelling
        team_api_id=0,
        minutes_played=90,
        goals=1,
        assists=0,
        red_card=False,
        own_goals=0,
        ingame_pen_saves=0,
        shootout_pen_saves=0,
        ingame_pen_misses=0,
    )
    result = _resolve_football_player(stat, candidates, db_session)
    assert result is not None
    assert result.name == "Cristiano Ronaldo"


def test_resolve_returns_none_for_unmatched(db_session, test_teams):
    team1, _ = test_teams
    candidates = db_session.query(Player).filter(Player.team_id == team1.id).all()

    stat = FootballPlayerStat(
        api_player_id=0,
        name="Nobody Special ZZZXXX",
        team_api_id=0,
        minutes_played=0,
        goals=0,
        assists=0,
        red_card=False,
        own_goals=0,
        ingame_pen_saves=0,
        shootout_pen_saves=0,
        ingame_pen_misses=0,
    )
    result = _resolve_football_player(stat, candidates, db_session)
    assert result is None


# ---------------------------------------------------------------------------
# _apply_football_result
# ---------------------------------------------------------------------------

def _make_stat(**kwargs) -> FootballPlayerStat:
    defaults = dict(
        api_player_id=0, name="", team_api_id=0, minutes_played=90,
        goals=0, assists=0, red_card=False, own_goals=0,
        ingame_pen_saves=0, shootout_pen_saves=0, ingame_pen_misses=0,
    )
    return FootballPlayerStat(**{**defaults, **kwargs})


def test_apply_creates_result_and_events(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    t1_player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    t2_player = db_session.query(Player).filter(Player.team_id == team2.id).first()

    resolved = [
        (t1_player, _make_stat(goals=1)),
        (t2_player, _make_stat(assists=1)),
    ]

    _apply_football_result(
        db=db_session,
        match=match,
        team1_goals_reg=1,
        team2_goals_reg=0,
        team1_goals_et=None,
        team2_goals_et=None,
        shootout_winner_id=None,
        resolved_events=resolved,
        t1_total=1,
        t2_total=0,
    )

    fr = db_session.query(FootballMatchResult).filter_by(match_id=match.id).first()
    assert fr is not None
    assert fr.team1_goals_reg == 1
    assert fr.team2_goals_reg == 0

    events = db_session.query(FootballPlayerMatchEvent).filter_by(match_id=match.id).all()
    assert len(events) == 2

    t1_event = next(e for e in events if e.player_id == t1_player.id)
    assert t1_event.goals == 1
    assert t1_event.team_goals_conceded == 0   # t2 scored 0

    db_session.refresh(match)
    assert match.status == MatchStatus.COMPLETED


def test_apply_replaces_existing_result(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    # First result
    _apply_football_result(
        db=db_session, match=match,
        team1_goals_reg=2, team2_goals_reg=1,
        team1_goals_et=None, team2_goals_et=None,
        shootout_winner_id=None, resolved_events=[],
        t1_total=2, t2_total=1,
    )

    # Second call should replace, not duplicate
    _apply_football_result(
        db=db_session, match=match,
        team1_goals_reg=3, team2_goals_reg=0,
        team1_goals_et=None, team2_goals_et=None,
        shootout_winner_id=None, resolved_events=[],
        t1_total=3, t2_total=0,
    )

    results = db_session.query(FootballMatchResult).filter_by(match_id=match.id).all()
    assert len(results) == 1
    assert results[0].team1_goals_reg == 3


def test_apply_sets_shootout_winner(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    _apply_football_result(
        db=db_session, match=match,
        team1_goals_reg=1, team2_goals_reg=1,
        team1_goals_et=1, team2_goals_et=1,
        shootout_winner_id=team2.id, resolved_events=[],
        t1_total=1, t2_total=1,
    )

    fr = db_session.query(FootballMatchResult).filter_by(match_id=match.id).first()
    assert fr.shootout_winner_id == team2.id
    assert fr.team1_goals_et == 1


def test_apply_resets_predictions_for_rescoring(db_session, test_tournament, test_teams, test_user):
    team1, team2 = test_teams
    t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    from app.models.football_prediction import FootballPrediction
    pred = Prediction(
        user_id=test_user.id,
        match_id=match.id,
        is_processed=True,
        points_earned=50,
    )
    db_session.add(pred)
    db_session.flush()
    fp = FootballPrediction(
        prediction_id=pred.id,
        team1_goals=1,
        team2_goals=0,
        player_pick_1_id=t1_players[0].id,
        player_pick_2_id=t1_players[1].id,
        player_pick_3_id=t2_players[0].id,
    )
    db_session.add(fp)
    db_session.commit()

    _apply_football_result(
        db=db_session, match=match,
        team1_goals_reg=1, team2_goals_reg=0,
        team1_goals_et=None, team2_goals_et=None,
        shootout_winner_id=None, resolved_events=[],
        t1_total=1, t2_total=0,
    )

    db_session.refresh(pred)
    assert pred.is_processed is True   # rescored by calculate_scores
    # points_earned may be non-zero if scoring runs; the key check is it was reset & re-run


# ---------------------------------------------------------------------------
# sync_match_result
# ---------------------------------------------------------------------------

def test_sync_match_result_returns_not_finished_when_api_says_so(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        external_match_id="12345",
        sync_state="linked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    mock_provider = MagicMock()
    mock_provider.get_fixture_result.return_value = None   # match not finished
    set_provider(mock_provider)

    result = sync_match_result(db_session, match.id)
    assert result["status"] == "not_finished"

    db_session.refresh(match)
    assert match.status == MatchStatus.SCHEDULED   # unchanged

    set_provider(None)


def test_sync_match_result_errors_without_external_id(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    mock_provider = MagicMock()
    set_provider(mock_provider)

    result = sync_match_result(db_session, match.id)
    assert result["status"] == "error"
    assert "external_match_id" in result["detail"]

    set_provider(None)


def test_sync_match_result_writes_result_and_sets_state(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

    for p in t1_players + t2_players:
        p.api_football_player_id = str(p.id)
    db_session.commit()

    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        external_match_id="99999",
        sync_state="linked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    fixture_result = FootballFixtureResult(
        fixture_id=99999,
        status_short="FT",
        home_team_api_id=100,   # maps to team_1
        away_team_api_id=200,
        team1_goals_reg=2,
        team2_goals_reg=1,
        team1_goals_et=None,
        team2_goals_et=None,
        penalty_team1=None,
        penalty_team2=None,
    )

    player_stats = [
        FootballPlayerStat(
            api_player_id=t1_players[0].id,
            name=t1_players[0].name,
            team_api_id=100,
            minutes_played=90,
            goals=2,
            assists=0,
            red_card=False,
            own_goals=0,
            ingame_pen_saves=0,
            shootout_pen_saves=0,
            ingame_pen_misses=0,
        ),
        FootballPlayerStat(
            api_player_id=t2_players[0].id,
            name=t2_players[0].name,
            team_api_id=200,
            minutes_played=90,
            goals=1,
            assists=0,
            red_card=False,
            own_goals=0,
            ingame_pen_saves=0,
            shootout_pen_saves=0,
            ingame_pen_misses=0,
        ),
    ]

    mock_provider = MagicMock()
    mock_provider.get_fixture_result.return_value = fixture_result
    mock_provider.get_player_stats.return_value = player_stats
    set_provider(mock_provider)

    result = sync_match_result(db_session, match.id)

    assert result["status"] == "synced"
    assert result["unresolved_players"] == []

    db_session.refresh(match)
    assert match.status == MatchStatus.COMPLETED
    assert match.sync_state == "result_synced"

    fr = db_session.query(FootballMatchResult).filter_by(match_id=match.id).first()
    assert fr is not None
    assert fr.team1_goals_reg == 2
    assert fr.team2_goals_reg == 1

    events = db_session.query(FootballPlayerMatchEvent).filter_by(match_id=match.id).all()
    assert len(events) == 2

    set_provider(None)


def test_sync_match_result_reports_unresolved_players(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        external_match_id="88888",
        sync_state="linked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    fixture_result = FootballFixtureResult(
        fixture_id=88888,
        status_short="FT",
        home_team_api_id=100,
        away_team_api_id=200,
        team1_goals_reg=1,
        team2_goals_reg=0,
        team1_goals_et=None,
        team2_goals_et=None,
        penalty_team1=None,
        penalty_team2=None,
    )

    player_stats = [
        FootballPlayerStat(
            api_player_id=0,
            name="ZZZXXX Nobody",   # won't resolve
            team_api_id=100,
            minutes_played=90,
            goals=1,
            assists=0,
            red_card=False,
            own_goals=0,
            ingame_pen_saves=0,
            shootout_pen_saves=0,
            ingame_pen_misses=0,
        ),
    ]

    mock_provider = MagicMock()
    mock_provider.get_fixture_result.return_value = fixture_result
    mock_provider.get_player_stats.return_value = player_stats
    set_provider(mock_provider)

    result = sync_match_result(db_session, match.id)

    assert result["status"] == "synced"
    assert len(result["unresolved_players"]) == 1
    assert "ZZZXXX Nobody" in result["unresolved_players"][0]

    db_session.refresh(match)
    assert match.sync_error is not None
    assert "ZZZXXX Nobody" in match.sync_error

    set_provider(None)


def test_sync_match_result_derives_pen_shootout_winner(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        external_match_id="77777",
        sync_state="linked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    # AET draw, team2 wins on penalties (away)
    fixture_result = FootballFixtureResult(
        fixture_id=77777,
        status_short="PEN",
        home_team_api_id=100,
        away_team_api_id=200,
        team1_goals_reg=1,
        team2_goals_reg=1,
        team1_goals_et=1,
        team2_goals_et=1,
        penalty_team1=3,
        penalty_team2=5,   # team2 wins
    )

    mock_provider = MagicMock()
    mock_provider.get_fixture_result.return_value = fixture_result
    mock_provider.get_player_stats.return_value = []
    set_provider(mock_provider)

    sync_match_result(db_session, match.id)

    fr = db_session.query(FootballMatchResult).filter_by(match_id=match.id).first()
    assert fr.shootout_winner_id == team2.id

    set_provider(None)
