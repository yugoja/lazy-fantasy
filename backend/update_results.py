"""
Update match results for T20 World Cup 2026 matches (Feb 7-14).
Adds missing players and sets winners, POM, top scorer, top wicket-taker.
"""
from app.database import SessionLocal
from app.models import Match, Team, Player, MatchStatus

db = SessionLocal()

# Helper to get team by short_name
def get_team(short_name: str) -> Team:
    t = db.query(Team).filter(Team.short_name == short_name).first()
    assert t, f"Team not found: {short_name}"
    return t

# Helper to get or create player
def get_or_create_player(name: str, team_short_name: str, role: str = "All-Rounder") -> Player:
    team = get_team(team_short_name)
    p = db.query(Player).filter(Player.name == name, Player.team_id == team.id).first()
    if not p:
        p = Player(name=name, team_id=team.id, role=role)
        db.add(p)
        db.flush()
        print(f"  Created player: {name} (id={p.id}, team={team_short_name})")
    return p

# Helper to update a match
def update_match(match_id: int, winner_short: str, pom_name: str, pom_team: str,
                 most_runs_name: str, most_runs_team: str,
                 most_wkts_name: str, most_wkts_team: str):
    match = db.query(Match).get(match_id)
    assert match, f"Match not found: {match_id}"

    winner = get_team(winner_short)
    pom = get_or_create_player(pom_name, pom_team)
    top_runs = get_or_create_player(most_runs_name, most_runs_team)
    top_wkts = get_or_create_player(most_wkts_name, most_wkts_team)

    match.status = MatchStatus.COMPLETED
    match.result_winner_id = winner.id
    match.result_pom_player_id = pom.id
    match.result_most_runs_player_id = top_runs.id
    match.result_most_wickets_player_id = top_wkts.id

    t1 = db.get(Team, match.team_1_id)
    t2 = db.get(Team, match.team_2_id)
    print(f"Match {match_id}: {t1.short_name} vs {t2.short_name} -> Winner: {winner_short}, POM: {pom_name}")


print("=== Updating T20 WC 2026 Match Results (Feb 7-14) ===\n")

# Feb 7 - Match 22: PAK vs NED -> PAK won by 3 wkts
update_match(22, "PAK",
    pom_name="Faheem Ashraf", pom_team="PAK",
    most_runs_name="Babar Azam", most_runs_team="PAK",
    most_wkts_name="Shaheen Afridi", most_wkts_team="PAK")

# Feb 7 - Match 23: WI vs SCO -> WI won by 35 runs
update_match(23, "WI",
    pom_name="Shimron Hetmyer", pom_team="WI",
    most_runs_name="Shimron Hetmyer", most_runs_team="WI",
    most_wkts_name="Romario Shepherd", most_wkts_team="WI")

# Feb 7 - Match 24: IND vs USA -> IND won by 29 runs
update_match(24, "IND",
    pom_name="Suryakumar Yadav", pom_team="IND",
    most_runs_name="Suryakumar Yadav", most_runs_team="IND",
    most_wkts_name="Arshdeep Singh", most_wkts_team="IND")

# Feb 8 - Match 25: NZ vs AFG -> NZ won by 5 wkts
update_match(25, "NZ",
    pom_name="Tim Seifert", pom_team="NZ",
    most_runs_name="Tim Seifert", most_runs_team="NZ",
    most_wkts_name="Trent Boult", most_wkts_team="NZ")

# Feb 8 - Match 26: ENG vs NEP -> ENG won by 4 runs
update_match(26, "ENG",
    pom_name="Will Jacks", pom_team="ENG",
    most_runs_name="Harry Brook", most_runs_team="ENG",
    most_wkts_name="Sam Curran", most_wkts_team="ENG")

# Feb 8 - Match 27: SL vs IRE -> SL won by 20 runs
update_match(27, "SL",
    pom_name="Kamindu Mendis", pom_team="SL",
    most_runs_name="Kamindu Mendis", most_runs_team="SL",
    most_wkts_name="Wanindu Hasaranga", most_wkts_team="SL")

# Feb 9 - Match 28: SCO vs ITA -> SCO won by 73 runs
update_match(28, "SCO",
    pom_name="Michael Leask", pom_team="SCO",
    most_runs_name="George Munsey", most_runs_team="SCO",
    most_wkts_name="Michael Leask", most_wkts_team="SCO")

# Feb 9 - Match 29: ZIM vs OMA -> ZIM won by 8 wkts
update_match(29, "ZIM",
    pom_name="Blessing Muzarabani", pom_team="ZIM",
    most_runs_name="Brian Bennett", most_runs_team="ZIM",
    most_wkts_name="Blessing Muzarabani", most_wkts_team="ZIM")

# Feb 9 - Match 30: SA vs CAN -> SA won by 57 runs
update_match(30, "SA",
    pom_name="Lungi Ngidi", pom_team="SA",
    most_runs_name="Navneet Dhaliwal", most_runs_team="CAN",
    most_wkts_name="Lungi Ngidi", most_wkts_team="SA")

