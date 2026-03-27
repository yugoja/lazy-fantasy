"""Unit tests for cricket sync — player resolution and sync logic with a mock provider."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.match_lineup import MatchLineup
from app.services.cricket_provider import ProviderMatchInfo, ProviderPlayer
from app.services.cricket_sync import (
    _normalize,
    _name_matches,
    _resolve_player,
    _top_by,
    _resolve_team,
    set_provider,
    sync_lineups,
    sync_results,
)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

def test_normalize_strips_diacritics():
    assert _normalize("Ünlü") == "unlu"


def test_normalize_removes_punctuation():
    assert _normalize("O'Brien") == "obrien"


def test_normalize_lowercases():
    assert _normalize("Virat Kohli") == "virat kohli"


# ---------------------------------------------------------------------------
# _name_matches
# ---------------------------------------------------------------------------

def test_name_matches_full_name():
    assert _name_matches("Virat Kohli", "Virat Kohli") is True


def test_name_matches_initial():
    assert _name_matches("V Kohli", "Virat Kohli") is True


def test_name_matches_wrong_last_name():
    assert _name_matches("V Sharma", "Virat Kohli") is False


def test_name_matches_single_token_last_name():
    assert _name_matches("Kohli", "Virat Kohli") is True


def test_name_matches_initial_wrong_first_letter():
    assert _name_matches("R Kohli", "Virat Kohli") is False


def test_name_matches_full_first_name_mismatch():
    assert _name_matches("Rohit Kohli", "Virat Kohli") is False


# ---------------------------------------------------------------------------
# _top_by
# ---------------------------------------------------------------------------

def test_top_by_returns_highest():
    players = [
        ProviderPlayer("1", "A", "T", batting_runs=30),
        ProviderPlayer("2", "B", "T", batting_runs=75),
        ProviderPlayer("3", "C", "T", batting_runs=10),
    ]
    assert _top_by(players, "batting_runs").name == "B"


def test_top_by_returns_none_if_all_zero():
    players = [ProviderPlayer("1", "A", "T", batting_runs=0)]
    assert _top_by(players, "batting_runs") is None


def test_top_by_empty_list():
    assert _top_by([], "batting_runs") is None


# ---------------------------------------------------------------------------
# _resolve_player — tier 1: exact provider_id
# ---------------------------------------------------------------------------

def test_resolve_player_by_provider_id(db_session, test_teams):
    team1, _ = test_teams
    player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    player.cricapi_player_id = "cric-123"
    db_session.commit()

    pp = ProviderPlayer(provider_id="cric-123", name="Wrong Name", team_name="X")
    resolved = _resolve_player(pp, [], db_session)
    assert resolved is not None
    assert resolved.id == player.id


# ---------------------------------------------------------------------------
# _resolve_player — tier 2: normalized name
# ---------------------------------------------------------------------------

def test_resolve_player_by_full_name(db_session, test_teams):
    team1, _ = test_teams
    player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    player.name = "Virat Kohli"
    db_session.commit()

    candidates = db_session.query(Player).filter(Player.team_id == team1.id).all()
    pp = ProviderPlayer(provider_id="", name="Virat Kohli", team_name="X")
    resolved = _resolve_player(pp, candidates, db_session)
    assert resolved is not None
    assert resolved.name == "Virat Kohli"


def test_resolve_player_by_initial(db_session, test_teams):
    team1, _ = test_teams
    player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    player.name = "Virat Kohli"
    db_session.commit()

    candidates = db_session.query(Player).filter(Player.team_id == team1.id).all()
    pp = ProviderPlayer(provider_id="", name="V Kohli", team_name="X")
    resolved = _resolve_player(pp, candidates, db_session)
    assert resolved is not None
    assert resolved.name == "Virat Kohli"


def test_resolve_player_unmatched_returns_none(db_session, test_teams):
    team1, _ = test_teams
    candidates = db_session.query(Player).filter(Player.team_id == team1.id).all()
    pp = ProviderPlayer(provider_id="", name="Nobody Special", team_name="X")
    resolved = _resolve_player(pp, candidates, db_session)
    assert resolved is None


# ---------------------------------------------------------------------------
# _resolve_player — tier 3: fuzzy
# ---------------------------------------------------------------------------

def test_resolve_player_fuzzy(db_session, test_teams):
    team1, _ = test_teams
    player = db_session.query(Player).filter(Player.team_id == team1.id).first()
    player.name = "Jasprit Bumrah"
    db_session.commit()

    candidates = db_session.query(Player).filter(Player.team_id == team1.id).all()
    # Slight misspelling — should fuzzy-match
    pp = ProviderPlayer(provider_id="", name="Jasprit Bumra", team_name="X")
    resolved = _resolve_player(pp, candidates, db_session)
    assert resolved is not None
    assert resolved.name == "Jasprit Bumrah"


# ---------------------------------------------------------------------------
# sync_lineups
# ---------------------------------------------------------------------------

def test_sync_lineups_populates_lineup(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

    # Assign cricapi_player_ids for reliable tier-1 resolution
    for p in t1_players + t2_players:
        p.cricapi_player_id = f"cric-{p.id}"
    db_session.commit()

    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        status=MatchStatus.SCHEDULED,
        external_match_id="ext-001",
        sync_state="linked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    def make_pp(player):
        return ProviderPlayer(provider_id=f"cric-{player.id}", name=player.name, team_name="")

    mock_info = ProviderMatchInfo(
        provider_match_id="ext-001",
        name="Team A vs Team B",
        status="Match not started",
        team1_name=team1.name,
        team2_name=team2.name,
        lineup_announced=True,
        team1_players=[make_pp(p) for p in t1_players],
        team2_players=[make_pp(p) for p in t2_players],
        winner_name=None,
        pom_name=None,
        overs_completed=None,
    )

    mock_provider = MagicMock()
    mock_provider.get_match_info.return_value = mock_info
    set_provider(mock_provider)

    sync_lineups(db_session)

    lineup_rows = db_session.query(MatchLineup).filter(MatchLineup.match_id == match.id).all()
    assert len(lineup_rows) == 22

    db_session.refresh(match)
    assert match.sync_state == "lineup_synced"

    set_provider(None)


def test_sync_lineups_skips_when_not_announced(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        status=MatchStatus.SCHEDULED,
        external_match_id="ext-002",
        sync_state="linked",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    mock_info = ProviderMatchInfo(
        provider_match_id="ext-002",
        name="Team A vs Team B",
        status="Match not started",
        team1_name=team1.name,
        team2_name=team2.name,
        lineup_announced=False,
        team1_players=[],
        team2_players=[],
        winner_name=None,
        pom_name=None,
        overs_completed=None,
    )

    mock_provider = MagicMock()
    mock_provider.get_match_info.return_value = mock_info
    set_provider(mock_provider)

    sync_lineups(db_session)

    lineup_rows = db_session.query(MatchLineup).filter(MatchLineup.match_id == match.id).all()
    assert len(lineup_rows) == 0

    db_session.refresh(match)
    assert match.sync_state == "linked"  # unchanged

    set_provider(None)


def test_sync_lineups_skips_unlinked_match(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        status=MatchStatus.SCHEDULED,
        external_match_id=None,
        sync_state="unlinked",
    )
    db_session.add(match)
    db_session.commit()

    mock_provider = MagicMock()
    set_provider(mock_provider)

    sync_lineups(db_session)

    mock_provider.get_match_info.assert_not_called()
    set_provider(None)


# ---------------------------------------------------------------------------
# sync_results
# ---------------------------------------------------------------------------

def test_sync_results_sets_result_and_scores(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    t1_players = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2_players = db_session.query(Player).filter(Player.team_id == team2.id).all()

    # Assign cricapi_player_ids for reliable tier-1 resolution
    for p in t1_players + t2_players:
        p.cricapi_player_id = f"cric-{p.id}"
    db_session.commit()

    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=4),
        status=MatchStatus.SCHEDULED,
        external_match_id="ext-003",
        sync_state="lineup_synced",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    def make_pp(player, runs=0, wickets=0):
        pp = ProviderPlayer(provider_id=f"cric-{player.id}", name=player.name, team_name="")
        pp.batting_runs = runs
        pp.bowling_wickets = wickets
        return pp

    t1_pps = [make_pp(p, runs=50 if i == 0 else 10) for i, p in enumerate(t1_players)]
    t2_pps = [make_pp(p, runs=60 if i == 0 else 5, wickets=3 if i == 4 else 0) for i, p in enumerate(t2_players)]
    t1_pps[4].bowling_wickets = 2  # top wicket taker team1

    mock_info = ProviderMatchInfo(
        provider_match_id="ext-003",
        name="Team A vs Team B",
        status="Team A won by 5 wickets",
        team1_name=team1.name,
        team2_name=team2.name,
        lineup_announced=True,
        team1_players=t1_pps,
        team2_players=t2_pps,
        winner_name=team1.name,
        pom_name=t1_players[0].name,
        overs_completed=20.0,
    )

    mock_provider = MagicMock()
    mock_provider.get_match_info.return_value = mock_info
    set_provider(mock_provider)

    sync_results(db_session)

    db_session.refresh(match)
    assert match.status == MatchStatus.COMPLETED
    assert match.sync_state == "result_synced"
    assert match.result_winner_id == team1.id
    assert match.result_pom_player_id == t1_players[0].id
    assert match.result_most_runs_team1_player_id == t1_players[0].id
    assert match.result_most_runs_team2_player_id == t2_players[0].id

    set_provider(None)


def test_sync_results_skips_if_not_finished(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=4),
        status=MatchStatus.SCHEDULED,
        external_match_id="ext-004",
        sync_state="lineup_synced",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    mock_info = ProviderMatchInfo(
        provider_match_id="ext-004",
        name="Team A vs Team B",
        status="In Progress",  # not a result string
        team1_name=team1.name,
        team2_name=team2.name,
        lineup_announced=True,
        team1_players=[],
        team2_players=[],
        winner_name=None,
        pom_name=None,
        overs_completed=None,
    )

    mock_provider = MagicMock()
    mock_provider.get_match_info.return_value = mock_info
    set_provider(mock_provider)

    sync_results(db_session)

    db_session.refresh(match)
    assert match.status == MatchStatus.SCHEDULED  # unchanged

    set_provider(None)


def test_sync_results_skips_already_result_synced(db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=4),
        status=MatchStatus.COMPLETED,
        external_match_id="ext-005",
        sync_state="result_synced",
    )
    db_session.add(match)
    db_session.commit()

    mock_provider = MagicMock()
    set_provider(mock_provider)

    sync_results(db_session)

    mock_provider.get_match_info.assert_not_called()
    set_provider(None)
