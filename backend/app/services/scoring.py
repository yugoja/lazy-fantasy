"""Sport-agnostic scoring dispatcher.

Public entry point ``calculate_scores(db, match_id)`` is unchanged so routers,
admin, sync, and seed code don't move. It reads ``match.tournament.sport`` and
delegates to the per-sport scorer:

- cricket → :mod:`app.services.scoring_cricket` (reads inline ``predicted_*`` /
  ``result_*`` columns).
- football → :mod:`app.services.scoring_football` (pure functions), with the
  ORM→dataclass bridging done here so the football module stays DB-free.
"""

from sqlalchemy.orm import Session

from app.models import (
    FootballMatchResult,
    FootballPlayerMatchEvent,
    Match,
    MatchStatus,
    Prediction,
)
from app.services import scoring_cricket, scoring_football
from app.services.scoring_football import (
    DRAW,
    TEAM1,
    TEAM2,
    MatchResult,
    PlayerMatchEvents,
    Position,
    ScorelinePrediction,
)


# --- Football ORM → pure-dataclass bridge -----------------------------------
def _side(team_id: int | None, match: Match) -> int | None:
    """Map a DB team id to a relative side (TEAM1/TEAM2) for the scorer."""
    if team_id is None:
        return None
    if team_id == match.team_1_id:
        return TEAM1
    if team_id == match.team_2_id:
        return TEAM2
    return None


def _player_events(player_id: int, position: Position, by_player: dict) -> PlayerMatchEvents:
    """Build a PlayerMatchEvents for a picked player; zeros if they have no
    recorded event row (e.g. didn't play)."""
    ev: FootballPlayerMatchEvent | None = by_player.get(player_id)
    if ev is None:
        return PlayerMatchEvents(position=position, minutes_played=0)
    return PlayerMatchEvents(
        position=position,
        minutes_played=ev.minutes_played,
        goals=ev.goals,
        assists=ev.assists,
        team_goals_conceded=ev.team_goals_conceded,
        ingame_pen_saves=ev.ingame_pen_saves,
        shootout_pen_saves=ev.shootout_pen_saves,
        red_card=ev.red_card,
        own_goals=ev.own_goals,
        ingame_pen_misses=ev.ingame_pen_misses,
    )


def _build_football_inputs(
    prediction: Prediction, match: Match, result: FootballMatchResult
) -> tuple[ScorelinePrediction, list[PlayerMatchEvents], MatchResult]:
    """Translate the football ORM rows into the scorer's pure dataclasses."""
    fp = prediction.football
    scoreline = ScorelinePrediction(
        team1_goals=fp.team1_goals,
        team2_goals=fp.team2_goals,
        advance_winner=_side(fp.advance_winner_id, match),
    )
    match_result = MatchResult(
        stage=match.stage or scoring_football.GROUP,
        team1_goals_reg=result.team1_goals_reg,
        team2_goals_reg=result.team2_goals_reg,
        team1_goals_et=result.team1_goals_et,
        team2_goals_et=result.team2_goals_et,
        shootout_winner=_side(result.shootout_winner_id, match),
    )
    by_player = {ev.player_id: ev for ev in result.player_events}
    picks = [fp.player_pick_1, fp.player_pick_2, fp.player_pick_3]
    player_events = [_player_events(p.id, Position(p.role), by_player) for p in picks]
    return scoreline, player_events, match_result


def _score_football_prediction(
    prediction: Prediction, match: Match, result: FootballMatchResult
) -> int:
    if prediction.football is None:
        return 0
    scoreline, player_events, match_result = _build_football_inputs(
        prediction, match, result
    )
    return scoring_football.compute_match_score(scoreline, player_events, match_result)


def football_score_breakdown(
    prediction: Prediction, match: Match, result: FootballMatchResult
) -> dict:
    """Per-component football score for display (Done tab).

    Returns ``result_score`` (result+scoreline, pre-multiplier), per-pick
    ``player_scores`` (pre-multiplier), ``is_knockout``, and the final ``total``.
    """
    scoreline, player_events, match_result = _build_football_inputs(
        prediction, match, result
    )
    result_score = scoring_football.compute_result_score(scoreline, match_result)
    player_scores = [scoring_football.compute_player_score(ev) for ev in player_events]
    return {
        "result_score": result_score,
        "player_scores": player_scores,
        "is_knockout": match_result.is_knockout,
        "total": scoring_football.compute_match_score(
            scoreline, player_events, match_result
        ),
    }


# --- Public API -------------------------------------------------------------
def calculate_scores(db: Session, match_id: int) -> int:
    """Calculate and persist scores for all unprocessed predictions for a match.

    Returns the number of predictions processed.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or match.status != MatchStatus.COMPLETED:
        return 0

    sport = match.tournament.sport if match.tournament else "cricket"

    predictions = (
        db.query(Prediction)
        .filter(
            Prediction.match_id == match_id,
            Prediction.is_processed == False,  # noqa: E712
        )
        .all()
    )

    football_result = match.football_result if sport == "football" else None

    for prediction in predictions:
        if sport == "football":
            if football_result is None:
                continue  # no result recorded yet; leave unprocessed
            prediction.points_earned = _score_football_prediction(
                prediction, match, football_result
            )
        else:
            prediction.points_earned = scoring_cricket.score_prediction(prediction, match)
        prediction.is_processed = True

    db.commit()
    return len(predictions)
