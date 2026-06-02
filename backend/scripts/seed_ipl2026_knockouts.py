"""
Seed / update IPL 2026 playoff fixtures (Qualifier 1, Eliminator, Qualifier 2, Final).

The two qualifier-stage matches that aren't decided yet (Qualifier 2 and the
Final) are created against a "TBD" placeholder team so the fixtures still appear
on the schedule. Once the line-ups are known, edit FIXTURES below and re-run:
the script matches each playoff by its (tournament, date) and UPDATES the teams
in place, so the match id — and any predictions on it — are preserved.

Looks up teams dynamically by short_name; resolves the cricket tournament
dynamically. Safe to run on any environment, and idempotent (re-runnable).

Usage:
  python scripts/seed_ipl2026_knockouts.py local
  python scripts/seed_ipl2026_knockouts.py prod

Times stored as UTC (IST = UTC+5:30). All four playoffs are 19:30 IST → 14:00 UTC.

NOTE: scripts/seed_ipl2026_fixtures.py deletes FUTURE scheduled matches whose
teams aren't one of the 10 IPL franchises — that includes these TBD playoffs.
The group stage is over, so that seeder shouldn't run again; if it does, re-run
this script afterwards to recreate the playoffs.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from app.database import SessionLocal
from app.models import Match, MatchStatus
from app.models.team import Team
from app.models.tournament import Tournament

# Placeholder team used for playoffs whose line-up isn't decided yet.
TBD_NAME = "To Be Decided"
TBD_SHORT = "TBD"

IST_TO_UTC = {
    "15:30 IST": (10, 0),
    "19:30 IST": (14, 0),
}

# label is for humans/logs only (the Match model has no playoff-name column).
# Use TBD_SHORT for either side that isn't decided yet.
FIXTURES = [
    {"label": "Qualifier 1", "date": "2026-05-26", "time": "19:30 IST", "team1": "RCB",     "team2": "GT"},
    {"label": "Eliminator",  "date": "2026-05-27", "time": "19:30 IST", "team1": "RR",      "team2": "SRH"},
    {"label": "Qualifier 2", "date": "2026-05-29", "time": "19:30 IST", "team1": "GT",      "team2": "RR"},
    # Final: RCB (won Q1) vs GT (won Q2).
    {"label": "Final",       "date": "2026-05-31", "time": "19:30 IST", "team1": "RCB",     "team2": "GT"},
]


def make_start_time(date_str: str, time_str: str) -> datetime:
    hour, minute = IST_TO_UTC[time_str]
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.replace(hour=hour, minute=minute)


def resolve_tournament(db) -> Tournament:
    """Prefer the prod IPL tournament (id 2); else the sole cricket tournament."""
    t = db.query(Tournament).filter(Tournament.id == 2, Tournament.sport == "cricket").first()
    if t:
        return t
    cricket = db.query(Tournament).filter(Tournament.sport == "cricket").all()
    if len(cricket) == 1:
        return cricket[0]
    if not cricket:
        print("ERROR: no cricket tournament found.")
    else:
        print(f"ERROR: multiple cricket tournaments {[c.id for c in cricket]}; expected id 2.")
    db.close()
    sys.exit(1)


def ensure_tbd_team(db) -> Team:
    tbd = db.query(Team).filter(Team.short_name == TBD_SHORT, Team.sport == "cricket").first()
    if tbd:
        return tbd
    tbd = Team(name=TBD_NAME, short_name=TBD_SHORT, sport="cricket")
    db.add(tbd)
    db.flush()
    print(f"Created placeholder team '{TBD_SHORT}' (id {tbd.id})")
    return tbd


def run(mode: str):
    db = SessionLocal()

    tournament = resolve_tournament(db)
    print(f"Tournament: id={tournament.id} '{tournament.name}'")

    tbd = ensure_tbd_team(db)

    teams = db.query(Team).filter(Team.sport == "cricket").all()
    team_id = {t.short_name: t.id for t in teams}

    needed = {f["team1"] for f in FIXTURES} | {f["team2"] for f in FIXTURES}
    missing = sorted(s for s in needed if s not in team_id)
    if missing:
        print(f"ERROR: teams not found in DB: {missing}")
        db.close()
        sys.exit(1)

    inserted = updated = unchanged = 0
    for f in FIXTURES:
        t1, t2 = team_id[f["team1"]], team_id[f["team2"]]
        start = make_start_time(f["date"], f["time"])

        # Identity = (tournament, calendar date). Each playoff is on a unique date,
        # so this survives the TBD → real-team swap on a later re-run.
        existing = [
            m for m in db.query(Match).filter(
                Match.tournament_id == tournament.id,
                Match.status == MatchStatus.SCHEDULED,
            ).all()
            if m.start_time.date() == start.date()
        ]

        tbd_label = f"{f['team1']} v {f['team2']}"
        if existing:
            m = existing[0]
            # start_time may come back tz-aware from Postgres; compare naive UTC.
            cur_start = m.start_time.replace(tzinfo=None)
            if (m.team_1_id, m.team_2_id, cur_start) == (t1, t2, start):
                unchanged += 1
                print(f"  = {f['label']:<12} {tbd_label} unchanged (id {m.id})")
            else:
                m.team_1_id, m.team_2_id, m.start_time = t1, t2, start
                updated += 1
                print(f"  ~ {f['label']:<12} {tbd_label} updated (id {m.id})")
        else:
            db.add(Match(
                tournament_id=tournament.id,
                team_1_id=t1,
                team_2_id=t2,
                start_time=start,
                status=MatchStatus.SCHEDULED,
            ))
            inserted += 1
            print(f"  + {f['label']:<12} {tbd_label} inserted ({f['date']} {f['time']})")

    db.commit()
    db.close()
    print(f"Done [{mode}]: {inserted} inserted, {updated} updated, {unchanged} unchanged")


if __name__ == "__main__":
    mode = "local"
    if len(sys.argv) > 1:
        if sys.argv[1] in ("local", "prod"):
            mode = sys.argv[1]
        else:
            print("Usage: python scripts/seed_ipl2026_knockouts.py [local|prod]")
            sys.exit(1)

    print(f"Mode: {mode}")
    run(mode)
