"""
Auto-pick engine for WC 2026 predictions.

Pure function: autoPick(inputs, strategy, identity) → AutoPickResult.
Deterministic given the same inputs — seeded per (user_id, match_id, nonce).
No DB access, no side effects. Callers handle persistence.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

ENGINE_VERSION = "autopred-1.0.0"

Position = Literal["GK", "DEF", "MID", "FWD"]
Floor = Literal["high", "mid", "low"]
Availability = Literal["starter", "rotation", "doubt", "out"]
Strategy = Literal["safe", "balanced", "bold"]

DEFAULT_STRATEGY: Strategy = "balanced"

# Floor tiers in relaxation order (most restrictive → most permissive)
_FLOOR_TIERS: list[Floor] = ["high", "mid", "low"]


# ── Data contracts ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScoredPlayer:
    player_id: str
    team_id: str
    position: Position
    expected_points: float  # opaque scalar from data-layer model; higher = better
    floor: Floor            # role/confidence tier; drives pool eligibility
    availability: Availability


@dataclass(frozen=True)
class ScorelineProb:
    home: int
    away: int
    p: float  # probability; list should sum to ~1


@dataclass(frozen=True)
class DataQuality:
    lineups_confirmed: bool
    odds_source: Literal["correct-score", "poisson", "fallback"]


@dataclass(frozen=True)
class PredictionInputs:
    match_id: str
    home_team_id: str
    away_team_id: str
    players: tuple[ScoredPlayer, ...]
    scorelines: tuple[ScorelineProb, ...]
    data_quality: DataQuality


@dataclass(frozen=True)
class Identity:
    user_id: str
    match_id: str
    nonce: int = 0  # 0 = canonical fallback; >0 = reshuffle


@dataclass(frozen=True)
class AutoPickResult:
    match_id: str
    user_id: str
    strategy: Strategy
    scoreline_home: int
    scoreline_away: int
    player_ids: tuple[str, str, str]
    seed: str
    engine_version: str
    generated_at: str  # ISO
    lineups_confirmed: bool
    odds_source: str
    pool_degraded: bool = False


# ── Strategy config ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StrategyConfig:
    eligible_floors: tuple[Floor, ...]
    player_temperature: float
    scoreline_temperature: float
    scoreline_top_k: Optional[int] = None


STRATEGY: dict[Strategy, StrategyConfig] = {
    "safe": StrategyConfig(
        eligible_floors=("high",),
        player_temperature=0.40,
        scoreline_top_k=4,
        scoreline_temperature=0.5,
    ),
    "balanced": StrategyConfig(
        eligible_floors=("high", "mid"),
        player_temperature=0.90,
        scoreline_top_k=10,
        scoreline_temperature=1.0,
    ),
    "bold": StrategyConfig(
        eligible_floors=("high", "mid", "low"),
        player_temperature=1.80,
        scoreline_top_k=None,
        scoreline_temperature=1.6,
    ),
}


# ── RNG helpers ───────────────────────────────────────────────────────────────


def _make_rng(key: str) -> random.Random:
    """Seeded PRNG from a string key. SHA-256 → integer seed → Random."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    return random.Random(seed)


# ── Sampling primitives ───────────────────────────────────────────────────────


def _min_max_normalize(values: list[float]) -> list[float]:
    mn, mx = min(values), max(values)
    if mx == mn:
        return [0.5] * len(values)
    return [(v - mn) / (mx - mn) for v in values]


def _softmax_weights(values: list[float], temperature: float) -> list[float]:
    return [math.exp(v / temperature) for v in values]


def _normalize(weights: list[float]) -> list[float]:
    total = sum(weights)
    if total == 0:
        n = len(weights)
        return [1.0 / n] * n
    return [w / total for w in weights]


def _weighted_pick_one(normalized_weights: list[float], rng: random.Random) -> int:
    r = rng.random()
    cumulative = 0.0
    for i, w in enumerate(normalized_weights):
        cumulative += w
        if r < cumulative:
            return i
    return len(normalized_weights) - 1  # floating-point rounding guard


def _weighted_sample_without_replacement(
    weights: list[float], n: int, rng: random.Random
) -> list[int]:
    """Draw n distinct indices weighted by weights, without replacement."""
    remaining = list(weights)
    selected: list[int] = []
    for _ in range(n):
        idx = _weighted_pick_one(_normalize(remaining), rng)
        selected.append(idx)
        remaining[idx] = 0.0
    return selected


