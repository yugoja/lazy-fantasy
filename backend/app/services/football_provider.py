"""api-football.com data provider for football match results."""
import logging
from dataclasses import dataclass, field

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
class FootballPlayerStat:
    api_player_id: int
    name: str
    team_api_id: int
    minutes_played: int
    goals: int
    assists: int
    red_card: bool
    own_goals: int              # always 0 — API limitation, admin corrects via form
    ingame_pen_saves: int
    shootout_pen_saves: int
    ingame_pen_misses: int


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

        t1_reg = _int(reg.get("home")) or 0
        t2_reg = _int(reg.get("away")) or 0
        t1_et = _int(et.get("home"))
        t2_et = _int(et.get("away"))
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
                pen_saves = int(goals_block.get("saves") or 0)
                pen_missed = int(pen_block.get("missed") or 0)
                shootout_saves = int(pen_block.get("saved") or 0)

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
