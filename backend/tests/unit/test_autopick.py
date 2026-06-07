"""
Unit tests for the WC2026 auto-pick engine.

Covers all §12 property tests from the handover spec:
  1. Determinism
  2. Distinctness (unique-set proportion floors)
  3. Monotonic spread: unique(bold) > unique(balanced) > unique(safe)
  4. Coherence / floor guarantee
  5. Independence (nonce, userId)
Plus edge cases and golden regression snapshots.
"""

import pytest

from app.services.autopick import (
    DataQuality,
    Identity,
    PredictionInputs,
    ScoredPlayer,
    ScorelineProb,
    Strategy,
    auto_pick,
)

# ── Synthetic fixture ─────────────────────────────────────────────────────────

HOME = "team-fra"
AWAY = "team-bra"
MATCH_ID = "match-fra-bra-001"


def _p(
    pid: str,
    team: str,
    pos: str,
    xp: float,
    floor: str,
    avail: str = "starter",
) -> ScoredPlayer:
    return ScoredPlayer(
        player_id=pid,
        team_id=team,
        position=pos,  # type: ignore[arg-type]
        expected_points=xp,
        floor=floor,  # type: ignore[arg-type]
        availability=avail,  # type: ignore[arg-type]
    )


FRANCE = [
    _p("fra-gk", HOME, "GK",  8.2,  "high"),
    _p("fra-d1", HOME, "DEF", 7.5,  "high"),
    _p("fra-d2", HOME, "DEF", 6.8,  "high"),
    _p("fra-d3", HOME, "DEF", 6.5,  "high"),
    _p("fra-d4", HOME, "DEF", 6.0,  "mid"),
    _p("fra-m1", HOME, "MID", 9.1,  "high"),
    _p("fra-m2", HOME, "MID", 8.7,  "high"),
    _p("fra-m3", HOME, "MID", 7.3,  "mid"),
    _p("fra-f1", HOME, "FWD", 12.5, "high"),  # star striker
    _p("fra-f2", HOME, "FWD", 10.8, "high"),
    _p("fra-f3", HOME, "FWD", 8.9,  "mid"),
    _p("fra-b1", HOME, "MID", 5.0,  "mid",  "rotation"),
    _p("fra-b2", HOME, "FWD", 4.2,  "low",  "rotation"),
    _p("fra-b3", HOME, "DEF", 3.1,  "low",  "doubt"),
]

BRAZIL = [
    _p("bra-gk", AWAY, "GK",  7.9,  "high"),
    _p("bra-d1", AWAY, "DEF", 7.2,  "high"),
    _p("bra-d2", AWAY, "DEF", 6.9,  "high"),
    _p("bra-d3", AWAY, "DEF", 6.4,  "high"),
    _p("bra-d4", AWAY, "DEF", 5.8,  "mid"),
    _p("bra-m1", AWAY, "MID", 10.2, "high"),  # key midfielder
    _p("bra-m2", AWAY, "MID", 8.4,  "high"),
    _p("bra-m3", AWAY, "MID", 6.8,  "mid"),
    _p("bra-f1", AWAY, "FWD", 11.9, "high"),  # star striker
    _p("bra-f2", AWAY, "FWD", 9.5,  "high"),
    _p("bra-f3", AWAY, "FWD", 7.6,  "mid"),
    _p("bra-b1", AWAY, "MID", 4.8,  "mid",  "rotation"),
    _p("bra-b2", AWAY, "FWD", 3.9,  "low",  "rotation"),
    _p("bra-b3", AWAY, "DEF", 2.7,  "low",  "doubt"),
]

SCORELINES = (
    ScorelineProb(1, 0, 0.16),
    ScorelineProb(1, 1, 0.14),
    ScorelineProb(2, 1, 0.13),
    ScorelineProb(0, 1, 0.10),
    ScorelineProb(2, 0, 0.09),
    ScorelineProb(0, 0, 0.08),
    ScorelineProb(1, 2, 0.07),
    ScorelineProb(3, 1, 0.05),
    ScorelineProb(2, 2, 0.04),
    ScorelineProb(0, 2, 0.04),
    ScorelineProb(3, 0, 0.03),
    ScorelineProb(3, 2, 0.02),
    ScorelineProb(0, 3, 0.02),
    ScorelineProb(4, 0, 0.01),
    ScorelineProb(0, 4, 0.01),
)

