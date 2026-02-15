"""
Re-seed players from t20wc-squads.json and fix match result references.
1. Delete all existing players
2. Insert correct squads from JSON
3. Re-map match results to new player IDs
"""
import json
from app.database import SessionLocal
from app.models import Match, Team, Player, Prediction, MatchStatus

db = SessionLocal()

# -- Step 1: Clear match result player references (so FK constraints don't block delete)
print("=== Step 1: Clearing match result player references ===")
matches_with_results = db.query(Match).filter(Match.result_pom_player_id.isnot(None)).all()
for m in matches_with_results:
    m.result_pom_player_id = None
    m.result_most_runs_player_id = None
    m.result_most_wickets_player_id = None
db.flush()
print(f"  Cleared player refs from {len(matches_with_results)} matches")

# Clear any prediction player references
preds = db.query(Prediction).all()
for p in preds:
    p.predicted_most_runs_player_id = None
    p.predicted_most_wickets_player_id = None
    p.predicted_pom_player_id = None
db.flush()
print(f"  Cleared player refs from {len(preds)} predictions")

# -- Step 2: Delete all existing players
print("\n=== Step 2: Deleting all existing players ===")
count = db.query(Player).delete()
db.flush()
print(f"  Deleted {count} players")

# -- Step 3: Load squads from JSON and insert
print("\n=== Step 3: Inserting players from t20wc-squads.json ===")
with open("t20wc-squads.json") as f:
    squads = json.load(f)

# Team name -> short_name mapping
TEAM_SHORT = {
    "India": "IND", "Pakistan": "PAK", "Afghanistan": "AFG", "Australia": "AUS",
    "England": "ENG", "South Africa": "SA", "New Zealand": "NZ", "West Indies": "WI",
    "Sri Lanka": "SL", "USA": "USA", "Ireland": "IRE", "Scotland": "SCO",
    "Netherlands": "NED", "Nepal": "NEP", "Italy": "ITA", "Zimbabwe": "ZIM",
    "Namibia": "NAM", "Oman": "OMA", "Canada": "CAN", "UAE": "UAE",
}

# Role normalization
def normalize_role(role_str):
    r = role_str.lower()
    if "captain" in r and "wicketkeeper" in r:
        return "Wicketkeeper"
    if "captain" in r:
        return "All-Rounder"
    if "wicketkeeper" in r:
        return "Wicketkeeper"
    if "all-rounder" in r or "all rounder" in r:
        return "All-Rounder"
    if "bowl" in r:
        return "Bowler"
    if "bat" in r:
        return "Batsman"
    return "All-Rounder"

total_players = 0
team_player_map = {}  # team_short -> {player_name: player_id}

for squad in squads:
    team_name = squad["team"]
    short = TEAM_SHORT[team_name]
    team = db.query(Team).filter(Team.short_name == short).first()
    assert team, f"Team not found: {short}"

    team_player_map[short] = {}
    for p_data in squad["players"]:
        role = normalize_role(p_data["role"])
        player = Player(name=p_data["name"], team_id=team.id, role=role)
        db.add(player)
        db.flush()
        team_player_map[short][p_data["name"]] = player.id
        total_players += 1

    print(f"  {short}: {len(squad['players'])} players")

print(f"  Total: {total_players} players inserted")

# -- Step 4: Re-apply match results with correct player IDs
print("\n=== Step 4: Re-applying match results ===")

def get_player_id(name, team_short):
    """Look up player by name and team."""
    players = team_player_map.get(team_short, {})
    if name in players:
        return players[name]
    # Try partial match
    for pname, pid in players.items():
        if name in pname or pname in name:
            print(f"    Fuzzy match: '{name}' -> '{pname}' (id={pid})")
            return pid
    raise ValueError(f"Player not found: {name} in {team_short}. Available: {list(players.keys())}")

def get_team_id(short):
    t = db.query(Team).filter(Team.short_name == short).first()
    return t.id

