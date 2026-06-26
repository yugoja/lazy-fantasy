"""Football result sync service — auto-populates results via api-football.com."""
import logging
import re
import unicodedata
from datetime import datetime
from difflib import get_close_matches

from sqlalchemy.orm import Session

from app.models.football_match_result import FootballMatchResult, FootballPlayerMatchEvent
from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.prediction import Prediction
from app.services.football_provider import ApiFootballProvider, FootballPlayerStat
from app.services.league import snapshot_league_ranks
from app.services.scoring import calculate_scores

logger = logging.getLogger(__name__)

_provider: ApiFootballProvider | None = None


def set_provider(p: ApiFootballProvider) -> None:
    global _provider
    _provider = p


def get_provider() -> ApiFootballProvider | None:
    return _provider


# ---------------------------------------------------------------------------
# Public entry point (called by scheduler + admin endpoint)
# ---------------------------------------------------------------------------

def sync_match_result(db: Session, match_id: int) -> dict:
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        return {"status": "error", "detail": "match not found"}
    if not match.external_match_id:
        return {"status": "error", "detail": "match has no external_match_id — link it first"}

    if not _provider:
        return {"status": "error", "detail": "football provider not configured"}

    if not match.external_match_id.lstrip("-").isdigit():
        return {"status": "error", "detail": f"external_match_id '{match.external_match_id}' is not a valid fixture ID"}
    fixture_id = int(match.external_match_id)

    result = _provider.get_fixture_result(fixture_id)
    if result is None:
        return {"status": "not_finished", "predictions_processed": 0, "unresolved_players": [], "sync_error": None}

    player_stats = _provider.get_player_stats(fixture_id)

    all_players = (
        db.query(Player)
        .filter(Player.team_id.in_([match.team_1_id, match.team_2_id]))
        .all()
    )
    team1_db = [p for p in all_players if p.team_id == match.team_1_id]
    team2_db = [p for p in all_players if p.team_id == match.team_2_id]

    # Partition stats by team — home maps to team_1
    home_api_id = result.home_team_api_id
    team1_stats = [s for s in player_stats if s.team_api_id == home_api_id]
    team2_stats = [s for s in player_stats if s.team_api_id != home_api_id]

    resolved_events: list[tuple[Player, FootballPlayerStat]] = []
    unresolved: list[str] = []
    unresolved_stats: list[FootballPlayerStat] = []

    for stat in team1_stats:
        player = _resolve_football_player(stat, team1_db, db)
        if player:
            resolved_events.append((player, stat))
        else:
            unresolved.append(f"{stat.name} (team1)")
            unresolved_stats.append(stat)

    for stat in team2_stats:
        player = _resolve_football_player(stat, team2_db, db)
        if player:
            resolved_events.append((player, stat))
        else:
            unresolved.append(f"{stat.name} (team2)")
            unresolved_stats.append(stat)

    # Two distinct API players can resolve to the same DB player (e.g. Brazil's
    # GK "Ederson" and midfielder "Éderson" both map to one DB "EDERSON"). Keep a
    # single event per DB player — the one who actually played most — so the
    # unique (match, player) constraint can't crash the whole sync.
    deduped: dict[int, tuple[Player, FootballPlayerStat]] = {}
    for player, stat in resolved_events:
        current = deduped.get(player.id)
        if current is None or stat.minutes_played > current[1].minutes_played:
            deduped[player.id] = (player, stat)
    resolved_events = list(deduped.values())

    # Own goals aren't in fixtures/players — pull them from fixtures/events and
    # attach to the matching player's stat (shootout events excluded; an own goal
    # is always in regulation/ET).
    og_by_api: dict[int, int] = {}
    for ge in _provider.get_fixture_events(fixture_id):
        if ge.detail == "Own Goal" and not ge.is_shootout and ge.api_player_id:
            og_by_api[ge.api_player_id] = og_by_api.get(ge.api_player_id, 0) + 1
    if og_by_api:
        for _player, stat in resolved_events:
            stat.own_goals = og_by_api.get(stat.api_player_id, 0)

    # Derive shootout winner
    shootout_winner_id: int | None = None
    if result.status_short == "PEN" and result.penalty_team1 is not None and result.penalty_team2 is not None:
        if result.penalty_team1 > result.penalty_team2:
            shootout_winner_id = match.team_1_id
        else:
            shootout_winner_id = match.team_2_id

    # Final scoreline for goals-conceded calculation
    if result.team1_goals_et is not None:
        t1_total, t2_total = result.team1_goals_et, result.team2_goals_et
    else:
        t1_total, t2_total = result.team1_goals_reg, result.team2_goals_reg

    predictions_processed = _apply_football_result(
        db=db,
        match=match,
        team1_goals_reg=result.team1_goals_reg,
        team2_goals_reg=result.team2_goals_reg,
        team1_goals_et=result.team1_goals_et,
        team2_goals_et=result.team2_goals_et,
        shootout_winner_id=shootout_winner_id,
        resolved_events=resolved_events,
        t1_total=t1_total,
        t2_total=t2_total,
    )

    sync_error = ("; ".join(unresolved) if unresolved else None)
    match.sync_state = "result_synced"
    match.last_synced_at = datetime.utcnow()
    match.sync_error = sync_error[:500] if sync_error else None
    db.commit()

    # Loud alert when an unresolved API player was actually *picked* by someone:
    # they silently score 0 (the Isak/GK class of bug). Surface it so we reconcile.
    unresolved_picks = _flag_unresolved_picks(db, match, unresolved_stats)

    try:
        from app.services.player_form_service import update_player_form_after_match
        update_player_form_after_match(db, match, player_stats, result)
    except Exception as e:
        logger.warning(f"player_form update failed for match {match.id}: {e}")

    return {
        "status": "synced",
        "predictions_processed": predictions_processed,
        "unresolved_players": unresolved,
        "unresolved_picks": unresolved_picks,
        "sync_error": sync_error,
    }


