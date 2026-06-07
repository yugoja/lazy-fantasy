"""Unit tests for player_form_service pure functions — TDD red phase."""
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import Optional


# ── Helpers that mirror the expected signatures ───────────────────────────────

# We import the functions after each RED→GREEN cycle; if they don't exist yet,
# these tests simply collect but fail at import-resolution time.

from app.services.player_form_service import (
    _pre_xp,
    _wc_xp,
    _derive_floor,
    _blend,
)


# ── Minimal stand-in dataclasses (mirror WCSquadPlayer & PlayerForm shape) ────

@dataclass
class _SquadPlayer:
    """Mirrors WCSquadPlayer from football_provider."""
    api_player_id: int
    name: str
    position: str
    appearances: int
    minutes: int
    goals: int
    assists: int
    clean_sheets: int


@dataclass
class _Form:
    """Mirrors PlayerForm columns relevant to formula tests."""
    wc_goals: int = 0
    wc_assists: int = 0
    wc_minutes: int = 0
    wc_clean_sheets: int = 0
    wc_games: int = 0
    pre_expected_points: Optional[float] = None
    expected_points: float = 6.0
    floor: str = "mid"
    availability: str = "starter"


# ── _pre_xp ───────────────────────────────────────────────────────────────────

class TestPreXp:
    def test_fwd_with_goals(self):
        sp = _SquadPlayer(1, "Striker", "Attacker", appearances=10, minutes=900, goals=8, assists=2, clean_sheets=0)
        xp = _pre_xp(sp)
        # goals_per90 = 8 / (900/90) = 8/10 = 0.8  → *6 = 4.8
        # assists_per90 = 2/10 = 0.2 → *3 = 0.6
        # expected ≈ 5.4
        assert 5.0 < xp < 6.0

    def test_mid_with_assists(self):
        sp = _SquadPlayer(2, "Midfielder", "Midfielder", appearances=10, minutes=900, goals=3, assists=6, clean_sheets=0)
        xp = _pre_xp(sp)
        # goals_per90 = 0.3 → *5 = 1.5; assists_per90 = 0.6 → *4 = 2.4 → 3.9
        assert 3.5 < xp < 4.5

    def test_def_with_clean_sheets(self):
        sp = _SquadPlayer(3, "Defender", "Defender", appearances=10, minutes=900, goals=1, assists=2, clean_sheets=5)
        xp = _pre_xp(sp)
        # cs_rate = 5/10 = 0.5 → *5 = 2.5
        # assists_per90 = 0.2 → *3 = 0.6
        # goals_per90 = 0.1 → *4 = 0.4
        # expected ≈ 3.5
        assert 3.0 < xp < 4.5

    def test_gk_with_clean_sheets(self):
        sp = _SquadPlayer(4, "Keeper", "Goalkeeper", appearances=10, minutes=900, goals=0, assists=0, clean_sheets=6)
        xp = _pre_xp(sp)
        # cs_rate = 0.6 → *8 = 4.8; minutes/90/appearances = 1.0 → *2 = 2.0 → 6.8
        assert 6.0 < xp < 8.0

    def test_zero_appearances_returns_stub(self):
        sp = _SquadPlayer(5, "Unknown", "Attacker", appearances=0, minutes=0, goals=0, assists=0, clean_sheets=0)
        xp = _pre_xp(sp)
        # Falls back to stub for FWD = 10.0
        assert xp == 10.0

    def test_gk_zero_appearances_stub(self):
        sp = _SquadPlayer(6, "Unknown GK", "Goalkeeper", appearances=0, minutes=0, goals=0, assists=0, clean_sheets=0)
        xp = _pre_xp(sp)
        assert xp == 5.0

    def test_def_zero_appearances_stub(self):
        sp = _SquadPlayer(7, "Unknown DEF", "Defender", appearances=0, minutes=0, goals=0, assists=0, clean_sheets=0)
        xp = _pre_xp(sp)
        assert xp == 6.0

    def test_mid_zero_appearances_stub(self):
        sp = _SquadPlayer(8, "Unknown MID", "Midfielder", appearances=0, minutes=0, goals=0, assists=0, clean_sheets=0)
        xp = _pre_xp(sp)
        assert xp == 8.0


# ── _wc_xp ────────────────────────────────────────────────────────────────────