# Match results data: (match_id, winner, pom_name, pom_team, runs_name, runs_team, wkts_name, wkts_team)
results = [
    # Feb 7
    (22, "PAK", "Faheem Ashraf", "PAK", "Babar Azam", "PAK", "Shaheen Shah Afridi", "PAK"),
    (23, "WI", "Shimron Hetmyer", "WI", "Shimron Hetmyer", "WI", "Romario Shepherd", "WI"),
    (24, "IND", "Suryakumar Yadav", "IND", "Suryakumar Yadav", "IND", "Arshdeep Singh", "IND"),
    # Feb 8
    (25, "NZ", "Tim Seifert", "NZ", "Tim Seifert", "NZ", "Matt Henry", "NZ"),
    (26, "ENG", "Will Jacks", "ENG", "Harry Brook", "ENG", "Sam Curran", "ENG"),
    (27, "SL", "Kamindu Mendis", "SL", "Kamindu Mendis", "SL", "Wanindu Hasaranga", "SL"),
    # Feb 9
    (28, "SCO", "Michael Leask", "SCO", "George Munsey", "SCO", "Michael Leask", "SCO"),
    (29, "ZIM", "Blessing Muzarabani", "ZIM", "Brian Bennett", "ZIM", "Blessing Muzarabani", "ZIM"),
    (30, "SA", "Lungi Ngidi", "SA", "Navneet Dhaliwal", "CAN", "Lungi Ngidi", "SA"),
    # Feb 10
    (31, "NED", "Bas de Leede", "NED", "Bas de Leede", "NED", "Bas de Leede", "NED"),
    (32, "NZ", "Tim Seifert", "NZ", "Tim Seifert", "NZ", "Matt Henry", "NZ"),
    (33, "PAK", "Sahibzada Farhan", "PAK", "Sahibzada Farhan", "PAK", "Shadley van Schalkwyk", "USA"),
    # Feb 11
    (34, "SA", "Lungi Ngidi", "SA", "Rahmanullah Gurbaz", "AFG", "Lungi Ngidi", "SA"),
    (35, "AUS", "Nathan Ellis", "AUS", "Marcus Stoinis", "AUS", "Nathan Ellis", "AUS"),
    (36, "WI", "Sherfane Rutherford", "WI", "Sherfane Rutherford", "WI", "Alzarri Joseph", "WI"),
    # Feb 12
    (37, "SL", "Pavan Rathnayake", "SL", "Kamindu Mendis", "SL", "Wanindu Hasaranga", "SL"),
    (38, "ITA", "Crishan Jorge Kalugamage", "ITA", "Crishan Jorge Kalugamage", "ITA", "Crishan Jorge Kalugamage", "ITA"),
    (39, "IND", "Hardik Pandya", "IND", "Ishan Kishan", "IND", "Varun Chakaravarthy", "IND"),
    # Feb 13
    (40, "ZIM", "Blessing Muzarabani", "ZIM", "Matthew Renshaw", "AUS", "Blessing Muzarabani", "ZIM"),
    (41, "UAE", "Junaid Siddique", "UAE", "Aryansh Sharma", "UAE", "Junaid Siddique", "UAE"),
    (42, "USA", "Harmeet Singh", "USA", "Saiteja Mukkamalla", "USA", "Harmeet Singh", "USA"),
    # Feb 14
    (43, "IRE", "Lorcan Tucker", "IRE", "Lorcan Tucker", "IRE", "Josh Little", "IRE"),
    (44, "ENG", "Tom Banton", "ENG", "Tom Banton", "ENG", "Jofra Archer", "ENG"),
    (45, "SA", "Marco Jansen", "SA", "Aiden Markram", "SA", "Marco Jansen", "SA"),
]

for match_id, winner, pom_name, pom_team, runs_name, runs_team, wkts_name, wkts_team in results:
    match = db.get(Match, match_id)
    t1 = db.get(Team, match.team_1_id)
    t2 = db.get(Team, match.team_2_id)

    match.status = MatchStatus.COMPLETED
    match.result_winner_id = get_team_id(winner)
    match.result_pom_player_id = get_player_id(pom_name, pom_team)
    match.result_most_runs_player_id = get_player_id(runs_name, runs_team)
    match.result_most_wickets_player_id = get_player_id(wkts_name, wkts_team)

    print(f"  Match {match_id}: {t1.short_name} vs {t2.short_name} -> W:{winner}, POM:{pom_name}")

db.commit()
print(f"\n=== Done! {total_players} players seeded, {len(results)} match results applied ===")
db.close()
