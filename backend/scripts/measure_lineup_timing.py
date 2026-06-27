"""One-off: measure when the confirmed XI becomes available on ESPN vs
api-football for a single fixture, to decide whether ESPN is worth adopting as
the lineup source (it appears to publish ~1h before kickoff vs api-football's
~20m). Run at a few checkpoints before kickoff (e.g. T-90/T-60/T-30 via cron);
each run appends one timestamped line to LOG_PATH.

Defaults target the first R32 tie (South Africa v Canada, 2026-06-28 19:00Z).
"""
import sys
import os
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.football_provider import ApiFootballProvider

ESPN_EVENT_ID = 760486
APIFOOTBALL_FIXTURE_ID = 1561329
KICKOFF = datetime(2026, 6, 28, 19, 0, tzinfo=timezone.utc)
LOG_PATH = "/home/lazy-fantasy/lineup_timing.log"


def espn_starters() -> str:
    try:
        r = requests.get(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={ESPN_EVENT_ID}",
            timeout=15)
        rosters = r.json().get("rosters") or []
        counts = [sum(1 for p in (t.get("roster") or []) if p.get("starter")) for t in rosters]
        formations = [t.get("formation") for t in rosters]
        return f"teams={len(rosters)} starters={counts} formations={formations}"
    except Exception as e:
        return f"error={e}"


def apifootball_lineup() -> str:
    try:
        prov = ApiFootballProvider(settings.FOOTBALL_API_KEY, settings.FOOTBALL_API_BASE_URL)
        lu = prov.get_fixture_lineup(APIFOOTBALL_FIXTURE_ID)
        if lu is None:
            return "lineup=None"
        return f"home_starters={len(lu.home_starters)} away_starters={len(lu.away_starters)}"
    except Exception as e:
        return f"error={e}"


def main():
    now = datetime.now(timezone.utc)
    mins_to_ko = round((KICKOFF - now).total_seconds() / 60)
    line = (f"{now.isoformat()} | T-{mins_to_ko}m | "
            f"ESPN[{espn_starters()}] | APIFOOTBALL[{apifootball_lineup()}]")
    print(line)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"(could not write {LOG_PATH}: {e})")


if __name__ == "__main__":
    main()
