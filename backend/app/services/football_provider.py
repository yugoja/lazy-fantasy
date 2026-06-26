"""api-football.com data provider for football match results."""
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class FootballFixtureResult:
    fixture_id: int
    status_short: str           # "FT" | "AET" | "PEN"
    home_team_api_id: int
    away_team_api_id: int
    team1_goals_reg: int        # home = team_1
    team2_goals_reg: int
    team1_goals_et: int | None
    team2_goals_et: int | None
    penalty_team1: int | None
    penalty_team2: int | None


@dataclass
class WCSquadPlayer:
    api_player_id: int
    name: str
    position: str          # "Goalkeeper" | "Defender" | "Midfielder" | "Attacker"
    appearances: int
    minutes: int
    goals: int
    assists: int
    clean_sheets: int      # GK/DEF relevant; saves for GK, 0 for others


@dataclass
class FixtureLineup:
    home_starters: list[int]   # api_player_ids
    away_starters: list[int]
    home_subs: list[int]
    away_subs: list[int]


@dataclass
class LineupSlot:
    api_player_id: int
    row: int   # 1 = keeper, rising toward attack
    col: int   # position across that line (1 = one touchline)


@dataclass
class TeamFormation:
    formation: str                 # e.g. "4-2-3-1"
    starters: list[LineupSlot]


@dataclass
class FootballPlayerStat:
    api_player_id: int
    name: str
    team_api_id: int
    minutes_played: int
    goals: int
    assists: int
    red_card: bool
    own_goals: int              # filled from fixtures/events (see get_fixture_events)
    ingame_pen_saves: int
    shootout_pen_saves: int
    ingame_pen_misses: int


@dataclass
class FootballGoalEvent:
    """A Goal-type event from fixtures/events. `detail` is one of
    "Normal Goal" | "Own Goal" | "Penalty" | "Missed Penalty". `is_shootout`
    marks the post-match penalty shootout (which never feeds the scoreline)."""
    api_player_id: int
    name: str
    team_api_id: int
    detail: str
    is_shootout: bool


_FINISHED_STATUSES = {"FT", "AET", "PEN"}