# Feb 10 - Match 31: NED vs NAM -> NED won by 7 wkts
update_match(31, "NED",
    pom_name="Bas de Leede", pom_team="NED",
    most_runs_name="Bas de Leede", most_runs_team="NED",
    most_wkts_name="Bas de Leede", most_wkts_team="NED")

# Feb 10 - Match 32: NZ vs UAE -> NZ won by 10 wkts
update_match(32, "NZ",
    pom_name="Tim Seifert", pom_team="NZ",
    most_runs_name="Tim Seifert", most_runs_team="NZ",
    most_wkts_name="Trent Boult", most_wkts_team="NZ")

# Feb 10 - Match 33: PAK vs USA -> PAK won by 32 runs
update_match(33, "PAK",
    pom_name="Sahibzada Farhan", pom_team="PAK",
    most_runs_name="Sahibzada Farhan", most_runs_team="PAK",
    most_wkts_name="Shadley van Schalkwyk", most_wkts_team="USA")

# Feb 11 - Match 34: SA vs AFG -> SA won (double super over)
update_match(34, "SA",
    pom_name="Lungi Ngidi", pom_team="SA",
    most_runs_name="Rahmanullah Gurbaz", most_runs_team="AFG",
    most_wkts_name="Lungi Ngidi", most_wkts_team="SA")

# Feb 11 - Match 35: AUS vs IRE -> AUS won by 67 runs
update_match(35, "AUS",
    pom_name="Nathan Ellis", pom_team="AUS",
    most_runs_name="Marcus Stoinis", most_runs_team="AUS",
    most_wkts_name="Nathan Ellis", most_wkts_team="AUS")

# Feb 11 - Match 36: ENG vs WI -> WI won by 30 runs
update_match(36, "WI",
    pom_name="Sherfane Rutherford", pom_team="WI",
    most_runs_name="Sherfane Rutherford", most_runs_team="WI",
    most_wkts_name="Alzarri Joseph", most_wkts_team="WI")

# Feb 12 - Match 37: SL vs OMA -> SL won by 105 runs
update_match(37, "SL",
    pom_name="Pavan Rathnayake", pom_team="SL",
    most_runs_name="Kamindu Mendis", most_runs_team="SL",
    most_wkts_name="Wanindu Hasaranga", most_wkts_team="SL")

# Feb 12 - Match 38: NEP vs ITA -> ITA won by 10 wkts (historic!)
update_match(38, "ITA",
    pom_name="Crishan Kalugamage", pom_team="ITA",
    most_runs_name="Crishan Kalugamage", most_runs_team="ITA",
    most_wkts_name="Crishan Kalugamage", most_wkts_team="ITA")

# Feb 12 - Match 39: IND vs NAM -> IND won by 93 runs
update_match(39, "IND",
    pom_name="Hardik Pandya", pom_team="IND",
    most_runs_name="Ishan Kishan", most_runs_team="IND",
    most_wkts_name="Varun Chakravarthy", most_wkts_team="IND")

# Feb 13 - Match 40: AUS vs ZIM -> ZIM won by 23 runs (upset!)
update_match(40, "ZIM",
    pom_name="Blessing Muzarabani", pom_team="ZIM",
    most_runs_name="Matt Renshaw", most_runs_team="AUS",
    most_wkts_name="Blessing Muzarabani", most_wkts_team="ZIM")

# Feb 13 - Match 41: CAN vs UAE -> UAE won by 5 wkts
update_match(41, "UAE",
    pom_name="Junaid Siddique", pom_team="UAE",
    most_runs_name="Aryansh Sharma", most_runs_team="UAE",
    most_wkts_name="Junaid Siddique", most_wkts_team="UAE")

# Feb 13 - Match 42: USA vs NED -> USA won by 93 runs
update_match(42, "USA",
    pom_name="Harmeet Singh", pom_team="USA",
    most_runs_name="Saiteja Mukkamalla", most_runs_team="USA",
    most_wkts_name="Harmeet Singh", most_wkts_team="USA")

# Feb 14 - Match 43: IRE vs OMA -> IRE won by 96 runs
update_match(43, "IRE",
    pom_name="Lorcan Tucker", pom_team="IRE",
    most_runs_name="Lorcan Tucker", most_runs_team="IRE",
    most_wkts_name="Josh Little", most_wkts_team="IRE")

# Feb 14 - Match 44: ENG vs SCO -> ENG won by 5 wkts
update_match(44, "ENG",
    pom_name="Tom Banton", pom_team="ENG",
    most_runs_name="Tom Banton", most_runs_team="ENG",
    most_wkts_name="Jofra Archer", most_wkts_team="ENG")

# Feb 14 - Match 45: NZ vs SA -> SA won by 7 wkts
update_match(45, "SA",
    pom_name="Marco Jansen", pom_team="SA",
    most_runs_name="Aiden Markram", most_runs_team="SA",
    most_wkts_name="Marco Jansen", most_wkts_team="SA")

db.commit()
print(f"\n=== Successfully updated all 24 matches! ===")
db.close()