# ---------------------------------------------------------------------------
# Shared result-apply helper (used by sync + admin manual form)
# ---------------------------------------------------------------------------

def _apply_football_result(
    db: Session,
    match: Match,
    team1_goals_reg: int,
    team2_goals_reg: int,
    team1_goals_et: int | None,
    team2_goals_et: int | None,
    shootout_winner_id: int | None,
    resolved_events: list[tuple[Player, FootballPlayerStat]],
    t1_total: int,
    t2_total: int,
) -> int:
    existing = db.query(FootballMatchResult).filter_by(match_id=match.id).first()
    # Shootout pen saves can't be derived from the API (a saved and an off-target
    # shootout penalty both read as "Missed Penalty"), so they're entered by hand.
    # Preserve any non-zero value across this delete-and-recreate so a re-sync
    # doesn't wipe the manual correction.
    manual_shootout_saves: dict[int, int] = {}
    if existing:
        for ev in existing.player_events:
            if ev.shootout_pen_saves:
                manual_shootout_saves[ev.player_id] = ev.shootout_pen_saves
        db.delete(existing)
        db.flush()

    fr = FootballMatchResult(
        match_id=match.id,
        team1_goals_reg=team1_goals_reg,
        team2_goals_reg=team2_goals_reg,
        team1_goals_et=team1_goals_et,
        team2_goals_et=team2_goals_et,
        shootout_winner_id=shootout_winner_id,
    )
    for player, stat in resolved_events:
        conceded = t2_total if player.team_id == match.team_1_id else t1_total
        fr.player_events.append(FootballPlayerMatchEvent(
            player_id=player.id,
            minutes_played=stat.minutes_played,
            goals=stat.goals,
            assists=stat.assists,
            team_goals_conceded=conceded,
            ingame_pen_saves=stat.ingame_pen_saves,
            shootout_pen_saves=manual_shootout_saves.get(player.id, stat.shootout_pen_saves),
            red_card=stat.red_card,
            own_goals=stat.own_goals,
            ingame_pen_misses=stat.ingame_pen_misses,
        ))
    db.add(fr)
    match.status = MatchStatus.COMPLETED
    # Record the match winner on the shared column so cross-sport surfaces
    # (dugout Match Verdict, etc.) can key off it. None for a genuine draw.
    if shootout_winner_id is not None:
        match.result_winner_id = shootout_winner_id
    elif t1_total > t2_total:
        match.result_winner_id = match.team_1_id
    elif t2_total > t1_total:
        match.result_winner_id = match.team_2_id
    else:
        match.result_winner_id = None
    db.commit()

    db.query(Prediction).filter(Prediction.match_id == match.id).update(
        {"is_processed": False, "points_earned": 0}
    )
    db.commit()

    snapshot_league_ranks(db, match.id)
    return calculate_scores(db, match.id)