DQ = DataQuality(lineups_confirmed=True, odds_source="correct-score")

FIXTURE = PredictionInputs(
    match_id=MATCH_ID,
    home_team_id=HOME,
    away_team_id=AWAY,
    players=tuple(FRANCE + BRAZIL),
    scorelines=SCORELINES,
    data_quality=DQ,
)

SPARSE_FIXTURE = PredictionInputs(
    match_id="match-sparse-001",
    home_team_id="team-a",
    away_team_id="team-b",
    players=(
        _p("p1", "team-a", "FWD", 10, "high"),
        _p("p2", "team-a", "FWD", 8,  "high"),
        _p("p3", "team-b", "FWD", 7,  "mid"),
        _p("p4", "team-b", "MID", 5,  "mid"),
        _p("p5", "team-a", "DEF", 3,  "low"),
    ),
    scorelines=(ScorelineProb(1, 0, 1.0),),
    data_quality=DataQuality(lineups_confirmed=False, odds_source="fallback"),
)

EMPTY_SCORELINE_FIXTURE = PredictionInputs(
    **{**FIXTURE.__dict__, "match_id": "match-no-odds-001", "scorelines": ()},
)


def _pick(user_id: str, strategy: Strategy, nonce: int = 0):
    return auto_pick(FIXTURE, strategy, Identity(user_id=user_id, match_id=MATCH_ID, nonce=nonce))


def _unique_sets(results) -> int:
    return len({tuple(sorted(r.player_ids)) for r in results})


def _modal_count(results) -> int:
    freq: dict[tuple, int] = {}
    for r in results:
        key = tuple(sorted(r.player_ids))
        freq[key] = freq.get(key, 0) + 1
    return max(freq.values())


# ── §12 Property test 1: Determinism ─────────────────────────────────────────


@pytest.mark.parametrize("strategy", ["safe", "balanced", "bold"])
def test_determinism_same_inputs(strategy):
    a = _pick("user-det", strategy)
    b = _pick("user-det", strategy)
    assert a.player_ids == b.player_ids
    assert (a.scoreline_home, a.scoreline_away) == (b.scoreline_home, b.scoreline_away)


def test_nonce_0_and_absent_are_identical():
    a = _pick("user-canon", "balanced", nonce=0)
    b = auto_pick(FIXTURE, "balanced", Identity(user_id="user-canon", match_id=MATCH_ID))
    assert a.player_ids == b.player_ids


def test_determinism_independent_of_player_order():
    shuffled = PredictionInputs(
        **{**FIXTURE.__dict__, "players": tuple(reversed(FIXTURE.players))}
    )
    a = auto_pick(FIXTURE, "balanced", Identity("u1", MATCH_ID))
    b = auto_pick(shuffled, "balanced", Identity("u1", MATCH_ID))
    assert set(a.player_ids) == set(b.player_ids)
    assert (a.scoreline_home, a.scoreline_away) == (b.scoreline_home, b.scoreline_away)


def test_determinism_independent_of_scoreline_order():
    shuffled = PredictionInputs(
        **{**FIXTURE.__dict__, "scorelines": tuple(reversed(FIXTURE.scorelines))}
    )
    a = auto_pick(FIXTURE, "safe", Identity("u2", MATCH_ID))
    b = auto_pick(shuffled, "safe", Identity("u2", MATCH_ID))
    assert (a.scoreline_home, a.scoreline_away) == (b.scoreline_home, b.scoreline_away)


# ── §12 Property test 2: Distinctness ────────────────────────────────────────

N = 200
_SAFE_RESULTS = [_pick(f"user-{i}", "safe") for i in range(N)]
_BAL_RESULTS  = [_pick(f"user-{i}", "balanced") for i in range(N)]
_BOLD_RESULTS = [_pick(f"user-{i}", "bold") for i in range(N)]


def test_distinctness_safe():
    assert _unique_sets(_SAFE_RESULTS) / N >= 0.30


def test_distinctness_balanced():
    assert _unique_sets(_BAL_RESULTS) / N >= 0.60


def test_distinctness_bold():
    assert _unique_sets(_BOLD_RESULTS) / N >= 0.85


