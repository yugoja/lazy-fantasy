"""Unit tests for ApiFootballProvider extensions (WCSquadPlayer, FixtureLineup)."""
import pytest
from unittest.mock import MagicMock, patch

from app.services.football_provider import (
    ApiFootballProvider,
    WCSquadPlayer,
    FixtureLineup,
)


def _make_provider():
    return ApiFootballProvider(api_key="testkey")


# ── WCSquadPlayer dataclass ───────────────────────────────────────────────────

def test_wc_squad_player_has_expected_fields():
    sp = WCSquadPlayer(
        api_player_id=1,
        name="Lionel Messi",
        position="Attacker",
        appearances=10,
        minutes=900,
        goals=5,
        assists=3,
        clean_sheets=0,
    )
    assert sp.api_player_id == 1
    assert sp.position == "Attacker"
    assert sp.clean_sheets == 0


# ── FixtureLineup dataclass ───────────────────────────────────────────────────

def test_fixture_lineup_has_expected_fields():
    lineup = FixtureLineup(
        home_starters=[1, 2, 3],
        away_starters=[4, 5, 6],
        home_subs=[7, 8],
        away_subs=[9, 10],
    )
    assert lineup.home_starters == [1, 2, 3]
    assert lineup.away_subs == [9, 10]


# ── get_wc_squad ──────────────────────────────────────────────────────────────

def _squad_api_response(team_id=10, player_id=100, name="Test Player", position="Attacker",
                         appearances=5, minutes=450, goals=2, assists=1, clean_sheets=0):
    return {
        "response": [{
            "player": {"id": player_id, "name": name},
            "statistics": [{
                "team": {"id": team_id},
                "games": {"position": position, "appearences": appearances, "minutes": minutes},
                "goals": {"total": goals, "assists": assists, "conceded": 0, "saves": clean_sheets},
            }]
        }],
        "paging": {"current": 1, "total": 1},
    }


def test_get_wc_squad_returns_squad_players():
    provider = _make_provider()
    response = _squad_api_response()
    with patch.object(provider, "_get", return_value=response):
        players = provider.get_wc_squad(team_id=10, league_id=1, season=2026)
    assert len(players) == 1
    assert isinstance(players[0], WCSquadPlayer)
    assert players[0].api_player_id == 100
    assert players[0].name == "Test Player"
    assert players[0].position == "Attacker"
    assert players[0].appearances == 5
    assert players[0].goals == 2
    assert players[0].assists == 1


def test_get_wc_squad_handles_none_response():
    provider = _make_provider()
    with patch.object(provider, "_get", return_value=None):
        players = provider.get_wc_squad(team_id=10, league_id=1, season=2026)
    assert players == []


def test_get_wc_squad_handles_empty_response():
    provider = _make_provider()
    with patch.object(provider, "_get", return_value={"response": [], "paging": {"current": 1, "total": 1}}):
        players = provider.get_wc_squad(team_id=10, league_id=1, season=2026)
    assert players == []


def test_get_wc_squad_handles_pagination():
    provider = _make_provider()
    page1 = {
        "response": [
            {"player": {"id": 1, "name": "Player A"}, "statistics": [{
                "team": {"id": 10},
                "games": {"position": "Attacker", "appearences": 3, "minutes": 270},
                "goals": {"total": 1, "assists": 0, "conceded": 0, "saves": 0},
            }]}
        ],
        "paging": {"current": 1, "total": 2},
    }
    page2 = {
        "response": [
            {"player": {"id": 2, "name": "Player B"}, "statistics": [{
                "team": {"id": 10},
                "games": {"position": "Defender", "appearences": 3, "minutes": 270},
                "goals": {"total": 0, "assists": 1, "conceded": 0, "saves": 2},
            }]}
        ],
        "paging": {"current": 2, "total": 2},
    }
    with patch.object(provider, "_get", side_effect=[page1, page2]):
        players = provider.get_wc_squad(team_id=10, league_id=1, season=2026)
    assert len(players) == 2
    assert {p.name for p in players} == {"Player A", "Player B"}


def test_get_wc_squad_gk_uses_saves_as_clean_sheets():
    provider = _make_provider()
    response = _squad_api_response(position="Goalkeeper", clean_sheets=4)
    with patch.object(provider, "_get", return_value=response):
        players = provider.get_wc_squad(team_id=10, league_id=1, season=2026)
    assert players[0].clean_sheets == 4


# ── get_fixture_lineup ────────────────────────────────────────────────────────

def _lineup_api_response(home_starters, home_subs, away_starters, away_subs):
    def _make_team(starters, subs):
        return {
            "startXI": [{"player": {"id": pid}} for pid in starters],
            "substitutes": [{"player": {"id": pid}} for pid in subs],
        }
    return {
        "response": [
            _make_team(home_starters, home_subs),
            _make_team(away_starters, away_subs),
        ]
    }


def test_get_fixture_lineup_returns_lineup():
    provider = _make_provider()
    response = _lineup_api_response(
        home_starters=[1, 2, 3], home_subs=[11, 12],
        away_starters=[4, 5, 6], away_subs=[13, 14],
    )
    with patch.object(provider, "_get", return_value=response):
        lineup = provider.get_fixture_lineup(fixture_id=999)
    assert isinstance(lineup, FixtureLineup)
    assert lineup.home_starters == [1, 2, 3]
    assert lineup.away_starters == [4, 5, 6]
    assert lineup.home_subs == [11, 12]
    assert lineup.away_subs == [13, 14]


def test_get_fixture_lineup_returns_none_when_no_response():
    provider = _make_provider()
    with patch.object(provider, "_get", return_value=None):
        lineup = provider.get_fixture_lineup(fixture_id=999)
    assert lineup is None


def test_get_fixture_lineup_returns_none_when_empty_response():
    provider = _make_provider()
    with patch.object(provider, "_get", return_value={"response": []}):
        lineup = provider.get_fixture_lineup(fixture_id=999)
    assert lineup is None