# ---------------------------------------------------------------------------
# Unresolved-pick alerting
# ---------------------------------------------------------------------------

def _flag_unresolved_picks(
    db: Session, match: Match, unresolved_stats: list[FootballPlayerStat]
) -> list[str]:
    """Detect unresolved API players who were *picked* for this match — they
    silently score 0. Returns human-readable warnings and logs each loudly.

    Matches an unresolved API stat to a picked player by surname-token overlap
    (looser than the sync's own matcher, which already failed on these by
    definition) so a near-miss like "Husam Ali Mohammad Abudahab" vs
    "HUSAM ABUDAHAB" still gets surfaced for reconciliation."""
    from app.models.football_prediction import FootballPrediction

    if not unresolved_stats:
        return []

    rows = (
        db.query(
            FootballPrediction.player_pick_1_id,
            FootballPrediction.player_pick_2_id,
            FootballPrediction.player_pick_3_id,
        )
        .join(Prediction, Prediction.id == FootballPrediction.prediction_id)
        .filter(Prediction.match_id == match.id)
        .all()
    )
    pick_counts: dict[int, int] = {}
    for r in rows:
        for pid in r:
            if pid:
                pick_counts[pid] = pick_counts.get(pid, 0) + 1
    if not pick_counts:
        return []

    picked_players = db.query(Player).filter(Player.id.in_(list(pick_counts))).all()
    # surname token = last token of the normalized name
    by_surname: dict[str, list[Player]] = {}
    for p in picked_players:
        toks = _normalize(p.name).split()
        if toks:
            by_surname.setdefault(toks[-1], []).append(p)

    warnings: list[str] = []
    for stat in unresolved_stats:
        stat_tokens = set(_normalize(stat.name).split())
        for surname, players in by_surname.items():
            # unambiguous: exactly one picked player shares this surname token
            if surname in stat_tokens and len(players) == 1:
                p = players[0]
                n = pick_counts[p.id]
                msg = (
                    f"match {match.id}: picked player '{p.name}' (id {p.id}, "
                    f"{n} pick(s)) likely UNSCORED — API stat '{stat.name}' "
                    f"(api_id {stat.api_player_id}) did not resolve"
                )
                logger.warning(msg)
                warnings.append(msg)
    return warnings


# ---------------------------------------------------------------------------
# Player resolution (3-tier: exact api_id → token-set name → fuzzy)
# ---------------------------------------------------------------------------

def _resolve_football_player(stat: FootballPlayerStat, candidates: list[Player], db: Session) -> Player | None:
    # Tier 1: exact api_football_player_id
    if stat.api_player_id:
        player = db.query(Player).filter(
            Player.api_football_player_id == str(stat.api_player_id)
        ).first()
        if player:
            return player

    # Tier 2: token-set equality (handles "Bukayo Saka" ↔ "SAKA Bukayo")
    api_tokens = frozenset(_normalize(stat.name).split())
    for p in candidates:
        if frozenset(_normalize(p.name).split()) == api_tokens:
            _cache_api_id(db, p, stat.api_player_id)
            return p

    # Tier 3: difflib fuzzy
    name_map = {p.name: p for p in candidates}
    close = get_close_matches(
        _normalize(stat.name),
        [_normalize(n) for n in name_map],
        n=1,
        cutoff=0.82,
    )
    if close:
        for original_name, player in name_map.items():
            if _normalize(original_name) == close[0]:
                logger.debug(f"Fuzzy matched {stat.name!r} → {original_name!r}")
                _cache_api_id(db, player, stat.api_player_id)
                return player

    return None


def _cache_api_id(db: Session, player: Player, api_player_id: int) -> None:
    if api_player_id and not player.api_football_player_id:
        player.api_football_player_id = str(api_player_id)
        # no commit here — caller commits after the full batch


def _normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z ]", "", ascii_str.lower()).strip()
