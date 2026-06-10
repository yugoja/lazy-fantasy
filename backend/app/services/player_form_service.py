"""M2.5 — Real player form data layer.

Replaces position-based stubs with API-Football-derived expected_points.
Blends pre-tournament season stats with WC accumulator data as the
tournament progresses.
"""

from __future__ import annotations

import logging
import math
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import get_close_matches
from typing import Optional

from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.player_form import PlayerForm
from app.models.team import Team
from app.services.football_provider import (
    ApiFootballProvider,
    FixtureLineup,
    FootballFixtureResult,
    FootballPlayerStat,
    WCSquadPlayer,
)
from app.services.scoring_football import (
    ASSIST_POINTS,
    CLEAN_SHEET_POINTS,
    FLOOR_POINTS,
    GOAL_POINTS,
    MIN_CLEAN_SHEET_MINUTES,
    MIN_FLOOR_MINUTES,
    PEN_SAVE_POINTS,
    Position,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

# Position stubs (fallback when no API data at all)
_POSITION_XP: dict[str, float] = {
    "Attacker": 10.0,
    "Midfielder": 8.0,
    "Defender": 6.0,
    "Goalkeeper": 5.0,
}

# Neutral-venue expected-goals baseline (equal for both sides; Tier 1B complement)
BASE_LAMBDA: float = 1.3

# Maximum weight for WC tournament data so a tiny sample can't erase a full season
WC_WEIGHT_CAP: float = 0.7

# Rough average: ~1 penalty per 20 matches for a GK
EXPECTED_PEN_SAVES_PER_MATCH: float = 0.05

# ── Regularisation: shrink low-sample per-90 rates toward position mean ───────
_REGULARIZATION_90S: float = 5.0   # prior weight in 90-minute units

# Rough per-90 population means (season data across top leagues)
_POSITION_MEAN_G90: dict[str, float] = {
    "Goalkeeper": 0.0,
    "Defender":   0.02,
    "Midfielder": 0.06,
    "Attacker":   0.25,
}
_POSITION_MEAN_A90: dict[str, float] = {
    "Goalkeeper": 0.0,
    "Defender":   0.03,
    "Midfielder": 0.08,
    "Attacker":   0.12,
}

# ── Position string → Position enum ──────────────────────────────────────────
_STR_TO_POSITION: dict[str, Position] = {
    "Goalkeeper": Position.GK,
    "Defender":   Position.DEF,
    "Midfielder": Position.MID,
    "Attacker":   Position.FWD,
}


# ── Core XP formula (pure, testable) ─────────────────────────────────────────


def _xp_formula(
    g90: float,
    a90: float,
    expected_minutes: float,
    opponent_lambda: float,
    position: str,
) -> float:
    """Compute expected fantasy points for one player in one match.

    Derives all point values from scoring_football constants so any spec change
    propagates automatically. Clean-sheet probability is poisson_pmf(0, lambda)
    so team strength enters defensive XP through the lambda, not from data.
    """
    pos = _STR_TO_POSITION.get(position, Position.FWD)

    m = expected_minutes / 90.0
    p_appear = min(expected_minutes / MIN_FLOOR_MINUTES, 1.0)
    p_cs_elig = min(expected_minutes / MIN_CLEAN_SHEET_MINUTES, 1.0)
    # P(X=0) for Poisson(lambda) = e^(-lambda)
    p_cs = math.exp(-opponent_lambda)

    xp = FLOOR_POINTS * p_appear
    xp += g90 * m * GOAL_POINTS[pos]
    xp += a90 * m * ASSIST_POINTS[pos]
    if CLEAN_SHEET_POINTS[pos] > 0:
        xp += p_cs * p_cs_elig * CLEAN_SHEET_POINTS[pos]
    if pos == Position.GK:
        xp += EXPECTED_PEN_SAVES_PER_MATCH * PEN_SAVE_POINTS

    return round(xp, 2)


def _regularised_rates(
    goals: int, assists: int, total_minutes: float, position: str
) -> tuple[float, float]:
    """Shrink per-90 rates toward the position mean to dampen noisy small samples."""
    total_90s = total_minutes / 90.0
    prior = _REGULARIZATION_90S
    mean_g = _POSITION_MEAN_G90.get(position, 0.0)
    mean_a = _POSITION_MEAN_A90.get(position, 0.0)
    g90 = (goals + mean_g * prior) / (total_90s + prior)
    a90 = (assists + mean_a * prior) / (total_90s + prior)
    return g90, a90


# ── Position-aware xp formulas ────────────────────────────────────────────────


def _pre_xp(squad_player: WCSquadPlayer, opponent_lambda: float = BASE_LAMBDA) -> float:
    """Compute pre-tournament expected points from season stats."""
    pos = squad_player.position
    if squad_player.appearances == 0:
        return _POSITION_XP.get(pos, 6.0)

    expected_minutes = squad_player.minutes / squad_player.appearances
    g90, a90 = _regularised_rates(
        squad_player.goals, squad_player.assists, float(squad_player.minutes), pos
    )
    return _xp_formula(g90=g90, a90=a90, expected_minutes=expected_minutes,
                       opponent_lambda=opponent_lambda, position=pos)


def _wc_xp(form: PlayerForm, position: str, opponent_lambda: float = BASE_LAMBDA) -> float:
    """Compute WC-derived expected points from in-tournament accumulators."""
    if form.wc_games == 0:
        return 0.0

    expected_minutes = form.wc_minutes / form.wc_games
    g90, a90 = _regularised_rates(
        form.wc_goals, form.wc_assists, float(form.wc_minutes), position
    )
    return _xp_formula(g90=g90, a90=a90, expected_minutes=expected_minutes,
                       opponent_lambda=opponent_lambda, position=position)


def _derive_floor(form: PlayerForm) -> str:
    if form.wc_games == 0:
        return "mid"
    avg_min = form.wc_minutes / form.wc_games
    if avg_min >= 60:
        return "high"
    if avg_min >= 30:
        return "mid"
    return "low"


def _blend(form: PlayerForm, position: str, opponent_lambda: float = BASE_LAMBDA) -> float:
    """Blend pre-tournament and WC-derived expected points.

    WC weight is capped at WC_WEIGHT_CAP so a small tournament sample cannot
    fully override a full season of club form.
    """
    wc_weight = min(form.wc_games / 3.0, 1.0) * WC_WEIGHT_CAP
    pre = form.pre_expected_points if form.pre_expected_points is not None else _POSITION_XP.get(position, 6.0)
    if form.wc_games == 0:
        return round(pre, 2)
    wc = _wc_xp(form, position, opponent_lambda)
    return round((1 - wc_weight) * pre + wc_weight * wc, 2)


# ── Name normalisation (mirrors football_sync._normalize) ─────────────────────

def _normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z ]", "", ascii_str.lower()).strip()


