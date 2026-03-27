"""Cricket data sync service — auto lineup and result population via CricAPI."""
import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta
from difflib import get_close_matches

from sqlalchemy.orm import Session

from app.models.match import Match, MatchStatus
from app.models.match_lineup import MatchLineup
from app.models.player import Player
from app.services.cricket_provider import CricketProvider, ProviderMatchInfo, ProviderPlayer
from app.services.league import snapshot_league_ranks
from app.services.scoring import calculate_scores

logger = logging.getLogger(__name__)

_provider: CricketProvider | None = None


def set_provider(p: CricketProvider) -> None:
    global _provider
    _provider = p


def get_provider() -> CricketProvider | None:
    return _provider


# ---------------------------------------------------------------------------
# Public sync functions (called by scheduler)
# ---------------------------------------------------------------------------

def sync_lineups(db: Session) -> None:
    """For matches linked to CricAPI with start_time within 4h, auto-populate lineup."""
    if not _provider:
        return
    now = datetime.utcnow()
    window = now + timedelta(hours=4)
    matches = (
        db.query(Match)
        .filter(
            Match.status == MatchStatus.SCHEDULED,
            Match.external_match_id.isnot(None),
            Match.sync_state == "linked",
            Match.start_time <= window,
        )
        .all()
    )
    for match in matches:
        _sync_lineup_for_match(db, match)


def sync_results(db: Session) -> None:
    """For matches that should be over, fetch results and trigger scoring."""
    if not _provider:
        return
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=3, minutes=30)

    candidates = (
        db.query(Match)
        .filter(
            Match.external_match_id.isnot(None),
            Match.status == MatchStatus.SCHEDULED,
            Match.start_time <= cutoff,
            Match.sync_state != "result_synced",
        )
        .all()
    )
    for match in candidates:
        _sync_result_for_match(db, match)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sync_lineup_for_match(db: Session, match: Match) -> None:
    info = _provider.get_match_info(match.external_match_id)
    if not info:
        _set_sync_error(db, match, "CricAPI returned no data")
        return

    if not info.lineup_announced:
        return  # Not announced yet; try again next cycle

    all_players_in_match = (
        db.query(Player)
        .filter(Player.team_id.in_([match.team_1_id, match.team_2_id]))
        .all()
    )
    team1_db = [p for p in all_players_in_match if p.team_id == match.team_1_id]
    team2_db = [p for p in all_players_in_match if p.team_id == match.team_2_id]

    resolved: list[int] = []
    errors: list[str] = []

    for pp in info.team1_players:
        player = _resolve_player(pp, team1_db, db)
        if player:
            resolved.append(player.id)
        else:
            errors.append(f"Unmatched (team1): {pp.name!r}")

    for pp in info.team2_players:
        player = _resolve_player(pp, team2_db, db)
        if player:
            resolved.append(player.id)
        else:
            errors.append(f"Unmatched (team2): {pp.name!r}")

    team1_count = sum(1 for pid in resolved if any(p.id == pid and p.team_id == match.team_1_id for p in all_players_in_match))
    team2_count = len(resolved) - team1_count

    # Require at least 10 per team (allow 1 unmatched for tolerance)
    if team1_count < 10 or team2_count < 10:
        _set_sync_error(db, match, f"Too many unmatched players: {'; '.join(errors)}")
        return

    # Upsert lineup
    db.query(MatchLineup).filter(MatchLineup.match_id == match.id).delete()
    for pid in resolved:
        db.add(MatchLineup(match_id=match.id, player_id=pid))

    match.sync_state = "lineup_synced"
    match.sync_error = "; ".join(errors) if errors else None
    match.last_synced_at = datetime.utcnow()
    db.commit()
    logger.info(f"Lineup synced for match {match.id}: {len(resolved)} players ({len(errors)} unmatched)")


