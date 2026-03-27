"""CricAPI (cricketdata.org) implementation of CricketProvider."""
import logging
from typing import Any

import requests

from app.services.cricket_provider import CricketProvider, ProviderMatchInfo, ProviderPlayer

logger = logging.getLogger(__name__)


class CricApiProvider(CricketProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.cricapi.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _get(self, endpoint: str, **params) -> dict | None:
        """Make a GET request. Returns parsed JSON data dict or None on error."""
        try:
            resp = requests.get(
                f"{self.base_url}/{endpoint}",
                params={"apikey": self.api_key, **params},
                timeout=10,
            )
            if resp.status_code == 429:
                logger.warning("CricAPI rate limit hit")
                return None
            if resp.status_code != 200:
                logger.warning(f"CricAPI {endpoint} returned {resp.status_code}")
                return None
            body = resp.json()
            if body.get("status") != "success":
                logger.warning(f"CricAPI {endpoint} non-success: {body.get('status')}")
                return None
            return body.get("data")
        except Exception as e:
            logger.error(f"CricAPI request failed ({endpoint}): {e}")
            return None

    def get_match_info(self, provider_match_id: str) -> ProviderMatchInfo | None:
        data = self._get("match_info", id=provider_match_id)
        if not data:
            return None
        try:
            return self._parse_match_info(data)
        except Exception as e:
            logger.error(f"CricAPI parse error for match {provider_match_id}: {e}")
            return None

    def search_matches(self, series_id: str) -> list[ProviderMatchInfo]:
        data = self._get("series_info", id=series_id)
        if not data:
            return []
        matches = []
        for m in data.get("matchList", []):
            try:
                info = self._get("match_info", id=m.get("id", ""))
                if info:
                    matches.append(self._parse_match_info(info))
            except Exception as e:
                logger.warning(f"Failed to parse match in series {series_id}: {e}")
        return matches

    def _parse_match_info(self, data: dict) -> ProviderMatchInfo:
        match_id = data.get("id", "")
        name = data.get("name", "")
        status = data.get("status", "")
        teams = data.get("teams", [])
        team1_name = teams[0] if len(teams) > 0 else ""
        team2_name = teams[1] if len(teams) > 1 else ""

        # Playing XI — CricAPI returns `players` as a dict: {team_name: [{id, name, ...}]}
        players_data: dict[str, list[dict]] = data.get("players", {})
        lineup_announced = bool(players_data)

        team1_players = self._parse_players(players_data.get(team1_name, []), team1_name)
        team2_players = self._parse_players(players_data.get(team2_name, []), team2_name)

        # Enrich with batting/bowling stats from scorecard
        score = data.get("score", [])
        self._enrich_from_scorecard(score, team1_players, team2_players, team1_name)

        # Winner
        winner_name: str | None = None
        match_winner = data.get("matchWinner", "") or data.get("winner", "")
        if match_winner:
            winner_name = match_winner

        # Player of Match
        pom_name: str | None = None
        pom_list = data.get("playerOfMatch", []) or data.get("player_of_match", [])
        if pom_list and isinstance(pom_list, list) and pom_list:
            first = pom_list[0]
            pom_name = first.get("name") if isinstance(first, dict) else str(first)

        # Overs
        overs_completed: float | None = None
        if score:
            try:
                latest = score[-1]
                overs_str = latest.get("o", "")
                if overs_str:
                    overs_completed = float(overs_str)
            except (ValueError, TypeError, IndexError):
                pass

        return ProviderMatchInfo(
            provider_match_id=match_id,
            name=name,
            status=status,
            team1_name=team1_name,
            team2_name=team2_name,
            lineup_announced=lineup_announced,
            team1_players=team1_players,
            team2_players=team2_players,
            winner_name=winner_name,
            pom_name=pom_name,
            overs_completed=overs_completed,
        )

    def _parse_players(self, player_list: list[dict], team_name: str) -> list[ProviderPlayer]:
        result = []
        for p in player_list:
            result.append(ProviderPlayer(
                provider_id=str(p.get("id", "")),
                name=p.get("name", ""),
                team_name=team_name,
            ))
        return result

    def _enrich_from_scorecard(
        self,
        score: list[dict],
        team1_players: list[ProviderPlayer],
        team2_players: list[ProviderPlayer],
        team1_name: str,
    ) -> None:
        """Pull batting/bowling stats from scorecard innings data and set on ProviderPlayers."""
        # Build quick lookup by provider_id
        all_players = {p.provider_id: p for p in team1_players + team2_players}
        if not all_players:
            return

        for innings in score:
            batting = innings.get("batsmanData", innings.get("batting", []))
            bowling = innings.get("bowlerData", innings.get("bowling", []))

            for b in batting:
                pid = str(b.get("id", b.get("batsmanId", "")))
                if pid in all_players:
                    try:
                        all_players[pid].batting_runs = int(b.get("r", b.get("runs", 0)) or 0)
                        all_players[pid].batting_balls = int(b.get("b", b.get("balls", 0)) or 0)
                    except (ValueError, TypeError):
                        pass

            for bw in bowling:
                pid = str(bw.get("id", bw.get("bowlerId", "")))
                if pid in all_players:
                    try:
                        all_players[pid].bowling_wickets = int(bw.get("w", bw.get("wickets", 0)) or 0)
                        overs_str = str(bw.get("o", bw.get("overs", "0")))
                        all_players[pid].bowling_overs = float(overs_str) if overs_str else 0.0
                    except (ValueError, TypeError):
                        pass