def _match_player(
    api_player_id: int,
    name: str,
    candidates: list[Player],
    db: Session,
    cutoff: float = 0.82,
) -> Optional[Player]:
    """4-tier matching: exact api_id → token-set → fuzzy difflib → token-subset.

    The token-subset tier handles FIFA-format vs API-format name differences,
    e.g. DB 'VINICIUS JR' vs API 'Vinícius Júnior': the 'vinicius' token
    appears in both normalized forms.
    """
    if api_player_id:
        p = db.query(Player).filter(
            Player.api_football_player_id == str(api_player_id)
        ).first()
        if p:
            return p

    api_tokens = frozenset(_normalize(name).split())
    for p in candidates:
        if frozenset(_normalize(p.name).split()) == api_tokens:
            if api_player_id and not p.api_football_player_id:
                p.api_football_player_id = str(api_player_id)
            return p

    name_map = {p.name: p for p in candidates}
    close = get_close_matches(
        _normalize(name),
        [_normalize(n) for n in name_map],
        n=1,
        cutoff=cutoff,
    )
    if close:
        for original_name, player in name_map.items():
            if _normalize(original_name) == close[0]:
                if api_player_id and not player.api_football_player_id:
                    player.api_football_player_id = str(api_player_id)
                return player

    # Tier 4: token-subset — any significant token (>3 chars) from API name
    # matches any token in the DB name. Handles cross-format cases like
    # 'Vinícius Júnior' ↔ 'VINICIUS JR', 'Alisson Becker' ↔ 'ALISSON'.
    significant_api_tokens = {t for t in api_tokens if len(t) > 3}
    best: Optional[tuple[int, Player]] = None  # (overlap_count, player)
    for p in candidates:
        db_tokens = frozenset(_normalize(p.name).split())
        overlap = significant_api_tokens & db_tokens
        if overlap:
            count = len(overlap)
            if best is None or count > best[0]:
                best = (count, p)

    if best:
        player = best[1]
        if api_player_id and not player.api_football_player_id:
            player.api_football_player_id = str(api_player_id)
        return player

    # Tier 5: abbreviated-name matching — handles "E. Martínez" → "MARTINEZ Emiliano".
    # Splits original API name on ". " to get (initial, lastname), then finds DB
    # players whose normalized name contains the lastname AND a token starting with
    # the initial. _normalize strips dots so we check the raw name here.
    if ". " in name:
        parts = name.split(". ", 1)
        initial = _normalize(parts[0]).strip()
        lastname = _normalize(parts[1]).strip()
        lastname_tokens = frozenset(lastname.split())
        initial_matches: list[Player] = []
        for p in candidates:
            db_tokens = list(_normalize(p.name).split())
            if lastname_tokens & frozenset(db_tokens):
                if any(t.startswith(initial) for t in db_tokens):
                    initial_matches.append(p)
        if len(initial_matches) == 1:
            player = initial_matches[0]
            if api_player_id and not player.api_football_player_id:
                player.api_football_player_id = str(api_player_id)
            return player

    return None


