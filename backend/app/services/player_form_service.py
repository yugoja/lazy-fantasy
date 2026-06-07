"""M2.5 — Real player form data layer.

Replaces position-based stubs with API-Football-derived expected_points.
Blends pre-tournament season stats with WC accumulator data as the
tournament progresses.
"""

from __future__ import annotations

import logging
import re
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

logger = logging.getLogger(__name__)

# ── Position stubs (fallback when no API data) ────────────────────────────────

_POSITION_XP: dict[str, float] = {
    "Attacker": 10.0,
    "Midfielder": 8.0,
    "Defender": 6.0,
    "Goalkeeper": 5.0,
}

# ── Position-aware xp formulas ────────────────────────────────────────────────


def _pre_xp(squad_player: WCSquadPlayer) -> float:
    """Compute pre-tournament expected points from season stats (0–15 range)."""
    pos = squad_player.position
    if squad_player.appearances == 0:
        return _POSITION_XP.get(pos, 6.0)

    apps = squad_player.appearances
    per90_base = squad_player.minutes / 90.0 / apps if apps else 0.0
    goals_per90 = squad_player.goals / (squad_player.minutes / 90.0) if squad_player.minutes else 0.0
    assists_per90 = squad_player.assists / (squad_player.minutes / 90.0) if squad_player.minutes else 0.0
    cs_rate = squad_player.clean_sheets / apps if apps else 0.0

    if pos == "Goalkeeper":
        return round(cs_rate * 8 + per90_base * 2, 2)
    elif pos == "Defender":
        return round(cs_rate * 5 + assists_per90 * 3 + goals_per90 * 4, 2)
    elif pos == "Midfielder":
        return round(goals_per90 * 5 + assists_per90 * 4, 2)
    else:  # Attacker
        return round(goals_per90 * 6 + assists_per90 * 3, 2)


def _wc_xp(form: PlayerForm, position: str) -> float:
    """Compute WC-derived expected points from in-tournament accumulators."""
    if form.wc_games == 0:
        return 0.0

    games = form.wc_games
    minutes = form.wc_minutes
    per90_base = minutes / 90.0 / games if games else 0.0
    goals_per90 = form.wc_goals / (minutes / 90.0) if minutes else 0.0
    assists_per90 = form.wc_assists / (minutes / 90.0) if minutes else 0.0
    cs_rate = form.wc_clean_sheets / games if games else 0.0

    if position == "Goalkeeper":
        return round(cs_rate * 8 + per90_base * 2, 2)
    elif position == "Defender":
        return round(cs_rate * 5 + assists_per90 * 3 + goals_per90 * 4, 2)
    elif position == "Midfielder":
        return round(goals_per90 * 5 + assists_per90 * 4, 2)
    else:  # Attacker
        return round(goals_per90 * 6 + assists_per90 * 3, 2)


def _derive_floor(form: PlayerForm) -> str:
    if form.wc_games == 0:
        return "mid"
    avg_min = form.wc_minutes / form.wc_games
    if avg_min >= 60:
        return "high"
    if avg_min >= 30:
        return "mid"
    return "low"


def _blend(form: PlayerForm, position: str) -> float:
    """Blend pre-tournament and WC-derived expected points."""
    wc_weight = min(form.wc_games / 3.0, 1.0)
    pre = form.pre_expected_points if form.pre_expected_points is not None else _POSITION_XP.get(position, 6.0)
    wc = _wc_xp(form, position)
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

    return None


# ── Public API ─────────────────────────────────────────────────────────────────

@dataclass
class SeedSummary:
    teams_matched: int = 0
    teams_unmatched: int = 0
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


def seed_player_form(
    db: Session,
    provider: ApiFootballProvider,
    wc_league_id: int,
    season: int,
) -> SeedSummary:
    """One-time seeding of player_form rows from API-Football season stats.

    Step 1: match API-Football teams to DB teams (sets api_football_team_id).
    Step 2: for each matched team, fetch squad and upsert PlayerForm rows.
    """
    summary = SeedSummary()

    # Step 1: match teams
    api_teams = provider.get_wc_teams(wc_league_id, season)
    summary.teams_matched, summary.teams_unmatched = _match_teams(db, api_teams)
    logger.info(f"Team matching: {summary.teams_matched} matched, {summary.teams_unmatched} unmatched")

    wc_teams = (
        db.query(Team)
        .filter(Team.api_football_team_id.isnot(None), Team.sport == "football")
        .all()
    )

    # For pre-tournament seeding use prior club season (no WC league filter).
    # Once the WC is underway, WC stats accumulate via update_player_form_after_match.
    pre_season = season - 1

    # Track processed player IDs across teams — the API sometimes lists the same
    # player under multiple teams (transfers), and the same player can be returned
    # by tier-1 matching for different squad entries.
    seen_player_ids: set[int] = set()

    for team in wc_teams:
        api_team_id = int(team.api_football_team_id)
        squad = provider.get_wc_squad(api_team_id, pre_season)
        db_players = db.query(Player).filter(Player.team_id == team.id).all()

        for sp in squad:
            player = _match_player(sp.api_player_id, sp.name, db_players, db)
            if not player:
                summary.players_unmatched += 1
                continue

            if player.id in seen_player_ids:
                continue
            seen_player_ids.add(player.id)

            summary.players_matched += 1
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
