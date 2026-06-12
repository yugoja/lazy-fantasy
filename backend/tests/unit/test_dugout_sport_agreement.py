"""Dugout agreement/contrarian must be sport-aware and never count null==null.

Regression: a football match leaking into a cricket league produced bogus
"6/6 agree" events because every cricket field was null on both sides.
"""
from types import SimpleNamespace as NS

from app.services.dugout import _count_agreement, _called_winner_id


def _match(sport, t1=1, t2=2):
    return NS(tournament=NS(sport=sport), team_1_id=t1, team_2_id=t2)


def _cricket(win=None, r1=None, r2=None, w1=None, w2=None, pom=None):
    return NS(
        predicted_winner_id=win,
        predicted_most_runs_team1_player_id=r1,
        predicted_most_runs_team2_player_id=r2,
        predicted_most_wickets_team1_player_id=w1,
        predicted_most_wickets_team2_player_id=w2,
        predicted_pom_player_id=pom,
    )


def _football(t1, t2, picks, adv=None):
    return NS(football=NS(
        team1_goals=t1, team2_goals=t2, advance_winner_id=adv,
        player_pick_1_id=picks[0], player_pick_2_id=picks[1], player_pick_3_id=picks[2],
    ))


class TestCountAgreement:
    def test_cricket_nulls_are_not_agreement(self):
        # Two empty predictions used to score 6/6 — must now be 0/6.
        empty = _cricket()
        assert _count_agreement(empty, empty, _match("cricket")) == (0, 6)

    def test_cricket_counts_only_real_matches(self):
        a = _cricket(win=5, r1=10, pom=7)
        b = _cricket(win=5, r1=10, pom=99)  # agree on winner + r1, differ on pom
        assert _count_agreement(a, b, _match("cricket")) == (2, 6)

    def test_football_scoreline_and_picks(self):
        a = _football(2, 1, [10, 11, 12])
        b = _football(2, 1, [10, 99, 98])  # same score + 1 shared pick
        assert _count_agreement(a, b, _match("football")) == (2, 4)

    def test_football_no_agreement(self):
        a = _football(2, 1, [10, 11, 12])
        b = _football(0, 0, [20, 21, 22])
        assert _count_agreement(a, b, _match("football")) == (0, 4)

    def test_football_missing_extension(self):
        a = NS(football=None)
        b = _football(1, 0, [1, 2, 3])
        assert _count_agreement(a, b, _match("football")) == (0, 4)


class TestCalledWinner:
    def test_football_from_scoreline(self):
        assert _called_winner_id(_football(2, 1, [1, 2, 3]), _match("football", 7, 8)) == 7
        assert _called_winner_id(_football(0, 3, [1, 2, 3]), _match("football", 7, 8)) == 8

    def test_football_draw_is_none(self):
        assert _called_winner_id(_football(1, 1, [1, 2, 3]), _match("football")) is None

    def test_football_advance_winner_wins(self):
        # knockout draw resolved by advance_winner_id
        assert _called_winner_id(_football(1, 1, [1, 2, 3], adv=8), _match("football", 7, 8)) == 8

    def test_cricket_uses_predicted_winner(self):
        assert _called_winner_id(_cricket(win=42), _match("cricket")) == 42