class TestWcXp:
    def test_fwd_two_goals_one_assist_in_two_games(self):
        form = _Form(wc_goals=2, wc_assists=1, wc_minutes=180, wc_clean_sheets=0, wc_games=2)
        xp = _wc_xp(form, "Attacker")
        # goals_per90 = 2/(180/90) = 2/2 = 1.0 → *6 = 6.0
        # assists_per90 = 1/2 = 0.5 → *3 = 1.5
        # expected ≈ 7.5
        assert 7.0 < xp < 8.5

    def test_gk_clean_sheet(self):
        form = _Form(wc_goals=0, wc_assists=0, wc_minutes=90, wc_clean_sheets=1, wc_games=1)
        xp = _wc_xp(form, "Goalkeeper")
        # cs_rate = 1.0 → *8 = 8.0; minutes/90/games = 1.0 → *2 = 2.0 → 10.0
        assert 9.0 < xp <= 10.0

    def test_def_no_wc_data_returns_zero(self):
        form = _Form(wc_games=0)
        xp = _wc_xp(form, "Defender")
        assert xp == 0.0

    def test_mid_goals_dominate(self):
        form = _Form(wc_goals=3, wc_assists=0, wc_minutes=270, wc_games=3)
        xp = _wc_xp(form, "Midfielder")
        # goals_per90 = 3/3 = 1.0 → *5 = 5.0; assists = 0 → 5.0
        assert 4.5 < xp < 5.5


# ── _derive_floor ─────────────────────────────────────────────────────────────

class TestDeriveFloor:
    def test_no_wc_data_returns_mid(self):
        form = _Form(wc_games=0, wc_minutes=0)
        assert _derive_floor(form) == "mid"

    def test_60_plus_avg_returns_high(self):
        form = _Form(wc_games=2, wc_minutes=130)  # avg 65
        assert _derive_floor(form) == "high"

    def test_exactly_60_avg_is_high(self):
        form = _Form(wc_games=2, wc_minutes=120)  # avg 60
        assert _derive_floor(form) == "high"

    def test_30_to_59_avg_returns_mid(self):
        form = _Form(wc_games=2, wc_minutes=80)  # avg 40
        assert _derive_floor(form) == "mid"

    def test_under_30_avg_returns_low(self):
        form = _Form(wc_games=2, wc_minutes=40)  # avg 20
        assert _derive_floor(form) == "low"


# ── _blend ────────────────────────────────────────────────────────────────────

class TestBlend:
    def test_zero_wc_games_returns_pre_xp(self):
        form = _Form(wc_games=0, pre_expected_points=8.5)
        result = _blend(form, "Attacker")
        # wc_weight = 0 → pure pre
        assert result == 8.5

    def test_three_wc_games_returns_pure_wc(self):
        # With 3 WC games and a goal per game, wc_weight = 1.0
        form = _Form(
            wc_games=3, wc_goals=3, wc_assists=0, wc_minutes=270, wc_clean_sheets=0,
            pre_expected_points=8.0,
        )
        result = _blend(form, "Attacker")
        wc = _wc_xp(form, "Attacker")
        assert abs(result - wc) < 0.01

    def test_one_wc_game_blends_one_third(self):
        # wc_weight = 1/3
        form = _Form(
            wc_games=1, wc_goals=1, wc_assists=0, wc_minutes=90, wc_clean_sheets=0,
            pre_expected_points=9.0,
        )
        result = _blend(form, "Attacker")
        wc = _wc_xp(form, "Attacker")
        pre = 9.0
        expected = round((2/3) * pre + (1/3) * wc, 2)
        assert result == expected

    def test_pre_xp_none_uses_position_stub(self):
        # pre_expected_points=None → should use FWD stub=10.0
        form = _Form(wc_games=0, pre_expected_points=None)
        result = _blend(form, "Attacker")
        assert result == 10.0

    def test_gk_stub_when_no_pre_xp(self):
        form = _Form(wc_games=0, pre_expected_points=None)
        result = _blend(form, "Goalkeeper")
        assert result == 5.0

    def test_result_is_rounded_to_two_decimal_places(self):
        form = _Form(
            wc_games=1, wc_goals=1, wc_assists=1, wc_minutes=90, wc_clean_sheets=0,
            pre_expected_points=7.0,
        )
        result = _blend(form, "Midfielder")
        # Check it has at most 2 decimal places
        assert result == round(result, 2)

    def test_wc_weight_capped_at_one_after_three_games(self):
        # 6 games should not make wc_weight > 1
        form = _Form(
            wc_games=6, wc_goals=6, wc_assists=0, wc_minutes=540, wc_clean_sheets=0,
            pre_expected_points=5.0,
        )
        result = _blend(form, "Attacker")
        wc = _wc_xp(form, "Attacker")
        assert abs(result - wc) < 0.01  # wc_weight == 1.0 even with 6 games
