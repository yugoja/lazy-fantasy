"""
Seed FIFA World Cup 2026 group-stage fixtures from a JSON file.

Creates (idempotently):
  - 1 Tournament  (name from JSON, sport='football')
  - the teams referenced by the fixtures (sport='football', short_name = FIFA code)
  - the matches (team_1 = home, team_2 = away, stage mapped to the scorer's
    canonical values, kickoff stored as naive UTC)

Re-running is safe: the tournament/teams are matched by name and matches by
(tournament, home, away, kickoff), so duplicates are skipped.

Squads/players are NOT in this file — seed those separately before the player
picks in the predict flow will work.

Usage (from backend/, or in the compose backend container):
  python -m scripts.seed_worldcup_fixtures
  python -m scripts.seed_worldcup_fixtures path/to/world_cup_2026_group_stage.json
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Match, MatchStatus, Team, Tournament
from app.services.scoring_football import KNOCKOUT_STAGES

DEFAULT_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "world_cup_2026_group_stage.json",
)

# JSON stage label → Match.stage canonical value (see scoring_football.KNOCKOUT_STAGES)
STAGE_MAP = {
    "Group Stage": "GROUP",
    "Round of 32": "R32",
    "Round of 16": "R16",
    "Quarter-final": "QF",
    "Quarter-finals": "QF",
    "Semi-final": "SF",
    "Semi-finals": "SF",
    "Third-place Playoff": "THIRD",
    "Third Place Play-off": "THIRD",
    "3rd Place Final": "THIRD",   # api-football's label
    "Final": "FINAL",
}

# FIFA tri-codes for the 48 participating nations (Team.short_name).
FIFA_CODES = {
    "Algeria": "ALG", "Argentina": "ARG", "Australia": "AUS", "Austria": "AUT",
    "Belgium": "BEL", "Bosnia and Herzegovina": "BIH", "Brazil": "BRA",
    "Canada": "CAN", "Cape Verde": "CPV", "Colombia": "COL", "Congo DR": "COD",
    "Croatia": "CRO", "Curaçao": "CUW", "Czech Republic": "CZE", "Ecuador": "ECU",
    "Egypt": "EGY", "England": "ENG", "France": "FRA", "Germany": "GER",
    "Ghana": "GHA", "Haiti": "HAI", "Iran": "IRN", "Iraq": "IRQ",
    "Ivory Coast": "CIV", "Japan": "JPN", "Jordan": "JOR", "Mexico": "MEX",
    "Morocco": "MAR", "Netherlands": "NED", "New Zealand": "NZL", "Norway": "NOR",
    "Panama": "PAN", "Paraguay": "PAR", "Portugal": "POR", "Qatar": "QAT",
    "Saudi Arabia": "KSA", "Scotland": "SCO", "Senegal": "SEN",
    "South Africa": "RSA", "South Korea": "KOR", "Spain": "ESP", "Sweden": "SWE",
    "Switzerland": "SUI", "Tunisia": "TUN", "Türkiye": "TUR",
    "United States": "USA", "Uruguay": "URU", "Uzbekistan": "UZB",
}


def short_name_for(team_name: str) -> str:
    if team_name in FIFA_CODES:
        return FIFA_CODES[team_name]
    # Fallback: first 3 alpha chars uppercased (keeps it deterministic).
    alpha = "".join(c for c in team_name if c.isalpha())
    return (alpha[:3] or team_name[:3]).upper()


def parse_kickoff(iso: str) -> datetime:
    """ISO-8601 (…Z) → naive UTC datetime, matching how the app stores times."""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def naive_utc(dt: datetime) -> datetime:
    """Normalize a possibly tz-aware datetime (Postgres returns aware for
    timestamptz columns) to naive UTC, so dedup keys compare consistently."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def run(json_path: str):
    with open(json_path) as f:
        data = json.load(f)

    fixtures = data["matches"]
    tournament_name = data.get("tournament", "FIFA World Cup 2026")
    kickoffs = [parse_kickoff(m["kickoff_utc"]) for m in fixtures]

    db = SessionLocal()
    try:
        # --- Tournament -----------------------------------------------------
        tournament = db.query(Tournament).filter(Tournament.name == tournament_name).first()
        if not tournament:
            tournament = Tournament(
                name=tournament_name,
                start_date=min(kickoffs).date(),
                end_date=max(kickoffs).date(),
                sport="football",
                picks_window="open",
            )
            db.add(tournament)
            db.flush()
            print(f"Created tournament '{tournament_name}' (id={tournament.id}, sport=football)")
        else:
            if tournament.sport != "football":
                print(f"ERROR: tournament '{tournament_name}' exists with sport={tournament.sport!r}")
                sys.exit(1)
            print(f"Tournament '{tournament_name}' already exists (id={tournament.id})")

        # --- Teams (find-or-create by name) ---------------------------------
        team_names = sorted({m["home_team"] for m in fixtures} | {m["away_team"] for m in fixtures})
        team_id: dict[str, int] = {}
        created_teams = 0
        for name in team_names:
            team = db.query(Team).filter(Team.name == name, Team.sport == "football").first()
            if not team:
                team = Team(name=name, short_name=short_name_for(name), sport="football")
                db.add(team)
                db.flush()
                created_teams += 1
            team_id[name] = team.id
        print(f"Teams: {len(team_names)} referenced, {created_teams} newly created")

        # --- Matches (skip dupes) -------------------------------------------
        existing = db.query(Match).filter(Match.tournament_id == tournament.id).all()
        existing_keys = {(m.team_1_id, m.team_2_id, naive_utc(m.start_time)) for m in existing}

        inserted = skipped = 0
        for m in fixtures:
            t1 = team_id[m["home_team"]]
            t2 = team_id[m["away_team"]]
            start = parse_kickoff(m["kickoff_utc"])
            # Fail loudly on an unrecognised stage rather than silently defaulting
            # to GROUP — a mislabeled knockout would lose its ×2 multiplier and
            # advance-winner scoring. Empty label = group (the source omits it).
            raw_stage = (m.get("stage") or "").strip()
            if raw_stage in STAGE_MAP:
                stage = STAGE_MAP[raw_stage]
            elif raw_stage in ("", "Group Stage"):
                stage = "GROUP"
            else:
                raise ValueError(
                    f"Unrecognised stage {raw_stage!r} for "
                    f"{m['home_team']} v {m['away_team']}: add it to STAGE_MAP. "
                    f"Knockout matches must map into {sorted(KNOCKOUT_STAGES)}."
                )
            if (t1, t2, start) in existing_keys:
                skipped += 1
                continue
            db.add(Match(
                tournament_id=tournament.id,
                team_1_id=t1,
                team_2_id=t2,
                start_time=start,
                status=MatchStatus.SCHEDULED,
                stage=stage,
            ))
            inserted += 1

        db.commit()
        print(f"Matches: inserted {inserted}, skipped {skipped} already present")
        print(f"Window: {min(kickoffs).date()} → {max(kickoffs).date()}")
        print("NOTE: squads/players not seeded — player picks need a separate seed.")
    finally:
        db.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JSON
    if not os.path.exists(path):
        print(f"JSON file not found: {path}")
        sys.exit(1)
    print(f"Seeding from {path}")
    run(path)