# ── Public API ─────────────────────────────────────────────────────────────────

@dataclass
class SeedSummary:
    teams_matched: int = 0
    teams_unmatched: int = 0
    teams_skipped: int = 0
    players_matched: int = 0
    players_unmatched: int = 0
    forms_created: int = 0


def _role_to_position(role: str) -> str:
    mapping = {
        "goalkeeper": "Goalkeeper",
        "defender": "Defender",
        "midfielder": "Midfielder",
        "forward": "Attacker",
    }
    return mapping.get(role.lower(), "Attacker")


def _match_teams(db: Session, api_teams: list[dict]) -> tuple[int, int]:
    """Fuzzy-match API-Football team names to DB teams, set api_football_team_id."""
    db_teams = db.query(Team).filter(Team.sport == "football").all()
    name_map = {t.name: t for t in db_teams}
    normalized_map = {_normalize(name): t for name, t in name_map.items()}

    matched = unmatched = 0
    for api_team in api_teams:
        api_name = api_team["name"]
        api_id = str(api_team["id"])

        # Exact match
        if api_name in name_map:
            name_map[api_name].api_football_team_id = api_id
            matched += 1
            continue

        # Fuzzy
        close = get_close_matches(_normalize(api_name), list(normalized_map), n=1, cutoff=0.75)
        if close:
            normalized_map[close[0]].api_football_team_id = api_id
            matched += 1
        else:
            logger.warning(f"No DB match for API team: {api_name!r}")
            unmatched += 1

    db.commit()
    return matched, unmatched


def _team_is_seeded(db: Session, team_id: int) -> bool:
    """Return True if the majority of a team's players already have form rows."""
    total = db.query(Player).filter(Player.team_id == team_id).count()
    if total == 0:
        return False
    seeded = (
        db.query(PlayerForm)
        .join(Player, PlayerForm.player_id == Player.id)
        .filter(Player.team_id == team_id)
        .count()
    )
    return seeded >= (total * 0.5)


def seed_player_form(
    db: Session,
    provider: ApiFootballProvider,
    wc_league_id: int,
    season: int,
    team_ids: Optional[list[int]] = None,
    skip_seeded: bool = True,
) -> SeedSummary:
    """Seed player_form rows from API-Football season stats.

    Step 1: match API-Football teams to DB teams (sets api_football_team_id).
    Step 2: for each matched team (or only those in team_ids), fetch squad and
            upsert PlayerForm rows using club stats where available.

    team_ids: restrict to specific DB team IDs (e.g. teams playing today).
    skip_seeded: if True (default), skip teams that already have form data for
                 ≥50% of their players — avoids wasting API calls on re-runs.
    """
    summary = SeedSummary()

    # Step 1: match teams (always runs for all teams to keep api_football_team_id fresh)
    api_teams = provider.get_wc_teams(wc_league_id, season)
    summary.teams_matched, summary.teams_unmatched = _match_teams(db, api_teams)
    logger.info(f"Team matching: {summary.teams_matched} matched, {summary.teams_unmatched} unmatched")

    team_filter = [Team.api_football_team_id.isnot(None), Team.sport == "football"]
    if team_ids:
        team_filter.append(Team.id.in_(team_ids))
    wc_teams = db.query(Team).filter(*team_filter).all()

    if skip_seeded:
        unseeded = [t for t in wc_teams if not _team_is_seeded(db, t.id)]
        summary.teams_skipped = len(wc_teams) - len(unseeded)
        if summary.teams_skipped:
            logger.info(f"Skipping {summary.teams_skipped} already-seeded team(s), processing {len(unseeded)}")
        wc_teams = unseeded

    # Use the officially registered WC squad (/players/squads) for player discovery
    # — this gives exactly the 26 players per team registered for the tournament.
    # Club stats are fetched separately per-player via get_player_club_stats.
    pre_season = season - 1  # used only for club stats lookup

    # Track processed player IDs across teams — the API sometimes lists the same
    # player under multiple teams (transfers), and the same player can be returned
    # by tier-1 matching for different squad entries.
    seen_player_ids: set[int] = set()

    for team in wc_teams:
        api_team_id = int(team.api_football_team_id)
        squad = provider.get_registered_squad(api_team_id)
        if not squad:
            logger.warning(f"{team.name}: no registered squad found")
        db_players = db.query(Player).filter(Player.team_id == team.id).all()

        for sp in squad:
            # Exclude already-matched players so ambiguous names (e.g. "E. Martínez"
            # with three MARTINEZ candidates) don't land on the wrong one.
            unseen_candidates = [p for p in db_players if p.id not in seen_player_ids]
            player = _match_player(sp.api_player_id, sp.name, unseen_candidates, db)
            if not player:
                summary.players_unmatched += 1
                continue

            seen_player_ids.add(player.id)

            summary.players_matched += 1

            # Prefer club stats — 30+ games vs 5–10 national team games per year.
            # Sleep 0.65s between calls to respect the 100 req/min API rate limit.
            if sp.api_player_id:
                time.sleep(0.65)
                club_sp = provider.get_player_club_stats(sp.api_player_id, pre_season)
                if not club_sp:
                    time.sleep(0.65)
                    club_sp = provider.get_player_club_stats(sp.api_player_id, pre_season - 1)
                if club_sp and club_sp.appearances > sp.appearances:
                    sp = club_sp

            xp = _pre_xp(sp)

            existing = db.query(PlayerForm).filter(PlayerForm.player_id == player.id).first()
            if existing:
                existing.pre_expected_points = xp
                existing.expected_points = xp
                existing.floor = "mid"
                existing.availability = "starter"
            else:
                db.add(PlayerForm(
                    player_id=player.id,
                    expected_points=xp,
                    floor="mid",
                    availability="starter",
                    wc_goals=0,
                    wc_assists=0,
                    wc_minutes=0,
                    wc_clean_sheets=0,
                    wc_games=0,
                    pre_expected_points=xp,
                ))
                summary.forms_created += 1

        db.commit()

    return summary


