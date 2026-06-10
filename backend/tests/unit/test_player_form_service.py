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
        # g90 ≈ (8+1.25)/15=0.617, a90 ≈ (2+0.6)/15=0.173, m=1, FWD: floor+goals+assists ≈ 3+6.17+0.87 ≈ 10.0
        assert 9.0 < xp < 11.5

    def test_mid_with_assists(self):
        sp = _SquadPlayer(2, "Midfielder", "Midfielder", appearances=10, minutes=900, goals=3, assists=6, clean_sheets=0)
        xp = _pre_xp(sp)
        # g90≈0.22, a90≈0.427; MID: floor+goals+assists+cs ≈ 3+3.3+4.27+0.82 ≈ 11.4
        assert 10.5 < xp < 13.0

    def test_def_with_contributions(self):
        sp = _SquadPlayer(3, "Defender", "Defender", appearances=10, minutes=900, goals=1, assists=2, clean_sheets=0)
        xp = _pre_xp(sp)
        # g90≈0.073, a90≈0.143; DEF: floor+goals+assists+cs ≈ 3+1.83+1.72+1.64 ≈ 8.2
        assert 7.0 < xp < 10.0

    def test_gk_with_saves(self):
        # clean_sheets from squad data is not used in new formula (cs derived from lambda).
        # GK with 40 saves in 10 games: XP ≈ floor + clean_sheet_prob*6 + pen_save ≈ 4.9
        sp = _SquadPlayer(4, "Keeper", "Goalkeeper", appearances=10, minutes=900, goals=0, assists=0, clean_sheets=40)
        xp = _pre_xp(sp)
        assert 4.0 < xp < 6.0

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
        # g90 ≈ (2+1.25)/7=0.464, a90 ≈ (1+0.6)/7=0.229; floor+goals+assists ≈ 3+4.64+1.14 ≈ 8.8
        assert 8.0 < xp < 10.5

    def test_gk_no_attacking_output(self):
        # Clean-sheet history (wc_clean_sheets) is NOT used in new formula.
        # GK XP depends on floor + lambda-derived cs probability + pen-save term.
        form = _Form(wc_goals=0, wc_assists=0, wc_minutes=90, wc_clean_sheets=1, wc_games=1)
        xp = _wc_xp(form, "Goalkeeper")
        # floor(3) + p_cs*6 + pen_save = 3 + 0.2725*6 + 0.25 ≈ 4.9
        assert 4.0 < xp < 6.0

    def test_def_no_wc_data_returns_zero(self):
        form = _Form(wc_games=0)
        xp = _wc_xp(form, "Defender")
        assert xp == 0.0

    def test_mid_goals_dominate(self):
        form = _Form(wc_goals=3, wc_assists=0, wc_minutes=270, wc_games=3)
        xp = _wc_xp(form, "Midfielder")
        # g90 ≈ (3+0.3)/8=0.4125; MID: floor+goals+cs ≈ 3+6.19+0.82 ≈ 10.5
        assert 9.5 < xp < 12.0


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

    def test_three_wc_games_weight_is_capped(self):
        # With 3 WC games, wc_weight = min(3/3,1)*WC_WEIGHT_CAP = 0.7 (not 1.0)
        from app.services.player_form_service import WC_WEIGHT_CAP
        form = _Form(
            wc_games=3, wc_goals=3, wc_assists=0, wc_minutes=270, wc_clean_sheets=0,
            pre_expected_points=8.0,
        )
        result = _blend(form, "Attacker")
        wc = _wc_xp(form, "Attacker")
        pre = 8.0
        expected = round((1 - WC_WEIGHT_CAP) * pre + WC_WEIGHT_CAP * wc, 2)
        assert abs(result - expected) < 0.05
        # Must NOT be pure WC (cap means pre is still 30% weighted)
        assert abs(result - wc) > 0.1

    def test_one_wc_game_blends_with_cap(self):
        # wc_weight = (1/3) * WC_WEIGHT_CAP
        from app.services.player_form_service import WC_WEIGHT_CAP
        form = _Form(
            wc_games=1, wc_goals=1, wc_assists=0, wc_minutes=90, wc_clean_sheets=0,
            pre_expected_points=9.0,
        )
        result = _blend(form, "Attacker")
        wc = _wc_xp(form, "Attacker")
        pre = 9.0
        wc_weight = (1 / 3) * WC_WEIGHT_CAP
        expected = round((1 - wc_weight) * pre + wc_weight * wc, 2)
        assert abs(result - expected) < 0.05

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

    def test_wc_weight_capped_at_wc_weight_cap_even_with_many_games(self):
        # 6 WC games: wc_weight = min(6/3,1)*WC_WEIGHT_CAP = WC_WEIGHT_CAP (not 1.0)
        from app.services.player_form_service import WC_WEIGHT_CAP
        form = _Form(
            wc_games=6, wc_goals=6, wc_assists=0, wc_minutes=540, wc_clean_sheets=0,
            pre_expected_points=5.0,
        )
        result = _blend(form, "Attacker")
        wc = _wc_xp(form, "Attacker")
        pre = 5.0
        expected = round((1 - WC_WEIGHT_CAP) * pre + WC_WEIGHT_CAP * wc, 2)
        assert abs(result - expected) < 0.05
        # Pre form still contributes (1 - WC_WEIGHT_CAP) = 30%
        assert abs(result - wc) > 0.1