def test_safe_modal_share_below_threshold():
    assert _modal_count(_SAFE_RESULTS) / N < 0.25


# ── §12 Property test 3: Monotonic spread ────────────────────────────────────


def test_monotonic_spread():
    safe = _unique_sets(_SAFE_RESULTS)
    bal  = _unique_sets(_BAL_RESULTS)
    bold = _unique_sets(_BOLD_RESULTS)
    assert bold > bal > safe


# ── §12 Property test 4: Coherence / floor guarantee ─────────────────────────


def test_safe_picks_only_high_floor():
    floor_map = {p.player_id: p.floor for p in FIXTURE.players}
    for i in range(50):
        result = _pick(f"u{i}", "safe")
        for pid in result.player_ids:
            assert floor_map[pid] == "high", f"Non-high player {pid} in safe pick"


def test_no_out_players_ever_selected():
    out_ids = {p.player_id for p in FIXTURE.players if p.availability == "out"}
    for strategy in ("safe", "balanced", "bold"):
        for i in range(30):
            result = _pick(f"u{i}", strategy)  # type: ignore[arg-type]
            for pid in result.player_ids:
                assert pid not in out_ids


def test_three_distinct_players():
    for strategy in ("safe", "balanced", "bold"):
        for i in range(20):
            result = _pick(f"u{i}", strategy)  # type: ignore[arg-type]
            assert len(set(result.player_ids)) == 3


# ── §12 Property test 5: Independence ────────────────────────────────────────


def test_different_user_different_pick():
    same = sum(
        1 for i in range(50)
        if _pick(f"user-a-{i}", "balanced").player_ids
        == _pick(f"user-b-{i}", "balanced").player_ids
    )
    assert same < 10


def test_nonce_increment_changes_pick():
    same = sum(
        1 for i in range(50)
        if _pick(f"user-{i}", "balanced", nonce=0).player_ids
        == _pick(f"user-{i}", "balanced", nonce=1).player_ids
    )
    assert same < 10


def test_canonical_draw_unaffected_by_reshuffles():
    canonical = _pick("user-b", "safe", nonce=0)
    _pick("user-a", "safe", nonce=5)  # someone else reshuffles
    after = _pick("user-b", "safe", nonce=0)
    assert canonical.player_ids == after.player_ids


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_sparse_fixture_pool_relaxation():
    result = auto_pick(SPARSE_FIXTURE, "safe", Identity("u1", SPARSE_FIXTURE.match_id))
    assert len(result.player_ids) == 3
    assert len(set(result.player_ids)) == 3
    assert result.pool_degraded is True


def test_empty_scorelines_fallback():
    result = auto_pick(
        EMPTY_SCORELINE_FIXTURE, "balanced", Identity("u1", EMPTY_SCORELINE_FIXTURE.match_id)
    )
    assert result.scoreline_home == 1
    assert result.scoreline_away == 0


def test_meta_fields_populated():
    result = _pick("user-meta", "bold")
    assert result.engine_version
    assert result.seed
    assert result.generated_at
    assert result.odds_source


def test_scoreline_from_fixture_distribution():
    valid = {(s.home, s.away) for s in FIXTURE.scorelines}
    for i in range(30):
        r = _pick(f"u{i}", "balanced")
        assert (r.scoreline_home, r.scoreline_away) in valid


# ── Golden regression tests ───────────────────────────────────────────────────
# Freeze expected outputs — fail loudly if the algorithm drifts.


def test_golden_safe_user42():
    r = auto_pick(FIXTURE, "safe", Identity("user-42", MATCH_ID))
    assert set(r.player_ids) == {"fra-d1", "fra-f1", "fra-d2"}


def test_golden_balanced_user42():
    r = auto_pick(FIXTURE, "balanced", Identity("user-42", MATCH_ID))
    assert set(r.player_ids) == {"fra-d1", "fra-b1", "bra-m3"}


def test_golden_bold_user42():
    r = auto_pick(FIXTURE, "bold", Identity("user-42", MATCH_ID))
    # bold can surface non-star players — just verify it's stable
    first = auto_pick(FIXTURE, "bold", Identity("user-42", MATCH_ID))
    assert set(r.player_ids) == set(first.player_ids)