class ApiFootballProvider:
    def __init__(self, api_key: str, base_url: str = "https://v3.football.api-sports.io"):
        self._key = api_key
        self._base = base_url.rstrip("/")

    def _get(self, endpoint: str, **params) -> dict | None:
        url = f"{self._base}/{endpoint.lstrip('/')}"
        headers = {"x-apisports-key": self._key}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 429:
                logger.warning("api-football rate limit hit")
                return None
            resp.raise_for_status()
            data = resp.json()
            errors = data.get("errors", {})
            if errors:
                logger.error(f"api-football error: {errors}")
                return None
            return data
        except Exception as e:
            logger.error(f"api-football request failed: {e}")
            return None

    def get_fixture_result(self, fixture_id: int) -> FootballFixtureResult | None:
        data = self._get("fixtures", id=fixture_id)
        if not data:
            return None
        responses = data.get("response", [])
        if not responses:
            return None
        f = responses[0]
        status_short = f["fixture"]["status"]["short"]
        if status_short not in _FINISHED_STATUSES:
            return None

        score = f["score"]
        home_id = f["teams"]["home"]["id"]
        away_id = f["teams"]["away"]["id"]

        def _int(val) -> int | None:
            return int(val) if val is not None else None

        reg = score.get("fulltime", {})
        et = score.get("extratime", {})
        pen = score.get("penalty", {})
        final = f.get("goals", {}) or {}  # final reg+ET total, excludes shootout

        t1_reg = _int(reg.get("home")) or 0
        t2_reg = _int(reg.get("away")) or 0
        # `score.extratime` holds goals scored *during* ET only, not the running
        # total — so the end-of-ET scoreline is the top-level `goals` (reg+ET,
        # shootout excluded). Only populate it when ET was actually played.
        went_to_et = et.get("home") is not None or et.get("away") is not None
        t1_et = _int(final.get("home")) if went_to_et else None
        t2_et = _int(final.get("away")) if went_to_et else None
        p1 = _int(pen.get("home"))
        p2 = _int(pen.get("away"))

        return FootballFixtureResult(
            fixture_id=fixture_id,
            status_short=status_short,
            home_team_api_id=home_id,
            away_team_api_id=away_id,
            team1_goals_reg=t1_reg,
            team2_goals_reg=t2_reg,
            team1_goals_et=t1_et,
            team2_goals_et=t2_et,
            penalty_team1=p1,
            penalty_team2=p2,
        )

    def get_wc_teams(self, league_id: int, season: int) -> list[dict]:
        """Return list of {id, name} dicts for all teams in the WC league."""
        data = self._get("teams", league=league_id, season=season)
        if not data:
            return []
        return [
            {"id": entry["team"]["id"], "name": entry["team"]["name"]}
            for entry in data.get("response", [])
        ]

    def get_registered_squad(self, team_id: int) -> list[WCSquadPlayer]:
        """Return the officially registered WC squad (26 players) from /players/squads.

        No stats — just player IDs, names, and positions. Use get_player_club_stats
        separately to enrich with club-season data.
        """
        data = self._get("players/squads", team=team_id)
        if not data or not data.get("response"):
            return []
        players = []
        for entry in data["response"]:
            for p in entry.get("players", []):
                pos = p.get("position") or "Attacker"
                players.append(WCSquadPlayer(
                    api_player_id=int(p["id"]),
                    name=p.get("name", ""),
                    position=pos,
                    appearances=0,
                    minutes=0,
                    goals=0,
                    assists=0,
                    clean_sheets=0,
                ))
        return players

    def get_wc_squad(self, team_id: int, season: int, league_id: Optional[int] = None) -> list[WCSquadPlayer]:
        """Fetch all squad players for a team with their season stats (handles pagination).

        Pass league_id to restrict to a specific competition (e.g. WC in-progress);
        omit it to get full club-season stats (used for pre-tournament seeding).
        """
        players: list[WCSquadPlayer] = []
        page = 1
        while True:
            params: dict = {"team": team_id, "season": season, "page": page}
            if league_id is not None:
                params["league"] = league_id
            data = self._get("players", **params)
            if not data:
                break
            response = data.get("response", [])
            if not response:
                break
            for entry in response:
                p = entry.get("player", {})
                stats = (entry.get("statistics") or [{}])[0]
                games = stats.get("games", {})
                goals_block = stats.get("goals", {})
                position = games.get("position") or "Attacker"
                appearances = int(games.get("appearences") or 0)
                minutes = int(games.get("minutes") or 0)
                goals = int(goals_block.get("total") or 0)
                assists = int(goals_block.get("assists") or 0)
                # For GK, use saves as clean_sheets proxy; for others use conceded=0 indicator
                clean_sheets = int(goals_block.get("saves") or 0)
                players.append(WCSquadPlayer(
                    api_player_id=int(p.get("id", 0)),
                    name=p.get("name", ""),
                    position=position,
                    appearances=appearances,
                    minutes=minutes,
                    goals=goals,
                    assists=assists,
                    clean_sheets=clean_sheets,
                ))
            paging = data.get("paging", {})
            if paging.get("current", 1) >= paging.get("total", 1):
                break
            page += 1
        return players

    def get_player_club_stats(self, player_id: int, season: int) -> Optional[WCSquadPlayer]:
        """Get a player's primary club stats for the season.

        Queries by player ID (not team), returns the stats entry with the most
        appearances — which is almost always the club, not the national team.
        Returns None if no data or zero appearances found.
        """
        data = self._get("players", id=player_id, season=season)
        if not data:
            return None
        response = data.get("response", [])
        if not response:
            return None

        player_entry = response[0]
        p = player_entry.get("player", {})
        statistics = player_entry.get("statistics") or []
        if not statistics:
            return None

        best = max(statistics, key=lambda s: int(s.get("games", {}).get("appearences") or 0))
        games = best.get("games", {})
        goals_block = best.get("goals", {})
        appearances = int(games.get("appearences") or 0)
        if appearances == 0:
            return None

        return WCSquadPlayer(
            api_player_id=int(p.get("id", player_id)),
            name=p.get("name", ""),
            position=games.get("position") or "Attacker",
            appearances=appearances,
            minutes=int(games.get("minutes") or 0),
            goals=int(goals_block.get("total") or 0),
            assists=int(goals_block.get("assists") or 0),
            clean_sheets=int(goals_block.get("saves") or 0),
        )

    def get_fixture_lineup(self, fixture_id: int) -> Optional[FixtureLineup]:
        """Fetch confirmed lineups for a fixture. Returns None if not yet announced."""
        data = self._get("fixtures/lineups", fixture=fixture_id)
        if not data:
            return None
        response = data.get("response", [])
        if len(response) < 2:
            return None

        def _extract_ids(team_obj: dict, key: str) -> list[int]:
            return [int(e["player"]["id"]) for e in team_obj.get(key, []) if e.get("player", {}).get("id")]

        home = response[0]
        away = response[1]
        return FixtureLineup(
            home_starters=_extract_ids(home, "startXI"),
            away_starters=_extract_ids(away, "startXI"),
            home_subs=_extract_ids(home, "substitutes"),
            away_subs=_extract_ids(away, "substitutes"),
        )

    def get_fixture_formations(self, fixture_id: int) -> Optional[tuple[TeamFormation, TeamFormation]]:
        """Confirmed (home, away) formations with each starter's grid position.

        Returns None until the lineup is announced.
        """
        data = self._get("fixtures/lineups", fixture=fixture_id)
        if not data:
            return None
        response = data.get("response", [])
        if len(response) < 2:
            return None

        def _team(obj: dict) -> TeamFormation:
            slots: list[LineupSlot] = []
            for e in obj.get("startXI", []):
                player = e.get("player", {})
                pid, grid = player.get("id"), player.get("grid")
                if pid is None or not grid or ":" not in str(grid):
                    continue
                row, col = str(grid).split(":", 1)
                try:
                    slots.append(LineupSlot(int(pid), int(row), int(col)))
                except ValueError:
                    continue
            return TeamFormation(formation=obj.get("formation") or "", starters=slots)

        return _team(response[0]), _team(response[1])

    def get_player_stats(self, fixture_id: int) -> list[FootballPlayerStat]:
        data = self._get("fixtures/players", fixture=fixture_id)
        if not data:
            return []
        stats: list[FootballPlayerStat] = []
        for team_obj in data.get("response", []):
            team_api_id = team_obj["team"]["id"]
            for p in team_obj.get("players", []):
                player_info = p.get("player", {})
                s = (p.get("statistics") or [{}])[0]
                games = s.get("games", {})
                goals_block = s.get("goals", {})
                pen_block = s.get("penalty", {})

                minutes = int(games.get("minutes") or 0)
                goals = int(goals_block.get("total") or 0)
                assists = int(goals_block.get("assists") or 0)
                red_card = bool(s.get("cards", {}).get("red"))
                # `goals.saves` is the keeper's TOTAL shots saved (routine saves),
                # which the v2 model does not score. The penalty-save bonus comes
                # only from `penalty.saved` (penalties the keeper actually saved).
                pen_saves = int(pen_block.get("saved") or 0)
                pen_missed = int(pen_block.get("missed") or 0)
                # fixtures/players does not separate shootout saves; they would
                # need the fixtures/events endpoint. Keep this bucket empty for now.
                shootout_saves = 0

                stats.append(FootballPlayerStat(
                    api_player_id=int(player_info.get("id", 0)),
                    name=player_info.get("name", ""),
                    team_api_id=team_api_id,
                    minutes_played=minutes,
                    goals=goals,
                    assists=assists,
                    red_card=red_card,
                    own_goals=0,
                    ingame_pen_saves=pen_saves,
                    shootout_pen_saves=shootout_saves,
                    ingame_pen_misses=pen_missed,
                ))
        return stats

    def get_fixture_events(self, fixture_id: int) -> list[FootballGoalEvent]:
        """Goal-type events for a fixture (fixtures/events).

        `fixtures/players` exposes neither own goals nor the penalty shootout, so
        these are sourced here: own goals (detail "Own Goal") and shootout
        penalties (comments "Penalty Shootout")."""
        data = self._get("fixtures/events", fixture=fixture_id)
        if not data:
            return []
        events: list[FootballGoalEvent] = []
        for e in data.get("response", []):
            if e.get("type") != "Goal":
                continue
            player = e.get("player", {}) or {}
            pid = player.get("id")
            if pid is None:
                continue
            comments = (e.get("comments") or "")
            events.append(FootballGoalEvent(
                api_player_id=int(pid),
                name=player.get("name", ""),
                team_api_id=int((e.get("team", {}) or {}).get("id", 0)),
                detail=e.get("detail", "") or "",
                is_shootout="shootout" in comments.lower(),
            ))
        return events