def _sync_result_for_match(db: Session, match: Match) -> None:
    info = _provider.get_match_info(match.external_match_id)
    if not info:
        _set_sync_error(db, match, "CricAPI returned no data for result")
        return

    # Only proceed if the API reports the match is finished
    status_lower = info.status.lower()
    if "result" not in status_lower and "won" not in status_lower and "tied" not in status_lower:
        return

    all_players = (
        db.query(Player)
        .filter(Player.team_id.in_([match.team_1_id, match.team_2_id]))
        .all()
    )
    team1_db = [p for p in all_players if p.team_id == match.team_1_id]
    team2_db = [p for p in all_players if p.team_id == match.team_2_id]

    errors: list[str] = []

    # Resolve winner
    winner_id: int | None = None
    if info.winner_name:
        winner_id = _resolve_team(info.winner_name, match)
    if not winner_id:
        errors.append(f"Cannot resolve winner: {info.winner_name!r}")

    # Resolve POM
    pom_player_id: int | None = None
    if info.pom_name:
        pom_pp = ProviderPlayer(provider_id="", name=info.pom_name, team_name="")
        pom_player = _resolve_player(pom_pp, team1_db + team2_db, db)
        if pom_player:
            pom_player_id = pom_player.id
        else:
            errors.append(f"Cannot resolve POM: {info.pom_name!r}")

    if errors:
        _set_sync_error(db, match, "; ".join(errors))
        return

    # Find top scorer and wicket-taker per team from provider data
    t1_top_runs = _top_by(info.team1_players, "batting_runs")
    t2_top_runs = _top_by(info.team2_players, "batting_runs")
    t1_top_wkts = _top_by(info.team1_players, "bowling_wickets")
    t2_top_wkts = _top_by(info.team2_players, "bowling_wickets")

    mr_t1 = _resolve_player(t1_top_runs, team1_db, db) if t1_top_runs else None
    mr_t2 = _resolve_player(t2_top_runs, team2_db, db) if t2_top_runs else None
    mw_t1 = _resolve_player(t1_top_wkts, team1_db, db) if t1_top_wkts else None
    mw_t2 = _resolve_player(t2_top_wkts, team2_db, db) if t2_top_wkts else None

    stat_errors = []
    if not mr_t1:
        stat_errors.append(f"top runs team1: {t1_top_runs.name if t1_top_runs else 'none'}")
    if not mr_t2:
        stat_errors.append(f"top runs team2: {t2_top_runs.name if t2_top_runs else 'none'}")
    if not mw_t1:
        stat_errors.append(f"top wkts team1: {t1_top_wkts.name if t1_top_wkts else 'none'}")
    if not mw_t2:
        stat_errors.append(f"top wkts team2: {t2_top_wkts.name if t2_top_wkts else 'none'}")

    if stat_errors:
        # Non-fatal: set sync_error but still set result if we have winner + pom
        logger.warning(f"Match {match.id} stat resolution issues: {stat_errors}")
        match.sync_error = f"Partial stat resolution: {'; '.join(stat_errors)}"

    # Apply result
    match.result_winner_id = winner_id
    match.result_most_runs_team1_player_id = mr_t1.id if mr_t1 else None
    match.result_most_runs_team2_player_id = mr_t2.id if mr_t2 else None
    match.result_most_wickets_team1_player_id = mw_t1.id if mw_t1 else None
    match.result_most_wickets_team2_player_id = mw_t2.id if mw_t2 else None
    match.result_pom_player_id = pom_player_id
    match.status = MatchStatus.COMPLETED
    match.sync_state = "result_synced"
    match.last_synced_at = datetime.utcnow()
    db.commit()

    snapshot_league_ranks(db, match.id)
    predictions_processed = calculate_scores(db, match.id)
    logger.info(f"Auto-result synced for match {match.id}: {predictions_processed} predictions scored")



# ---------------------------------------------------------------------------
# Player resolution (3-tier fallback)
# ---------------------------------------------------------------------------

def _resolve_player(pp: ProviderPlayer, candidates: list[Player], db: Session) -> Player | None:
    """Map a ProviderPlayer to an internal Player via exact ID → name → fuzzy."""
    # Tier 1: exact cricapi_player_id match
    if pp.provider_id:
        player = db.query(Player).filter(Player.cricapi_player_id == pp.provider_id).first()
        if player:
            return player

    # Tier 2: normalized name match
    matches = [p for p in candidates if _name_matches(pp.name, p.name)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        logger.debug(f"Ambiguous name match for {pp.name!r}: {[p.name for p in matches]}")
        # Fall through to fuzzy

    # Tier 3: difflib fuzzy
    name_map = {p.name: p for p in candidates}
    close = get_close_matches(_normalize(pp.name), [_normalize(n) for n in name_map], n=1, cutoff=0.82)
    if close:
        # Map normalized name back to original
        for original_name, player in name_map.items():
            if _normalize(original_name) == close[0]:
                logger.debug(f"Fuzzy matched {pp.name!r} → {original_name!r}")
                return player

    return None


def _normalize(name: str) -> str:
    """Lowercase, strip diacritics, remove punctuation."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z ]", "", ascii_str.lower()).strip()


def _name_matches(provider_name: str, db_name: str) -> bool:
    """Match abbreviated names like 'V Kohli' to 'Virat Kohli'."""
    p_tokens = _normalize(provider_name).split()
    d_tokens = _normalize(db_name).split()
    if not p_tokens or not d_tokens:
        return False
    # Last name must match
    if p_tokens[-1] != d_tokens[-1]:
        return False
    # If only one token in provider name, last name match is sufficient
    if len(p_tokens) == 1:
        return True
    # First token: check if it's an initial or full name
    if len(p_tokens[0]) == 1:
        # Initial match: "V" matches "Virat"
        return d_tokens[0].startswith(p_tokens[0])
    return p_tokens[0] == d_tokens[0]


def _top_by(players: list[ProviderPlayer], attr: str) -> ProviderPlayer | None:
    """Return the player with the highest value of attr, or None if list is empty."""
    if not players:
        return None
    best = max(players, key=lambda p: getattr(p, attr, 0))
    return best if getattr(best, attr, 0) > 0 else None


def _resolve_team(winner_name: str, match: Match) -> int | None:
    """Match a winner team name string to match.team_1_id or match.team_2_id."""
    wn = winner_name.lower()
    t1 = match.team_1
    t2 = match.team_2
    if t1 and (t1.name.lower() in wn or t1.short_name.lower() in wn):
        return t1.id
    if t2 and (t2.name.lower() in wn or t2.short_name.lower() in wn):
        return t2.id
    return None


def _set_sync_error(db: Session, match: Match, error: str) -> None:
    match.sync_error = error[:500]
    db.commit()
    logger.warning(f"Sync error for match {match.id}: {error}")
