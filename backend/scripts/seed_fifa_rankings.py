"""
Seed FIFA rankings for World Cup 2026 teams.

Updates the fifa_ranking column on football teams. Matches by team name
(same key used by the fixtures seed). Safe to re-run — idempotent UPDATE.

Usage (from backend/, or in the compose backend container):
  python -m scripts.seed_fifa_rankings
"""
from app.db import SessionLocal
from app.models.team import Team

RANKINGS: dict[str, int] = {
    "France": 1,
    "Spain": 2,
    "Argentina": 3,
    "England": 4,
    "Portugal": 5,
    "Brazil": 6,
    "Netherlands": 7,
    "Morocco": 8,
    "Belgium": 9,
    "Germany": 10,
    "Croatia": 11,
    "Colombia": 13,
    "Senegal": 14,
    "Mexico": 15,
    "United States": 16,
    "Uruguay": 17,
    "Japan": 18,
    "Switzerland": 19,
    "Iran": 21,
    "Austria": 23,
    "Ecuador": 24,
    "South Korea": 25,
    "Australia": 26,
    "Egypt": 29,
    "Canada": 30,
    "Ivory Coast": 33,
    "Qatar": 35,
    "Algeria": 36,
    "Sweden": 39,
    "Tunisia": 40,
    "Czechia": 41,
    "Türkiye": 42,
    "Norway": 44,
    "Scotland": 47,
    "DR Congo": 51,
    "Bosnia & Herzegovina": 52,
    "Panama": 53,
    "Saudi Arabia": 57,
    "South Africa": 60,
    "Iraq": 61,
    "Uzbekistan": 62,
    "Paraguay": 64,
    "Ghana": 65,
    "Jordan": 68,
    "Cape Verde": 70,
    "Curaçao": 81,
    "Haiti": 83,
    "New Zealand": 95,
}


def main() -> None:
    db = SessionLocal()
    try:
        updated = 0
        for name, rank in RANKINGS.items():
            team = db.query(Team).filter(Team.name == name, Team.sport == "football").first()
            if team is None:
                print(f"  WARNING: no football team found for '{name}'")
                continue
            team.fifa_ranking = rank
            updated += 1
        db.commit()
        print(f"Done — updated {updated}/{len(RANKINGS)} teams.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
