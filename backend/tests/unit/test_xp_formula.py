"""§9 target tests for the XP formula rewrite.

Written against the INTENDED behaviour. They fail against the current code —
that is expected. They define the target.

Run after implementing Tier 1A (XP rewrite) and Tier 1B (neutral baseline)
and verify all pass.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import pytest

from app.services.player_form_service import (
    BASE_LAMBDA,
    EXPECTED_PEN_SAVES_PER_MATCH,
    WC_WEIGHT_CAP,
    _blend,
    _wc_xp,
    _xp_formula,
)
from app.services.scoring_football import (
    ASSIST_POINTS,
    CLEAN_SHEET_POINTS,
    FLOOR_POINTS,
    GOAL_POINTS,
    PEN_SAVE_POINTS,
    Position,
)
from app.services.fallback_job import _rank_adjusted_lambdas

pytestmark = pytest.mark.unit


# ── Minimal stand-ins ──────────────────────────────────────────────────────────


@dataclass
class _Form:
    wc_goals: int = 0
    wc_assists: int = 0
    wc_minutes: int = 0
    wc_clean_sheets: int = 0
    wc_games: int = 0
    pre_expected_points: Optional[float] = None
    expected_points: float = 6.0
    floor: str = "mid"
    availability: str = "starter"


# ── Helper ─────────────────────────────────────────────────────────────────────


def _poisson0(lam: float) -> float:
    """P(X=0) for Poisson(lam) — the clean-sheet probability."""
    return math.exp(-lam)


# ══════════════════════════════════════════════════════════════════════════════
# _xp_formula
# ══════════════════════════════════════════════════════════════════════════════


class TestXpDerivesfromScoringConstants:
    """Goal / assist components must equal g90 * m * GOAL_POINTS[pos] / ASSIST_POINTS[pos]
    imported from scoring_football — no hardcoded coefficients allowed."""

    _POSITIONS = [
        ("Attacker", Position.FWD),
        ("Midfielder", Position.MID),
        ("Defender", Position.DEF),
        ("Goalkeeper", Position.GK),
    ]

    def _goal_only_xp(self, pos_str: str, pos: Position) -> float:
        # opponent_lambda=100 → p_cs ≈ 0, isolating goal + floor terms
        return _xp_formula(
            g90=1.0, a90=0.0, expected_minutes=90, opponent_lambda=100.0, position=pos_str
        )

    def _assist_only_xp(self, pos_str: str, pos: Position) -> float:
        return _xp_formula(
            g90=0.0, a90=1.0, expected_minutes=90, opponent_lambda=100.0, position=pos_str
        )

    def _gk_pen_offset(self, pos: Position) -> float:
        """GK gets an additive pen-save term; non-zero only for GK."""
        return EXPECTED_PEN_SAVES_PER_MATCH * PEN_SAVE_POINTS if pos == Position.GK else 0.0

    def test_goal_component_matches_scoring_table(self):
        for pos_str, pos in self._POSITIONS:
            xp = self._goal_only_xp(pos_str, pos)
            expected = FLOOR_POINTS + GOAL_POINTS[pos] + self._gk_pen_offset(pos)
            assert abs(xp - expected) < 0.1, (
                f"{pos_str}: expected {expected}, got {xp}"
            )

    def test_assist_component_matches_scoring_table(self):
        for pos_str, pos in self._POSITIONS:
            xp = self._assist_only_xp(pos_str, pos)
            expected = FLOOR_POINTS + ASSIST_POINTS[pos] + self._gk_pen_offset(pos)
            assert abs(xp - expected) < 0.1, (
                f"{pos_str}: expected {expected}, got {xp}"
            )


class TestDefenderGoalOutweighsForwardGoal:
    """A DEF and FWD with identical rates/minutes must have DEF goal-XP > FWD goal-XP.

    Locks the inversion fix: DEF goal = 25 pts, FWD goal = 10 pts.
    """

    def test_defender_goal_component_exceeds_forward(self):
        def_xp = _xp_formula(g90=1.0, a90=0.0, expected_minutes=90, opponent_lambda=100.0, position="Defender")
        fwd_xp = _xp_formula(g90=1.0, a90=0.0, expected_minutes=90, opponent_lambda=100.0, position="Attacker")
        assert def_xp > fwd_xp, f"DEF goal-XP ({def_xp}) must exceed FWD goal-XP ({fwd_xp})"

    def test_ratio_reflects_scoring_table(self):
        def_xp = _xp_formula(g90=1.0, a90=0.0, expected_minutes=90, opponent_lambda=100.0, position="Defender")
        fwd_xp = _xp_formula(g90=1.0, a90=0.0, expected_minutes=90, opponent_lambda=100.0, position="Attacker")
        # DEF goal = 25, FWD goal = 10; difference in XP should be 15 (floor cancels)
        assert abs((def_xp - fwd_xp) - (GOAL_POINTS[Position.DEF] - GOAL_POINTS[Position.FWD])) < 0.1


class TestXpComparableAcrossPositions:
    """Starting CB with no attacking output: XP must be sane (single-digit), not ~100× a FWD.

    Locks the scale-bug fix — no single term should dominate.
    """

    def test_cb_no_attack_xp_is_single_digit(self):
        cb_xp = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=BASE_LAMBDA, position="Defender")
        # Should be roughly FLOOR_POINTS + p_cs * CLEAN_SHEET_POINTS[DEF]
        # ≈ 3 + 0.27 * 6 ≈ 4.6 — well under 15
        assert cb_xp < 15, f"CB no-attack XP={cb_xp} is too large (scale bug)"

    def test_cb_not_orders_of_magnitude_above_forward(self):
        cb_xp = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=BASE_LAMBDA, position="Defender")
        fwd_xp = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=100.0, position="Attacker")
        # FWD floor-only = FLOOR_POINTS; CB shouldn't be 10x that
        assert cb_xp < fwd_xp * 10, f"CB XP={cb_xp} is unreasonably larger than FWD XP={fwd_xp}"


class TestCleanSheetScalesWithFavouritism:
    """A defender on a heavy-favourite team (low opponent lambda) must have higher
    XP than the same defender in an evenly-matched game.

    Team strength enters defensive XP through the clean-sheet term only.
    """

    def test_lower_opponent_lambda_means_higher_defender_xp(self):
        xp_favourite = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=0.5, position="Defender")
        xp_even = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=1.3, position="Defender")
        assert xp_favourite > xp_even, (
            f"Favourite ({xp_favourite}) should exceed evenly-matched ({xp_even})"
        )

    def test_clean_sheet_direction_is_monotone(self):
        xps = [
            _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=lam, position="Defender")
            for lam in [0.3, 0.6, 1.0, 1.5, 2.0]
        ]
        for i in range(len(xps) - 1):
            assert xps[i] > xps[i + 1], (
                f"XP should decrease as opponent_lambda increases; got {xps}"
            )


class TestCleanSheetUsesLambda:
    """p_clean_sheet must equal poisson_pmf(0, opponent_lambda) = e^(-lambda).

    DEF / GK / MID get the term; FWD does not.
    """

    def test_clean_sheet_probability_equals_poisson_zero(self):
        opp_lambda = 1.5
        p_cs = _poisson0(opp_lambda)

        for pos_str, pos in [("Defender", Position.DEF), ("Goalkeeper", Position.GK), ("Midfielder", Position.MID)]:
            xp = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=opp_lambda, position=pos_str)
            expected_cs_component = p_cs * CLEAN_SHEET_POINTS[pos]
            # xp - FLOOR_POINTS ≈ cs_component (g90=a90=0, ignoring optional pen-save)
            residual = xp - FLOOR_POINTS - expected_cs_component
            # allow for optional GK pen-save term (small)
            assert abs(residual) < 0.5, (
                f"{pos_str}: expected cs component {expected_cs_component:.3f}, residual={residual:.3f}"
            )

    def test_forward_gets_no_clean_sheet_term(self):
        p_cs = _poisson0(1.5)
        fwd_xp = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=1.5, position="Attacker")
        # FWD clean sheet points = 0; xp should just be FLOOR_POINTS
        assert abs(fwd_xp - FLOOR_POINTS) < 0.01, (
            f"FWD XP={fwd_xp} should equal FLOOR_POINTS={FLOOR_POINTS} (no clean sheet)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# _blend — WC weight cap
# ══════════════════════════════════════════════════════════════════════════════


class TestWcFormBlendCapped:
    """At wc_games >= 3, WC weight must equal WC_WEIGHT_CAP (0.7), not 1.0.

    Ensures a small WC sample can't fully erase a season of club form.
    """

    def test_wc_weight_caps_at_wc_weight_cap_not_one(self):
        # 3 WC games → without cap, weight = 1.0 (pure WC)
        form = _Form(
            wc_games=3, wc_goals=3, wc_assists=0, wc_minutes=270, wc_clean_sheets=0,
            pre_expected_points=8.0,
        )
        result = _blend(form, "Attacker")
        wc = _wc_xp(form, "Attacker")
        pre = 8.0
        expected = round((1 - WC_WEIGHT_CAP) * pre + WC_WEIGHT_CAP * wc, 2)
        assert abs(result - expected) < 0.05, (
            f"3 WC games: got {result}, expected capped blend {expected}"
        )
        # Must NOT equal pure WC (which the uncapped formula gives)
        assert abs(result - wc) > 0.2, (
            f"WC weight should be capped at {WC_WEIGHT_CAP}, not 1.0; result={result}, pure_wc={wc}"
        )

    def test_more_games_do_not_exceed_cap(self):
        form = _Form(
            wc_games=7, wc_goals=7, wc_assists=0, wc_minutes=630,
            pre_expected_points=8.0,
        )
        result = _blend(form, "Attacker")
        wc = _wc_xp(form, "Attacker")
        pre = 8.0
        expected = round((1 - WC_WEIGHT_CAP) * pre + WC_WEIGHT_CAP * wc, 2)
        assert abs(result - expected) < 0.05

    def test_wc_weight_cap_constant_is_0_7(self):
        assert WC_WEIGHT_CAP == 0.7


# ══════════════════════════════════════════════════════════════════════════════
# Scoreline — symmetric at neutral equal-strength
# ══════════════════════════════════════════════════════════════════════════════


class TestScorelineSymmetricAtNeutralEqualStrength:
    """Equal-strength teams at a neutral venue → home_lambda == away_lambda.

    Locks the home-advantage fix: WC is played at neutral venues.
    """

    def test_equal_rank_produces_equal_lambdas(self):
        home_lambda, away_lambda = _rank_adjusted_lambdas(home_rank=10, away_rank=10)
        assert home_lambda == away_lambda, (
            f"Equal-rank teams: home_lambda={home_lambda} != away_lambda={away_lambda}"
        )

    def test_equal_rank_none_produces_equal_lambdas(self):
        home_lambda, away_lambda = _rank_adjusted_lambdas(home_rank=None, away_rank=None)
        assert home_lambda == away_lambda

    def test_equal_strength_symmetric_win_probabilities(self):
        """When lambdas are equal, P(home wins) ≈ P(away wins)."""
        home_lambda, away_lambda = _rank_adjusted_lambdas(home_rank=10, away_rank=10)
        max_goals = 5
        p_home_win = p_away_win = 0.0
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p = _poisson0(home_lambda) if h == 0 else 1  # placeholder
                # compute directly
                ph = (home_lambda ** h) * math.exp(-home_lambda) / math.factorial(h)
                pa = (away_lambda ** a) * math.exp(-away_lambda) / math.factorial(a)
                joint = ph * pa
                if h > a:
                    p_home_win += joint
                elif a > h:
                    p_away_win += joint
        assert abs(p_home_win - p_away_win) < 1e-9, (
            f"Equal strength: P(home)={p_home_win:.4f} != P(away)={p_away_win:.4f}"
        )

    def test_stronger_home_has_higher_lambda(self):
        """When home side is ranked higher (#5 vs #25), home_lambda > away_lambda."""
        home_lambda, away_lambda = _rank_adjusted_lambdas(home_rank=5, away_rank=25)
        assert home_lambda > away_lambda

    def test_neutral_base_lambda_equals_for_both_sides(self):
        """The base (equal-strength) lambda should be equal for home and away."""
        h, a = _rank_adjusted_lambdas(home_rank=20, away_rank=20)
        assert h == a


# ══════════════════════════════════════════════════════════════════════════════
# Golden values — hand-computed
# ══════════════════════════════════════════════════════════════════════════════


class TestXpGoldens:
    """Hand-computed XP for synthetic players, derived from scoring constants.

    opponent_lambda = 1.3 (neutral venue average), expected_minutes = 90.
    p_cs = exp(-1.3) ≈ 0.2725
    """

    OPP_LAMBDA = 1.3
    P_CS = math.exp(-1.3)  # ≈ 0.2725

    def test_fwd_no_output(self):
        # xp = FLOOR_POINTS (3) + 0 + 0 + 0 (FWD CS=0) = 3.0
        xp = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=self.OPP_LAMBDA, position="Attacker")
        assert abs(xp - FLOOR_POINTS) < 0.01, f"FWD no-output: expected {FLOOR_POINTS}, got {xp}"

    def test_def_no_output(self):
        # xp = 3 + 0 + 0 + 0.2725 * 6 = 3 + 1.635 = 4.635
        expected = FLOOR_POINTS + self.P_CS * CLEAN_SHEET_POINTS[Position.DEF]
        xp = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=self.OPP_LAMBDA, position="Defender")
        assert abs(xp - expected) < 0.02, f"DEF no-output: expected {expected:.3f}, got {xp}"

    def test_mid_one_goal_per_90(self):
        # xp = 3 + 1.0 * 15 + 0 + 0.2725 * 3 = 3 + 15 + 0.818 = 18.818
        expected = FLOOR_POINTS + 1.0 * GOAL_POINTS[Position.MID] + self.P_CS * CLEAN_SHEET_POINTS[Position.MID]
        xp = _xp_formula(g90=1.0, a90=0, expected_minutes=90, opponent_lambda=self.OPP_LAMBDA, position="Midfielder")
        assert abs(xp - expected) < 0.02, f"MID 1g/90: expected {expected:.3f}, got {xp}"

    def test_gk_no_output(self):
        # xp = 3 + 0 + 0 + 0.2725 * 6 = 4.635 (+small pen-save term, optional)
        expected_base = FLOOR_POINTS + self.P_CS * CLEAN_SHEET_POINTS[Position.GK]
        xp = _xp_formula(g90=0, a90=0, expected_minutes=90, opponent_lambda=self.OPP_LAMBDA, position="Goalkeeper")
        # Allow up to 0.5 for the optional pen-save term
        assert xp >= expected_base - 0.01, f"GK no-output xp={xp} is below base {expected_base:.3f}"
        assert xp < expected_base + 0.5, f"GK no-output xp={xp} suspiciously high above base {expected_base:.3f}"
