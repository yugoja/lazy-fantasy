"""
M2 — Football auto-pick fallback job.

At match lock (kickoff), fills missing football predictions for all members of
football leagues who have not yet submitted a pick. Idempotent: re-running
never creates duplicates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.league import League, LeagueMember
from app.models.match import Match
from app.models.player import Player
from app.models.prediction import Prediction
from app.services.autopick import (
    DEFAULT_STRATEGY,
    DataQuality,
    Identity,
    PredictionInputs,
    ScorelineProb,
    ScoredPlayer,
    Strategy,
    auto_pick,
)
from app.services.prediction import create_football_prediction

# ── Position mapping ──────────────────────────────────────────────────────────

_ROLE_TO_POSITION: dict[str, str] = {
    "goalkeeper": "GK",
    "defender":   "DEF",
    "midfielder": "MID",
    "forward":    "FWD",
}

# Stub expected-points by position until API-Football data layer is wired.
# Reflects typical fantasy-points ceiling: FWD score most, GK least.
_POSITION_XP: dict[str, float] = {
    "FWD": 10.0,
    "MID":  8.0,
    "DEF":  6.0,
    "GK":   5.0,
}

# High-floor positions: starters most likely to contribute (FWD + MID by default).
_HIGH_FLOOR_POSITIONS = {"FWD", "MID"}


def _role_to_position(role: str) -> str:
    return _ROLE_TO_POSITION.get(role.lower(), "MID")


# ── Scoreline distribution (Poisson) ─────────────────────────────────────────


def _poisson_prob(lam: float, k: int) -> float:
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _poisson_scorelines(
    home_lambda: float = 1.4,
    away_lambda: float = 1.1,
    max_goals: int = 4,
) -> tuple[ScorelineProb, ...]:
    """Generate a correct-score distribution from independent Poisson models."""
    lines = []
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = _poisson_prob(home_lambda, h) * _poisson_prob(away_lambda, a)
            lines.append(ScorelineProb(home=h, away=a, p=round(p, 6)))
    # Normalise so sum == 1.0 (truncating at max_goals loses ~2% mass)
    total = sum(s.p for s in lines)
    return tuple(ScorelineProb(s.home, s.away, round(s.p / total, 6)) for s in lines)


# ── PredictionInputs builder ──────────────────────────────────────────────────


def build_prediction_inputs_from_db(db: Session, match: Match) -> PredictionInputs:
    """
    Build PredictionInputs for a match using only data already in the DB.

    Uses stub expected_points based on position and sets all players to
    floor='mid' (or 'high' for FWD/MID) and availability='starter' until the
    API-Football data layer provides real per-player estimates.
    """
    players = (
        db.query(Player)
        .filter(Player.team_id.in_([match.team_1_id, match.team_2_id]))
        .all()
    )

    scored = tuple(
        ScoredPlayer(
            player_id=str(p.id),
            team_id=str(p.team_id),
            position=_role_to_position(p.role),  # type: ignore[arg-type]
            expected_points=_POSITION_XP.get(_role_to_position(p.role), 6.0),
            floor="high" if _role_to_position(p.role) in _HIGH_FLOOR_POSITIONS else "mid",  # type: ignore[arg-type]
            availability="starter",
        )
        for p in players
    )

    return PredictionInputs(
        match_id=str(match.id),
        home_team_id=str(match.team_1_id),
        away_team_id=str(match.team_2_id),
        players=scored,
        scorelines=_poisson_scorelines(),
        data_quality=DataQuality(lineups_confirmed=False, odds_source="poisson"),
    )


@dataclass
class FallbackSummary:
    match_id: int
    filled: int
    skipped: int
    user_ids_filled: list[int] = field(default_factory=list)


def run_football_fallback(
    db: Session,
    match: Match,
    inputs: PredictionInputs,
    strategy: Strategy = DEFAULT_STRATEGY,
) -> FallbackSummary:
    """
    Fill missing football predictions for all football-league members.

    - Only targets users who are members of at least one league with sport='football'.
    - Skips users who already have a Prediction row for this match.
    - Idempotent: safe to call multiple times; second call fills 0.
    """
    # All users in any football league (distinct)
    football_member_ids: list[int] = (
        db.query(LeagueMember.user_id)
        .join(League, LeagueMember.league_id == League.id)
        .filter(League.sport == "football")
        .distinct()
        .all()
    )
    football_member_ids = [row[0] for row in football_member_ids]

    if not football_member_ids:
        return FallbackSummary(match_id=match.id, filled=0, skipped=0)

    # Users who already have a prediction for this match
    already_predicted: set[int] = {
        row[0]
        for row in db.query(Prediction.user_id)
        .filter(
            Prediction.match_id == match.id,
            Prediction.user_id.in_(football_member_ids),
        )
        .all()
    }

    to_fill = [uid for uid in football_member_ids if uid not in already_predicted]
    skipped = len(football_member_ids) - len(to_fill)

    filled_ids: list[int] = []
    for user_id in to_fill:
        result = auto_pick(
            inputs,
            strategy,
            Identity(user_id=str(user_id), match_id=str(match.id)),
        )
        player_ids = tuple(int(pid) for pid in result.player_ids)
        create_football_prediction(
            db=db,
            user_id=user_id,
            match_id=match.id,
            team1_goals=result.scoreline_home,
            team2_goals=result.scoreline_away,
            advance_winner_id=None,
            player_pick_ids=player_ids,  # type: ignore[arg-type]
            source="autopick",
        )
        filled_ids.append(user_id)

    return FallbackSummary(
        match_id=match.id,
        filled=len(filled_ids),
        skipped=skipped,
        user_ids_filled=filled_ids,
    )