def update_player_form_after_match(
    db: Session,
    match,
    player_stats: list[FootballPlayerStat],
    fixture_result: FootballFixtureResult,
) -> None:
    """Increment WC accumulators and recompute expected_points after a match.

    Best-effort: errors do NOT propagate to the caller.
    """
    from app.models.match import Match

    # t1_conceded = goals scored against team1 = what team2 scored
    if fixture_result.team1_goals_et is not None:
        t1_conceded = fixture_result.team2_goals_et or 0
        t2_conceded = fixture_result.team1_goals_et or 0
    else:
        t1_conceded = fixture_result.team2_goals_reg
        t2_conceded = fixture_result.team1_goals_reg

    all_players = (
        db.query(Player)
        .filter(Player.team_id.in_([match.team_1_id, match.team_2_id]))
        .all()
    )
    player_map = {str(p.api_football_player_id): p for p in all_players if p.api_football_player_id}

    for stat in player_stats:
        player = player_map.get(str(stat.api_player_id))
        if not player:
            continue

        form = db.query(PlayerForm).filter(PlayerForm.player_id == player.id).first()
        if not form:
            continue

        is_team1 = player.team_id == match.team_1_id
        team_conceded = t1_conceded if is_team1 else t2_conceded
        clean_sheet = (team_conceded == 0) and (stat.minutes_played >= 60)

        form.wc_goals += stat.goals
        form.wc_assists += stat.assists
        form.wc_minutes += stat.minutes_played
        form.wc_games += 1
        if clean_sheet:
            form.wc_clean_sheets += 1

        position = _role_to_position(player.role)
        form.expected_points = _blend(form, position)
        form.floor = _derive_floor(form)
        form.updated_at = datetime.now(timezone.utc)

    db.commit()


def update_availability_from_lineup(
    db: Session,
    match,
    lineup: FixtureLineup,
) -> None:
    """Update availability for all players in both squads from a confirmed lineup."""
    all_starters = set(lineup.home_starters) | set(lineup.away_starters)
    all_subs = set(lineup.home_subs) | set(lineup.away_subs)
    all_in_lineup = all_starters | all_subs

    all_players = (
        db.query(Player)
        .filter(Player.team_id.in_([match.team_1_id, match.team_2_id]))
        .all()
    )

    for player in all_players:
        form = db.query(PlayerForm).filter(PlayerForm.player_id == player.id).first()
        if not form:
            continue

        api_id = int(player.api_football_player_id) if player.api_football_player_id else None
        if api_id is None:
            form.availability = "doubt"
        elif api_id in all_starters:
            form.availability = "starter"
        elif api_id in all_subs:
            form.availability = "rotation"
        else:
            form.availability = "doubt"

    db.commit()
