"""Unit tests for the football (WC2026) scoring engine.

Every number here is lifted directly from the scoring spec — the §3 result/
scoreline ladder tables and the §8 worked examples, which the spec designates as
the integration test fixtures. If the spec is re-tuned, these are the tests to
update.
"""

import pytest

from app.services.scoring_football import (
    TEAM1,
    TEAM2,
    MatchResult,
    PlayerMatchEvents,
    Position,
    ScorelinePrediction,
    compute_match_score,
    compute_player_score,
    compute_result_score,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# §3 — Result & scoreline ladder
# ---------------------------------------------------------------------------
class TestResultScoreGroupStage:
    """Group stage: Netherlands (team1) 2-1 Ecuador (team2). Spec §3 examples."""

    RESULT = MatchResult(stage="GROUP", team1_goals_reg=2, team2_goals_reg=1)

    def test_exact_scoreline_correct_result(self):
        # Netherlands 2-1: result ✓, both scores → 5 + 10 = 15
        pred = ScorelinePrediction(team1_goals=2, team2_goals=1)
        assert compute_result_score(pred, self.RESULT) == 15

    def test_correct_result_one_score(self):
        # Netherlands 3-1: result ✓, Ecuador score only → 5 + 5 = 10
        pred = ScorelinePrediction(team1_goals=3, team2_goals=1)
        assert compute_result_score(pred, self.RESULT) == 10

    def test_draw_prediction_still_scores_matching_team(self):
        # "Draw 1-1": wrong result, but Ecuador's actual 1 == predicted 1 → +5.
        # NB: the §3 illustrative table labels this row "None / 0", which is
        # inconsistent with both the §3 code formula and §8's User B (which
        # explicitly awards "+5 Ecuador score correct"). The formula and the
        # §8 fixtures are authoritative; scoreline credit is per-team independent.
        pred = ScorelinePrediction(team1_goals=1, team2_goals=1)
        assert compute_result_score(pred, self.RESULT) == 5

    def test_no_scores_match(self):
        # 3-3: wrong result (draw vs Neth win) and neither score matches → 0
        pred = ScorelinePrediction(team1_goals=3, team2_goals=3)
        assert compute_result_score(pred, self.RESULT) == 0

    def test_wrong_result_but_one_score_matches(self):
        # Wrong result (Ecuador win predicted), but Netherlands' 2 is correct → 5
        pred = ScorelinePrediction(team1_goals=2, team2_goals=3)
        assert compute_result_score(pred, self.RESULT) == 5


class TestResultScoreKnockout:
    """Knockout: Brazil (team1) vs France (team2). 90'=1-1, ET=2-2, France wins
    on pens. result = France advances; scoreline = 2-2. Spec §3 examples."""

    RESULT = MatchResult(
        stage="QF",
        team1_goals_reg=1,
        team2_goals_reg=1,
        team1_goals_et=2,
        team2_goals_et=2,
        shootout_winner=TEAM2,  # France
    )

    def test_france_2_1_win(self):
        # France 2-1 win: team1(Brazil)=1, team2(France)=2. Result ✓ (France
        # advances), France's 2 matches the ET 2 → 5 + 5 = 10
        pred = ScorelinePrediction(team1_goals=1, team2_goals=2)
        assert compute_result_score(pred, self.RESULT) == 10

    def test_france_2_2_win_both_scores(self):
        # France 2-2 win: draw scoreline + advance pick France. Result ✓, both
        # scores ✓ → 5 + 10 = 15
        pred = ScorelinePrediction(team1_goals=2, team2_goals=2, advance_winner=TEAM2)
        assert compute_result_score(pred, self.RESULT) == 15

    def test_draw_2_2_both_scores(self):
        # Draw 2-2 (no advance pick → predicts neither advances): result ✗ but
        # both scores ✓ → 0 + 10 = 10
        pred = ScorelinePrediction(team1_goals=2, team2_goals=2, advance_winner=None)
        assert compute_result_score(pred, self.RESULT) == 10

    def test_brazil_3_1_win_nothing(self):
        # Brazil 3-1 win: wrong result, no score matches → 0
        pred = ScorelinePrediction(team1_goals=3, team2_goals=1)
        assert compute_result_score(pred, self.RESULT) == 0


# ---------------------------------------------------------------------------
# §4 / §8 — Player event scoring
# ---------------------------------------------------------------------------
class TestPlayerScore:
    def test_fwd_goal_and_assist(self):
        # Memphis Depay: FWD, 90', 1G + 1A → 3 + 10 + 5 = 18
        ev = PlayerMatchEvents(Position.FWD, minutes_played=90, goals=1, assists=1)
        assert compute_player_score(ev) == 18

    def test_def_goal_no_clean_sheet(self):
        # Van Dijk: DEF, 90', 1G, team conceded 1 → 3 + 25 = 28
        ev = PlayerMatchEvents(
            Position.DEF, minutes_played=90, goals=1, team_goals_conceded=1
        )
        assert compute_player_score(ev) == 28

    def test_mid_assist_no_clean_sheet(self):
        # De Jong: MID, 90', 1A, conceded 1 → 3 + 10 = 13
        ev = PlayerMatchEvents(
            Position.MID, minutes_played=90, assists=1, team_goals_conceded=1
        )
        assert compute_player_score(ev) == 13

    def test_def_assist_no_clean_sheet(self):
        # Estupiñán: DEF, 90', 1A, conceded 2 → 3 + 12 = 15
        ev = PlayerMatchEvents(
            Position.DEF, minutes_played=90, assists=1, team_goals_conceded=2
        )
        assert compute_player_score(ev) == 15

    def test_sub_floor_only(self):
        # Gakpo: FWD, 75', no events → 3
        ev = PlayerMatchEvents(Position.FWD, minutes_played=75)
        assert compute_player_score(ev) == 3

    def test_gk_shootout_pen_save_no_clean_sheet(self):
        # Maignan: GK, 120', 1 shootout pen save, conceded 2 → 3 + 5 = 8
        ev = PlayerMatchEvents(
            Position.GK,
            minutes_played=120,
            shootout_pen_saves=1,
            team_goals_conceded=2,
        )
        assert compute_player_score(ev) == 8

    def test_fwd_goal_with_shootout_miss_not_penalised(self):
        # Vinicius: FWD, 120', 1G, missed shootout pen (no deduction) → 3 + 10 = 13
        ev = PlayerMatchEvents(Position.FWD, minutes_played=120, goals=1)
        assert compute_player_score(ev) == 13

    def test_mid_goal_in_et(self):
        # Camavinga: MID, 120', 1G (in ET counts normally), team conceded 2
        # (no clean sheet) → 3 + 15 = 18
        ev = PlayerMatchEvents(
            Position.MID, minutes_played=120, goals=1, team_goals_conceded=2
        )
        assert compute_player_score(ev) == 18

    # --- threshold & clean-sheet edges ---
    def test_under_30_mins_no_floor_but_keeps_events(self):
        # 20', 1G FWD: no +3 floor, but goal still counts → 10
        ev = PlayerMatchEvents(Position.FWD, minutes_played=20, goals=1)
        assert compute_player_score(ev) == 10

    def test_clean_sheet_requires_60_mins(self):
        # DEF 59', conceded 0 → floor only (no CS) = 3
        ev = PlayerMatchEvents(Position.DEF, minutes_played=59, team_goals_conceded=0)
        assert compute_player_score(ev) == 3

    def test_clean_sheet_def(self):
        # DEF 90', conceded 0 → 3 + 6 = 9
        ev = PlayerMatchEvents(Position.DEF, minutes_played=90, team_goals_conceded=0)
        assert compute_player_score(ev) == 9

    def test_clean_sheet_fwd_is_zero_bonus(self):
        # FWD 90', conceded 0 → floor only, CS bonus is 0 for forwards = 3
        ev = PlayerMatchEvents(Position.FWD, minutes_played=90, team_goals_conceded=0)
        assert compute_player_score(ev) == 3

    def test_gk_ingame_pen_save_and_clean_sheet(self):
        # GK 90', in-game pen save + clean sheet → 3 + 5 + 6 = 14
        ev = PlayerMatchEvents(
            Position.GK, minutes_played=90, ingame_pen_saves=1, team_goals_conceded=0
        )
        assert compute_player_score(ev) == 14

    def test_negatives_stack(self):
        # MID 90', red card + own goal + in-game pen miss → 3 - 3 - 3 - 3 = -6
        ev = PlayerMatchEvents(
            Position.MID,
            minutes_played=90,
            red_card=True,
            own_goals=1,
            ingame_pen_misses=1,
            team_goals_conceded=1,
        )
        assert compute_player_score(ev) == -6


# ---------------------------------------------------------------------------
# §8 — Full worked examples (designated integration fixtures)
# ---------------------------------------------------------------------------
class TestWorkedExampleGroupStage:
    """Example 1 — Netherlands 2-1 Ecuador (group stage, no multiplier)."""

    RESULT = MatchResult(stage="GROUP", team1_goals_reg=2, team2_goals_reg=1)

    def test_user_a_score_74(self):
        pred = ScorelinePrediction(team1_goals=2, team2_goals=1)  # Netherlands 2-1
        picks = [
            PlayerMatchEvents(Position.FWD, 90, goals=1, assists=1),  # Depay 18
            PlayerMatchEvents(Position.DEF, 90, goals=1, team_goals_conceded=1),  # VVD 28
            PlayerMatchEvents(Position.MID, 90, assists=1, team_goals_conceded=1),  # De Jong 13
        ]
        assert compute_match_score(pred, picks, self.RESULT) == 74

    def test_user_b_score_71(self):
        pred = ScorelinePrediction(team1_goals=3, team2_goals=1)  # Netherlands 3-1
        picks = [
            PlayerMatchEvents(Position.FWD, 90, goals=1, assists=1),  # Depay 18
            PlayerMatchEvents(Position.DEF, 90, goals=1, team_goals_conceded=1),  # VVD 28
            PlayerMatchEvents(Position.DEF, 90, assists=1, team_goals_conceded=2),  # Estupiñán 15
        ]
        assert compute_match_score(pred, picks, self.RESULT) == 71

    def test_user_d_score_31(self):
        pred = ScorelinePrediction(team1_goals=0, team2_goals=2)  # Ecuador 2-0
        picks = [
            PlayerMatchEvents(Position.FWD, 75),  # Gakpo 3
            PlayerMatchEvents(Position.FWD, 90, goals=1),  # Valencia 13
            PlayerMatchEvents(Position.DEF, 90, assists=1, team_goals_conceded=2),  # Estupiñán 15
        ]
        assert compute_match_score(pred, picks, self.RESULT) == 31


class TestWorkedExampleKnockout:
    """Example 2 — Brazil vs France QF. ET 2-2, France wins on pens. 2× applies."""

    RESULT = MatchResult(
        stage="QF",
        team1_goals_reg=1,
        team2_goals_reg=1,
        team1_goals_et=2,
        team2_goals_et=2,
        shootout_winner=TEAM2,  # France
    )

    def test_user_a_score_118(self):
        # France 2-1 win → team1(Brazil)=1, team2(France)=2
        pred = ScorelinePrediction(team1_goals=1, team2_goals=2)
        # France conceded 2, so no clean sheets.
        picks = [
            PlayerMatchEvents(Position.FWD, 120, goals=1, assists=1, team_goals_conceded=2),  # Mbappé 18
            PlayerMatchEvents(Position.MID, 120, goals=1, team_goals_conceded=2),  # Camavinga 18
            PlayerMatchEvents(Position.FWD, 120, goals=1, team_goals_conceded=2),  # Vinicius 13 (shootout miss free)
        ]
        # (10 + 49) * 2 = 118
        assert compute_match_score(pred, picks, self.RESULT) == 118

    def test_user_c_score_88(self):
        # France 2-2 win → draw scoreline, advance pick France
        pred = ScorelinePrediction(team1_goals=2, team2_goals=2, advance_winner=TEAM2)
        picks = [
            PlayerMatchEvents(Position.FWD, 120, goals=1, assists=1, team_goals_conceded=2),  # Mbappé 18
            PlayerMatchEvents(Position.GK, 120, shootout_pen_saves=1, team_goals_conceded=2),  # Maignan 8
            PlayerMatchEvents(Position.MID, 120, team_goals_conceded=2),  # Casemiro 3
        ]
        # (15 + 29) * 2 = 88
        assert compute_match_score(pred, picks, self.RESULT) == 88

    def test_knockout_multiplier_applies_to_total(self):
        # Sanity: same picks in a group stage would be (15 + 29) = 44, not 88.
        group_result = MatchResult(stage="GROUP", team1_goals_reg=2, team2_goals_reg=2)
        pred = ScorelinePrediction(team1_goals=2, team2_goals=2)
        picks = [
            PlayerMatchEvents(Position.FWD, 120, goals=1, assists=1, team_goals_conceded=2),
            PlayerMatchEvents(Position.GK, 120, shootout_pen_saves=1, team_goals_conceded=2),
            PlayerMatchEvents(Position.MID, 120, team_goals_conceded=2),
        ]
        assert compute_match_score(pred, picks, group_result) == 44
