"""
Seed the full FIFA World Cup 2026 knockout bracket (Round of 32 -> Final).

Two phases, both idempotent / re-runnable:

  seed  (default): create the 32 knockout matches from the skeleton JSON, with a
        synthetic "TBD" team on both sides of every tie. Identity is
        (tournament, stage, start_time) so a later --fill that swaps in real
        teams keeps the same match id (and any predictions on it).

  --fill: pull api-football's knockout fixtures (league=1, season=2026) and, for
        each tie it has decided, fill the real team_1/team_2 + external_match_id
        on the matching skeleton match (matched by stage + kickoff datetime).
        Re-run as ties decide; api-football only publishes knockout fixtures
        progressively, so unmatched skeleton slots simply stay TBD for now.

The skeleton JSON (world_cup_2026_knockouts.json) is authored from the official
schedule. Each entry: {slot, stage, kickoff_utc, venue, city}. `slot` is the
official match number (73-104) for humans/logs; the model has no slot column.

Usage (from backend/):
  python -m scripts.seed_worldcup_knockouts                 # dry-run seed
  python -m scripts.seed_worldcup_knockouts --apply         # write skeleton
  python -m scripts.seed_worldcup_knockouts --fill          # dry-run fill
  python -m scripts.seed_worldcup_knockouts --fill --apply  # write fill
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.config import settings
from app.models import Match, MatchStatus, Team, Tournament

DEFAULT_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "world_cup_2026_knockouts.json",
)

TBD_NAME = "To Be Decided"
TBD_SHORT = "TBD"

WC_LEAGUE_ID = 1
WC_SEASON = 2026
API_BASE = "https://v3.football.api-sports.io"

# JSON stage label -> canonical Match.stage (mirrors seed_worldcup_fixtures.py /
# scoring_football.KNOCKOUT_STAGES).
STAGE_MAP = {
    "Round of 32": "R32",
    "Round of 16": "R16",
    "Quarter-final": "QF", "Quarter-finals": "QF",
    "Semi-final": "SF", "Semi-finals": "SF",
    "Third-place Playoff": "THIRD", "Third Place Play-off": "THIRD",
    "3rd Place Final": "THIRD",
    "Final": "FINAL",
}
# Matches to expect per stage — a sanity check on the skeleton.
EXPECTED_COUNTS = {"R32": 16, "R16": 8, "QF": 4, "SF": 2, "THIRD": 1, "FINAL": 1}

# How close (in hours) an api-football kickoff must be to a skeleton slot's
# start_time to be considered the same tie.
FILL_WINDOW = timedelta(hours=6)


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def resolve_tournament(db) -> Tournament:
    fb = db.query(Tournament).filter(Tournament.sport == "football").all()
    if len(fb) == 1:
        return fb[0]
    if not fb:
        print("ERROR: no football tournament found. Seed group fixtures first.")
    else:
        print(f"ERROR: multiple football tournaments {[t.id for t in fb]}; expected one.")
    db.close()
    sys.exit(1)


def ensure_tbd_team(db) -> Team:
    tbd = db.query(Team).filter(Team.short_name == TBD_SHORT, Team.sport == "football").first()
    if tbd:
        return tbd
    tbd = Team(name=TBD_NAME, short_name=TBD_SHORT, sport="football")
    db.add(tbd)
    db.flush()
    print(f"Created placeholder team '{TBD_SHORT}' (id {tbd.id})")
    return tbd


def _load_skeleton(path):
    with open(path) as f:
        data = json.load(f)
    rows = data["matches"]
    out = []
    for r in rows:
        stage = STAGE_MAP.get(r["stage"])
        if stage is None:
            raise ValueError(f"Unrecognised stage {r['stage']!r} (slot {r.get('slot')})")
        out.append({
            "slot": r.get("slot"),
            "stage": stage,
            "start": _naive_utc(datetime.fromisoformat(r["kickoff_utc"].replace("Z", "+00:00"))),
            "venue": r.get("venue"),
        })
    return out


def _knockout_matches(db, tournament_id):
    return (
        db.query(Match)
        .filter(Match.tournament_id == tournament_id,
                Match.stage.in_(list(EXPECTED_COUNTS)))
        .all()
    )


# ---------------------------------------------------------------------------
# Phase 1: seed the TBD skeleton
# ---------------------------------------------------------------------------
def _json_path() -> str:
    for a in sys.argv[1:]:
        if a.endswith(".json"):
            return a
    return DEFAULT_JSON


def seed(db, tournament, apply: bool):
    rows = _load_skeleton(_json_path())
    counts = {}
    for r in rows:
        counts[r["stage"]] = counts.get(r["stage"], 0) + 1
    print(f"skeleton: {len(rows)} matches, by stage {counts}")
    if counts != EXPECTED_COUNTS:
        print(f"  WARNING: expected {EXPECTED_COUNTS}")
    # identity = (stage, start_time); verify uniqueness
    keys = [(r["stage"], r["start"]) for r in rows]
    if len(set(keys)) != len(keys):
        print("  ERROR: duplicate (stage, start_time) in skeleton — identity not unique")
        return
    tbd = ensure_tbd_team(db)
    existing = {(m.stage, _naive_utc(m.start_time)): m for m in _knockout_matches(db, tournament.id)}

    inserted = unchanged = 0
    for r in rows:
        key = (r["stage"], r["start"])
        if key in existing:
            unchanged += 1
            continue
        if apply:
            db.add(Match(
                tournament_id=tournament.id,
                team_1_id=tbd.id, team_2_id=tbd.id,
                start_time=r["start"], status=MatchStatus.SCHEDULED,
                stage=r["stage"],
            ))
        inserted += 1
        print(f"  + slot {r['slot']} {r['stage']:5} {r['start']} TBD v TBD ({r['venue']})")
    if apply:
        db.commit()
    print(f"seed [{'APPLY' if apply else 'dry'}]: {inserted} inserted, {unchanged} already present")


# ---------------------------------------------------------------------------
# Phase 2: fill decided teams from api-football
# ---------------------------------------------------------------------------
def fill(db, tournament, apply: bool):
    H = {"x-apisports-key": settings.FOOTBALL_API_KEY}
    r = requests.get(f"{API_BASE}/fixtures", headers=H,
                     params={"league": WC_LEAGUE_ID, "season": WC_SEASON}, timeout=20)
    fixtures = r.json().get("response", [])
    ko_fixtures = [f for f in fixtures if "Group" not in f["league"]["round"]]
    print(f"api-football knockout fixtures available: {len(ko_fixtures)}")

    team_by_api = {t.api_football_team_id: t for t in
                   db.query(Team).filter(Team.sport == "football",
                                         Team.api_football_team_id != None).all()}  # noqa: E711
    ko_matches = _knockout_matches(db, tournament.id)

    filled = skipped = unmatched = 0
    for f in ko_fixtures:
        stage = STAGE_MAP.get(f["league"]["round"])
        if stage is None:
            continue
        kickoff = _naive_utc(datetime.fromisoformat(f["fixture"]["date"]))
        # nearest skeleton match of the same stage within the window
        cands = [m for m in ko_matches if m.stage == stage
                 and abs(_naive_utc(m.start_time) - kickoff) <= FILL_WINDOW]
        if not cands:
            unmatched += 1
            print(f"  ? no skeleton slot for {stage} @ {kickoff} "
                  f"({f['teams']['home']['name']} v {f['teams']['away']['name']})")
            continue
        m = min(cands, key=lambda mm: abs(_naive_utc(mm.start_time) - kickoff))
        home = team_by_api.get(str(f["teams"]["home"]["id"]))
        away = team_by_api.get(str(f["teams"]["away"]["id"]))
        if not home or not away:
            unmatched += 1
            print(f"  ? team not in DB: {f['teams']['home']['name']} / {f['teams']['away']['name']}")
            continue
        fixture_id = str(f["fixture"]["id"])
        if (m.team_1_id, m.team_2_id, m.external_match_id) == (home.id, away.id, fixture_id):
            skipped += 1
            continue
        if apply:
            m.team_1_id, m.team_2_id = home.id, away.id
            m.external_match_id = fixture_id
        filled += 1
        print(f"  ~ {stage} match {m.id}: {home.short_name} v {away.short_name} "
              f"(fixture {fixture_id})")
    if apply:
        db.commit()
    print(f"fill [{'APPLY' if apply else 'dry'}]: {filled} filled, {skipped} unchanged, "
          f"{unmatched} unmatched")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    do_fill = "--fill" in sys.argv
    db = SessionLocal()
    tournament = resolve_tournament(db)
    print(f"Tournament: id={tournament.id} '{tournament.name}'")
    if do_fill:
        fill(db, tournament, apply)
    else:
        seed(db, tournament, apply)
    db.close()
