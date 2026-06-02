"""
Seed FIFA World Cup 2026 squad lists from the official FIFA PDF
(extracted to /tmp/squads_raw.txt via `pdftotext SquadLists-English.pdf`).

Run:
  pdftotext /path/to/SquadLists-English.pdf /tmp/squads_raw.txt
  cd backend && source venv/bin/activate
  python scripts/seed_worldcup_squads.py [--dry-run]
"""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.team import Team
from app.models.player import Player

RAW_TEXT_PATH = "/tmp/squads_raw.txt"

# PDF country name → DB team name (as stored by seed_worldcup_fixtures.py)
PDF_TO_DB_NAME: dict[str, str] = {
    "Algeria": "Algeria",
    "Argentina": "Argentina",
    "Australia": "Australia",
    "Austria": "Austria",
    "Belgium": "Belgium",
    "Bosnia And Herzegovina": "Bosnia and Herzegovina",
    "Brazil": "Brazil",
    "Cabo Verde": "Cape Verde",
    "Canada": "Canada",
    "Colombia": "Colombia",
    "Congo DR": "Congo DR",
    "Côte D'Ivoire": "Ivory Coast",
    "Croatia": "Croatia",
    "Curaçao": "Curaçao",
    "Czechia": "Czech Republic",
    "Czech Republic": "Czech Republic",
    "Ecuador": "Ecuador",
    "Egypt": "Egypt",
    "England": "England",
    "France": "France",
    "Germany": "Germany",
    "Ghana": "Ghana",
    "Haiti": "Haiti",
    "IR Iran": "Iran",
    "Iraq": "Iraq",
    "Japan": "Japan",
    "Jordan": "Jordan",
    "Korea Republic": "South Korea",
    "Mexico": "Mexico",
    "Morocco": "Morocco",
    "Netherlands": "Netherlands",
    "New Zealand": "New Zealand",
    "Norway": "Norway",
    "Panama": "Panama",
    "Paraguay": "Paraguay",
    "Portugal": "Portugal",
    "Qatar": "Qatar",
    "Saudi Arabia": "Saudi Arabia",
    "Scotland": "Scotland",
    "Senegal": "Senegal",
    "South Africa": "South Africa",
    "Spain": "Spain",
    "Sweden": "Sweden",
    "Switzerland": "Switzerland",
    "Tunisia": "Tunisia",
    "Türkiye": "Türkiye",
    "Uruguay": "Uruguay",
    "USA": "United States",
    "Uzbekistan": "Uzbekistan",
}

POS_MAP = {
    "GK": "Goalkeeper",
    "DF": "Defender",
    "MF": "Midfielder",
    "FW": "Forward",
}

TEAM_HEADER_RE = re.compile(r"^(.+?)\s*\(([A-Z]{3})\)$")
POS_RE = re.compile(r"^(GK|DF|MF|FW)$")
DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
# Jersey numbers are 1–99; heights are 3-digit (150–220) — exclude those
NUMBER_RE = re.compile(r"^\d{1,2}$")


def parse_squads(raw_path: str) -> dict[str, list[dict]]:
    """Returns {pdf_team_name: [{jersey, pos, display_name}, ...]}"""
    with open(raw_path) as f:
        lines = [l.rstrip() for l in f.readlines()]

    # Locate national team section start lines
    sections: list[tuple[int, str, str]] = []  # (line_idx, pdf_name, tri_code)
    for i, line in enumerate(lines):
        m = TEAM_HEADER_RE.match(line)
        if m:
            name = m.group(1).strip()
            code = m.group(2)
            if name in PDF_TO_DB_NAME:
                sections.append((i, name, code))

    squads: dict[str, list[dict]] = {}

    for sec_idx, (start, pdf_name, tri_code) in enumerate(sections):
        end = sections[sec_idx + 1][0] if sec_idx + 1 < len(sections) else len(lines)
        section_lines = [l for l in lines[start + 1 : end] if l.strip()]

        players = []
        i = 0
        while i < len(section_lines):
            line = section_lines[i]

            # Skip page headers
            if line in ("#", "POS", "PLAYER NAME", "FIRST NAME(S)", "SURNAME",
                        "SHORTNAME", "DATE OF BIRTH", "CLUB", "HEIGHT",
                        "SQUAD LIST", "FIFA World Cup 2026™",
                        "11 June 2026 – 19 July 2026", pdf_name, tri_code):
                i += 1
                continue
            # Skip page break repetitions of team name with code
            m = TEAM_HEADER_RE.match(line)
            if m and m.group(1).strip() == pdf_name:
                i += 1
                continue

            # Jersey number starts a player block
            if NUMBER_RE.match(line):
                jersey = int(line)
                # Look for POS within the next few lines
                pos = None
                display_name = None
                j = i + 1
                while j < len(section_lines) and j < i + 5:
                    if POS_RE.match(section_lines[j]):
                        pos = section_lines[j]
                        # Next non-empty line is the display name (LAST First format)
                        if j + 1 < len(section_lines):
                            display_name = section_lines[j + 1]
                        break
                    j += 1

                if pos and display_name:
                    # Skip header artifacts that look like names
                    if display_name not in ("PLAYER NAME", "FIRST NAME(S)", "#", "POS"):
                        players.append({
                            "jersey": jersey,
                            "pos": pos,
                            "display_name": display_name,
                        })
                    i = j + 2
                    continue

            i += 1

        squads[pdf_name] = players

    return squads


def seed(dry_run: bool = False) -> None:
    squads = parse_squads(RAW_TEXT_PATH)

    db = SessionLocal()
    try:
        # Build team lookup: db_name → Team (football teams have sport="football")
        teams_by_name: dict[str, Team] = {
            t.name: t
            for t in db.query(Team).filter(Team.sport == "football").all()
        }
        if not teams_by_name:
            print("ERROR: No football teams found. Run seed_worldcup_fixtures.py first.")
            return

        total_created = total_skipped = 0
        missing_teams = []

        for pdf_name, players in sorted(squads.items()):
            db_name = PDF_TO_DB_NAME.get(pdf_name)
            team = teams_by_name.get(db_name) if db_name else None
            if not team:
                missing_teams.append(pdf_name)
                print(f"  SKIP (team not in DB): {pdf_name}")
                continue

            existing = {
                p.name: p
                for p in db.query(Player).filter(Player.team_id == team.id).all()
            }

            created = skipped = 0
            for p in players:
                if p["display_name"] in existing:
                    skipped += 1
                    continue
                if not dry_run:
                    player = Player(
                        name=p["display_name"],
                        role=POS_MAP[p["pos"]],
                        team_id=team.id,
                    )
                    db.add(player)
                created += 1

            print(
                f"  {'[DRY] ' if dry_run else ''}{pdf_name:30s} → {db_name}: "
                f"{created} new, {skipped} existing ({len(players)} total)"
            )
            total_created += created
            total_skipped += skipped

        if not dry_run:
            db.commit()

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Done: {total_created} players created, "
              f"{total_skipped} skipped.")
        if missing_teams:
            print(f"Teams not found in DB: {missing_teams}")

    finally:
        db.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    seed(dry_run=dry_run)
