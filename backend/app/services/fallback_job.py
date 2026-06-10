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
from app.models.player_form import PlayerForm
from app.models.prediction import Prediction
from app.models.team import Team
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


_RANK_ADVANTAGE_THRESHOLD = 8   # rank difference for a clear favourite
_RANK_LAMBDA_SCALE = 0.03       # each rank step shifts lambda by this much

# WC is at neutral venues: equal baseline for both sides.
# Tier 3 note: ordinal FIFA rank is the only strength data available; cardinal
# (ranking points / Elo / odds) would improve the strength_adjustment but is
# not in the current schema — flagged as data-blocked.
BASE_LAMBDA: float = 1.3        # tune if data supports it

# Optional host-venue bump: not implemented — venue/host field absent from Match model.


def _poisson_prob(lam: float, k: int) -> float:
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _rank_adjusted_lambdas(
    home_rank: int | None,
    away_rank: int | None,
    base: float = BASE_LAMBDA,
) -> tuple[float, float]:
    """Shift Poisson lambdas based on relative FIFA ranking.

    Both sides start from the same BASE_LAMBDA (neutral venue — no home edge).
    A rank difference of 1 shifts each lambda by _RANK_LAMBDA_SCALE (0.03).
    France (#1) vs Senegal (#16): diff=15 → +0.45 / −0.45 → ~1.75 vs 0.85.
    Lambdas are clamped to [0.4, 2.8] to stay within sensible football ranges.
    """
    hr = home_rank or 24
    ar = away_rank or 24
    adjustment = (ar - hr) * _RANK_LAMBDA_SCALE  # positive when home is better ranked
    return (
        max(0.4, min(2.8, base + adjustment)),
        max(0.4, min(2.8, base - adjustment)),
    )


def _poisson_scorelines(
    home_lambda: float = BASE_LAMBDA,
    away_lambda: float = BASE_LAMBDA,
    max_goals: int = 4,
) -> tuple[ScorelineProb, ...]:
    """Generate a correct-score distribution from independent Poisson models."""
    lines = []
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = _poisson_prob(home_lambda, h) * _poisson_prob(away_lambda, a)
            lines.append(ScorelineProb(home=h, away=a, p=round(p, 6)))
    total = sum(s.p for s in lines)
    return tuple(ScorelineProb(s.home, s.away, round(s.p / total, 6)) for s in lines)


def _team_floor(team_rank: int | None, opponent_rank: int | None) -> str:
    """Return floor tier for a team's players based on relative FIFA ranking.

    If the team is clearly stronger (rank difference ≥ threshold), their players
    get 'high' so the safe strategy naturally picks from the dominant side.
    """
    tr = team_rank or 24
    opr = opponent_rank or 24
    return "high" if (opr - tr) >= _RANK_ADVANTAGE_THRESHOLD else "mid"


# ── PredictionInputs builder ──────────────────────────────────────────────────


def build_prediction_inputs_from_db(db: Session, match: Match) -> PredictionInputs:
    """Build PredictionInputs for a match using DB data.

    Scoreline lambdas are adjusted by relative FIFA ranking so stronger teams
    are expected to score more. Player floors reflect team-level advantage:
    the clearly stronger team's players are marked 'high', enabling the safe
    strategy to favour them over the underdog.
    """
    teams = {
        t.id: t
        for t in db.query(Team).filter(Team.id.in_([match.team_1_id, match.team_2_id])).all()
    }
    home_team = teams.get(match.team_1_id)
    away_team = teams.get(match.team_2_id)
    home_rank = home_team.fifa_ranking if home_team else None
    away_rank = away_team.fifa_ranking if away_team else None

    home_floor = _team_floor(home_rank, away_rank)
    away_floor = _team_floor(away_rank, home_rank)

    players = (
        db.query(Player)
        .filter(Player.team_id.in_([match.team_1_id, match.team_2_id]))
        .all()
    )

    forms = {
        pf.player_id: pf
        for pf in db.query(PlayerForm)
        .filter(PlayerForm.player_id.in_([p.id for p in players]))
        .all()
    }

    def _floor_for(p: Player) -> str:
        team_floor = home_floor if p.team_id == match.team_1_id else away_floor
        if p.id in forms:
            db_floor = forms[p.id].floor
            # Promote to team_floor if it's better; never demote below db_floor
            tier_order = {"high": 0, "mid": 1, "low": 2}
            return db_floor if tier_order[db_floor] <= tier_order[team_floor] else team_floor
        return team_floor

    scored = tuple(
        ScoredPlayer(
            player_id=str(p.id),
            team_id=str(p.team_id),
            position=_role_to_position(p.role),  # type: ignore[arg-type]
            expected_points=(
                forms[p.id].expected_points or _POSITION_XP.get(_role_to_position(p.role), 6.0)
                if p.id in forms
                else _POSITION_XP.get(_role_to_position(p.role), 6.0)
            ),
            floor=_floor_for(p),  # type: ignore[arg-type]
            availability=(
                forms[p.id].availability if p.id in forms  # type: ignore[arg-type]
                else "starter"
            ),
        )
        for p in players
    )

    home_lambda, away_lambda = _rank_adjusted_lambdas(home_rank, away_rank)

    return PredictionInputs(
        match_id=str(match.id),
        home_team_id=str(match.team_1_id),
        away_team_id=str(match.team_2_id),
        players=scored,
        scorelines=_poisson_scorelines(home_lambda, away_lambda),
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