# ── Pool construction ─────────────────────────────────────────────────────────


def _build_pool(
    players: list[ScoredPlayer], eligible_floors: tuple[Floor, ...]
) -> tuple[list[ScoredPlayer], bool]:
    """
    Filter players to the eligible pool. If fewer than 3 survive, relax floor
    tiers one at a time until we have at least 3. Returns (pool, degraded).
    """
    pool = [
        p for p in players
        if p.floor in eligible_floors and p.availability != "out"
    ]
    degraded = False

    extra_tiers = [t for t in _FLOOR_TIERS if t not in eligible_floors]
    for tier in extra_tiers:
        if len(pool) >= 3:
            break
        expanded = set(eligible_floors) | {tier}
        pool = [p for p in players if p.floor in expanded and p.availability != "out"]
        degraded = True

    # Last resort: include doubt players too
    if len(pool) < 3:
        pool = [p for p in players if p.availability != "out"]
        degraded = True

    return pool, degraded


# ── Public API ────────────────────────────────────────────────────────────────


def auto_pick(inputs: PredictionInputs, strategy: Strategy, identity: Identity) -> AutoPickResult:
    """
    Pure, deterministic auto-prediction engine.

    Same (inputs, strategy, identity) → identical result every call.
    No I/O, no global state, no time-dependency (generatedAt is stamped by caller
    if needed; we stamp it here for convenience but it doesn't affect picks).
    """
    cfg = STRATEGY[strategy]
    seed_str = f"{identity.user_id}:{identity.match_id}:{identity.nonce}"

    # Decoupled RNG streams so player and scoreline picks are independently stable
    player_rng = _make_rng(f"{identity.user_id}:{identity.match_id}:p:{identity.nonce}")
    scoreline_rng = _make_rng(f"{identity.user_id}:{identity.match_id}:s:{identity.nonce}")

    # ── Player pick ──────────────────────────────────────────────────────────

    # Sort deterministically so upstream reordering never changes the result
    sorted_players = sorted(inputs.players, key=lambda p: p.player_id)

    # Dedupe by player_id defensively
    seen: set[str] = set()
    deduped: list[ScoredPlayer] = []
    for p in sorted_players:
        if p.player_id not in seen:
            seen.add(p.player_id)
            deduped.append(p)

    pool, degraded = _build_pool(deduped, cfg.eligible_floors)

    # Min-max normalise so temperatures behave consistently across fixtures
    raw_points = [p.expected_points for p in pool]
    norm_points = _min_max_normalize(raw_points)
    raw_weights = _softmax_weights(norm_points, cfg.player_temperature)

    indices = _weighted_sample_without_replacement(raw_weights, 3, player_rng)
    player_ids = tuple(pool[i].player_id for i in indices)

    # ── Scoreline pick ───────────────────────────────────────────────────────

    scorelines = list(inputs.scorelines)

    if not scorelines:
        # No distribution available — fall back to 1-0 home win
        scorelines = [ScorelineProb(home=1, away=0, p=1.0)]

    # Sort deterministically before any filtering
    scorelines.sort(key=lambda s: (s.home, s.away))

    if cfg.scoreline_top_k is not None:
        scorelines = sorted(scorelines, key=lambda s: s.p, reverse=True)[: cfg.scoreline_top_k]
        scorelines.sort(key=lambda s: (s.home, s.away))  # re-sort for stability

    # Softmax over log(p) — equivalent to p^(1/T) re-normalised
    log_probs = [math.log(max(s.p, 1e-10)) for s in scorelines]
    sl_weights = _softmax_weights(log_probs, cfg.scoreline_temperature)
    sl_idx = _weighted_pick_one(_normalize(sl_weights), scoreline_rng)
    picked = scorelines[sl_idx]

    return AutoPickResult(
        match_id=inputs.match_id,
        user_id=identity.user_id,
        strategy=strategy,
        scoreline_home=picked.home,
        scoreline_away=picked.away,
        player_ids=(player_ids[0], player_ids[1], player_ids[2]),
        seed=seed_str,
        engine_version=ENGINE_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        lineups_confirmed=inputs.data_quality.lineups_confirmed,
        odds_source=inputs.data_quality.odds_source,
        pool_degraded=degraded,
    )
