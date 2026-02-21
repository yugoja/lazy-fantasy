"""
Seed script for ICC Men's T20 World Cup 2026 data.
Reads fixtures from seed_t20wc.json, creates tournament, teams, players, and group-stage + Super Eight matches.
Knockout matches are skipped (teams TBD).
"""
import sys
import json
sys.path.insert(0, '.')

from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models import Tournament, Team, Player, Match, MatchStatus

IST = timezone(timedelta(hours=5, minutes=30))

# Time parsing: "11:00 AM" IST -> UTC
TIME_MAP = {
    "11:00 AM": "05:30:00",   # 11:00 AM IST = 05:30 UTC
    "03:00 PM": "09:30:00",   # 3:00 PM IST = 09:30 UTC
    "07:00 PM": "13:30:00",   # 7:00 PM IST = 13:30 UTC
}

# 20 teams with short names
TEAM_SHORT_NAMES = {
    "India": "IND",
    "Pakistan": "PAK",
    "Netherlands": "NED",
    "Namibia": "NAM",
    "USA": "USA",
    "West Indies": "WI",
    "Scotland": "SCO",
    "England": "ENG",
    "Nepal": "NEP",
    "Italy": "ITA",
    "Sri Lanka": "SL",
    "Ireland": "IRE",
    "Zimbabwe": "ZIM",
    "Oman": "OMA",
    "Australia": "AUS",
    "South Africa": "SA",
    "Canada": "CAN",
    "New Zealand": "NZ",
    "Afghanistan": "AFG",
    "UAE": "UAE",
}

# Confirmed T20 WC 2026 squads (15 players each)
SQUADS = {
    "India": [
        ("Suryakumar Yadav", "Batsman"), ("Abhishek Sharma", "Batsman"), ("Tilak Varma", "Batsman"),
        ("Sanju Samson", "Wicketkeeper"), ("Shivam Dube", "All-Rounder"), ("Ishan Kishan", "Wicketkeeper"),
        ("Hardik Pandya", "All-Rounder"), ("Arshdeep Singh", "Bowler"), ("Jasprit Bumrah", "Bowler"),
        ("Mohammed Siraj", "Bowler"), ("Varun Chakaravarthy", "Bowler"), ("Kuldeep Yadav", "Bowler"),
        ("Axar Patel", "All-Rounder"), ("Washington Sundar", "All-Rounder"), ("Rinku Singh", "Batsman"),
    ],
    "Pakistan": [
        ("Salman Ali Agha", "All-Rounder"), ("Babar Azam", "Batsman"), ("Shaheen Shah Afridi", "Bowler"),
        ("Naseem Shah", "Bowler"), ("Shadab Khan", "All-Rounder"), ("Fakhar Zaman", "Batsman"),
        ("Saim Ayub", "Batsman"), ("Mohammad Nawaz", "All-Rounder"), ("Abrar Ahmed", "Bowler"),
        ("Sahibzada Farhan", "Wicketkeeper"), ("Usman Khan", "Wicketkeeper"), ("Faheem Ashraf", "All-Rounder"),
        ("Khawaja Nafay", "Batsman"), ("Usman Tariq", "Bowler"), ("Mohammad Salman Mirza", "Bowler"),
    ],
    "Australia": [
        ("Mitchell Marsh", "All-Rounder"), ("Travis Head", "Batsman"), ("Glenn Maxwell", "All-Rounder"),
        ("Marcus Stoinis", "All-Rounder"), ("Tim David", "Batsman"), ("Josh Inglis", "Wicketkeeper"),
        ("Cameron Green", "All-Rounder"), ("Adam Zampa", "Bowler"), ("Josh Hazlewood", "Bowler"),
        ("Nathan Ellis", "Bowler"), ("Xavier Bartlett", "Bowler"), ("Cooper Connolly", "Batsman"),
        ("Ben Dwarshuis", "Bowler"), ("Matthew Kuhnemann", "Bowler"), ("Matthew Renshaw", "Batsman"),
    ],
    "England": [
        ("Harry Brook", "Batsman"), ("Jos Buttler", "Wicketkeeper"), ("Phil Salt", "Wicketkeeper"),
        ("Will Jacks", "All-Rounder"), ("Sam Curran", "All-Rounder"), ("Jofra Archer", "Bowler"),
        ("Adil Rashid", "Bowler"), ("Rehan Ahmed", "Bowler"), ("Liam Dawson", "All-Rounder"),
        ("Ben Duckett", "Batsman"), ("Tom Banton", "Wicketkeeper"), ("Jacob Bethell", "All-Rounder"),
        ("Jamie Overton", "All-Rounder"), ("Josh Tongue", "Bowler"), ("Luke Wood", "Bowler"),
    ],
    "South Africa": [
        ("Aiden Markram", "Batsman"), ("Quinton de Kock", "Wicketkeeper"), ("David Miller", "Batsman"),
        ("Tristan Stubbs", "Batsman"), ("Heinrich Klaasen", "Wicketkeeper"), ("Marco Jansen", "All-Rounder"),
        ("Kagiso Rabada", "Bowler"), ("Anrich Nortje", "Bowler"), ("Keshav Maharaj", "Bowler"),
        ("Dewald Brevis", "Batsman"), ("Kwena Maphaka", "Bowler"), ("Lungi Ngidi", "Bowler"),
        ("Ryan Rickelton", "Wicketkeeper"), ("George Linde", "All-Rounder"), ("Corbin Bosch", "All-Rounder"),
    ],
    "New Zealand": [
        ("Mitchell Santner", "All-Rounder"), ("Finn Allen", "Batsman"), ("Devon Conway", "Wicketkeeper"),
        ("Rachin Ravindra", "All-Rounder"), ("Daryl Mitchell", "All-Rounder"), ("Glenn Phillips", "Batsman"),
        ("Mark Chapman", "Batsman"), ("James Neesham", "All-Rounder"), ("Tim Seifert", "Wicketkeeper"),
        ("Lockie Ferguson", "Bowler"), ("Matt Henry", "Bowler"), ("Ish Sodhi", "Bowler"),
        ("Kyle Jamieson", "Bowler"), ("Jacob Duffy", "Bowler"), ("Michael Bracewell", "All-Rounder"),
    ],
    "West Indies": [
        ("Shai Hope", "Wicketkeeper"), ("Rovman Powell", "Batsman"), ("Brandon King", "Batsman"),
        ("Nicholas Pooran", "Wicketkeeper"), ("Andre Russell", "All-Rounder"), ("Shimron Hetmyer", "Batsman"),
        ("Sherfane Rutherford", "Batsman"), ("Jason Holder", "All-Rounder"), ("Romario Shepherd", "All-Rounder"),
        ("Akeal Hosein", "Bowler"), ("Gudakesh Motie", "Bowler"), ("Alzarri Joseph", "Bowler"),
        ("Shamar Joseph", "Bowler"), ("Johnson Charles", "Batsman"), ("Matthew Forde", "All-Rounder"),
    ],
    "Sri Lanka": [
        ("Dasun Shanaka", "All-Rounder"), ("Pathum Nissanka", "Batsman"), ("Kusal Mendis", "Wicketkeeper"),
        ("Charith Asalanka", "Batsman"), ("Wanindu Hasaranga", "All-Rounder"), ("Maheesh Theekshana", "Bowler"),
        ("Matheesha Pathirana", "Bowler"), ("Dunith Wellalage", "All-Rounder"), ("Kamindu Mendis", "All-Rounder"),
        ("Kusal Perera", "Wicketkeeper"), ("Dushmantha Chameera", "Bowler"), ("Janith Liyanage", "All-Rounder"),
        ("Pavan Rathnayake", "Batsman"), ("Dushan Hemantha", "Bowler"), ("Pramod Madushan", "Bowler"),
    ],
    "Afghanistan": [
        ("Rashid Khan", "All-Rounder"), ("Rahmanullah Gurbaz", "Wicketkeeper"), ("Ibrahim Zadran", "Batsman"),
        ("Mohammad Nabi", "All-Rounder"), ("Azmatullah Omarzai", "All-Rounder"), ("Gulbadin Naib", "All-Rounder"),
        ("Fazalhaq Farooqi", "Bowler"), ("Mujeeb Ur Rahman", "Bowler"), ("Noor Ahmad", "Bowler"),
        ("Naveen-ul-Haq", "Bowler"), ("Sediqullah Atal", "Batsman"), ("Darwish Rasooli", "Batsman"),
        ("Shahidullah Kamal", "All-Rounder"), ("Mohammad Ishaq", "Wicketkeeper"), ("Zia-ur-Rehman Sharifi", "Bowler"),
    ],
    "Netherlands": [
        ("Scott Edwards", "Wicketkeeper"), ("Bas de Leede", "All-Rounder"), ("Logan van Beek", "Bowler"),
        ("Max O'Dowd", "Batsman"), ("Roelof van der Merwe", "All-Rounder"), ("Colin Ackermann", "All-Rounder"),
        ("Paul van Meekeren", "Bowler"), ("Fred Klaassen", "Bowler"), ("Aryan Dutt", "Bowler"),
        ("Michael Levitt", "Batsman"), ("Vikramjit Singh", "Batsman"), ("Timm van der Gugten", "Bowler"),
        ("Noah Croes", "Wicketkeeper"), ("Kyle Klein", "Bowler"), ("Saqib Zulfiqar", "All-Rounder"),
    ],
    "Scotland": [
        ("Richie Berrington", "All-Rounder"), ("George Munsey", "Batsman"), ("Brandon McMullen", "Batsman"),
        ("Michael Leask", "All-Rounder"), ("Mark Watt", "Bowler"), ("Bradley Wheal", "Bowler"),
        ("Chris Greaves", "All-Rounder"), ("Safyaan Sharif", "Bowler"), ("Matthew Cross", "Wicketkeeper"),
        ("Bradley Currie", "Bowler"), ("Michael Jones", "Batsman"), ("Tom Bruce", "Batsman"),
        ("Oliver Davidson", "All-Rounder"), ("Finlay McCreath", "Batsman"), ("Zainullah Ihsan", "Bowler"),
    ],
    "Ireland": [
        ("Lorcan Tucker", "Wicketkeeper"), ("Mark Adair", "Bowler"), ("Harry Tector", "Batsman"),
        ("Josh Little", "Bowler"), ("Curtis Campher", "All-Rounder"), ("George Dockrell", "All-Rounder"),
        ("Paul Stirling", "Batsman"), ("Ross Adair", "Batsman"), ("Barry McCarthy", "Bowler"),
        ("Craig Young", "Bowler"), ("Gareth Delany", "All-Rounder"), ("Ben White", "Bowler"),
        ("Tim Tector", "Batsman"), ("Matthew Humphreys", "Bowler"), ("Sam Topping", "Wicketkeeper"),
    ],
    "Zimbabwe": [
        ("Sikandar Raza", "All-Rounder"), ("Blessing Muzarabani", "Bowler"), ("Richard Ngarava", "Bowler"),
        ("Ryan Burl", "All-Rounder"), ("Brian Bennett", "Batsman"), ("Clive Madande", "Wicketkeeper"),
        ("Tadiwanashe Marumani", "Wicketkeeper"), ("Wellington Masakadza", "Bowler"), ("Brad Evans", "All-Rounder"),
        ("Dion Myers", "Batsman"), ("Graeme Cremer", "Bowler"), ("Tony Munyonga", "Batsman"),
        ("Tinotenda Maposa", "Bowler"), ("Tashinga Musekiwa", "All-Rounder"), ("Ben Curran", "Batsman"),
    ],
    "Namibia": [
        ("Gerhard Erasmus", "All-Rounder"), ("JJ Smit", "All-Rounder"), ("Jan Frylinck", "All-Rounder"),
        ("Bernard Scholtz", "Bowler"), ("Ruben Trumpelmann", "Bowler"), ("Zane Green", "Wicketkeeper"),
        ("Nicol Loftie-Eaton", "All-Rounder"), ("Ben Shikongo", "Bowler"), ("Louren Steenkamp", "Batsman"),
        ("Malan Kruger", "Batsman"), ("Jack Brassell", "Bowler"), ("Jan Balt", "Batsman"),
        ("Dylan Leicher", "All-Rounder"), ("Willem Myburgh", "Batsman"), ("Max Heingo", "Bowler"),
    ],
    "USA": [
        ("Monank Patel", "Wicketkeeper"), ("Saurabh Netravalkar", "Bowler"), ("Andries Gous", "Wicketkeeper"),
        ("Harmeet Singh", "All-Rounder"), ("Ali Khan", "Bowler"), ("Shayan Jahangir", "Wicketkeeper"),
        ("Milind Kumar", "Batsman"), ("Shehan Jayasuriya", "Batsman"), ("Nosthush Kenjige", "Bowler"),
        ("Shadley van Schalkwyk", "All-Rounder"), ("Mohammad Mohsin", "Bowler"), ("Saiteja Mukkamalla", "Batsman"),
        ("Sanjay Krishnamurthi", "All-Rounder"), ("Shubham Ranjane", "All-Rounder"), ("Ehsan Adil", "Bowler"),
    ],
    "Nepal": [
        ("Rohit Paudel", "Batsman"), ("Kushal Bhurtel", "Batsman"), ("Aasif Sheikh", "Wicketkeeper"),
        ("Dipendra Singh Airee", "All-Rounder"), ("Sandeep Lamichhane", "Bowler"), ("Kushal Malla", "All-Rounder"),
        ("Sompal Kami", "Bowler"), ("Karan KC", "Bowler"), ("Gulshan Jha", "All-Rounder"),
        ("Lalit Rajbanshi", "Bowler"), ("Sundeep Jora", "Batsman"), ("Aarif Sheikh", "Batsman"),
        ("Basir Ahamad", "All-Rounder"), ("Nandan Yadav", "Bowler"), ("Sher Malla", "Bowler"),
    ],
    "Oman": [
        ("Jatinder Singh", "Batsman"), ("Zeeshan Maqsood", "All-Rounder"), ("Aqib Ilyas", "Batsman"),
        ("Aamir Kaleem", "All-Rounder"), ("Vinayak Shukla", "Wicketkeeper"), ("Mohammad Nadeem", "All-Rounder"),
        ("Sufyan Mehmood", "Bowler"), ("Shakeel Ahmad", "Bowler"), ("Hammad Mirza", "Batsman"),
        ("Wasim Ali", "All-Rounder"), ("Karan Sonavale", "Batsman"), ("Shah Faisal", "Bowler"),
        ("Jay Odedra", "Bowler"), ("Shafiq Jan", "Bowler"), ("Ashish Odedara", "Batsman"),
    ],
    "UAE": [
        ("Muhammad Waseem", "Batsman"), ("Alishan Sharafu", "Batsman"), ("Junaid Siddique", "Bowler"),
        ("Aryansh Sharma", "Wicketkeeper"), ("Dhruv Parashar", "All-Rounder"), ("Haider Ali", "Bowler"),
        ("Harshit Kaushik", "All-Rounder"), ("Mayank Kumar", "Bowler"), ("Muhammad Arfan", "Bowler"),
        ("Muhammad Farooq", "All-Rounder"), ("Muhammad Jawadullah", "Bowler"), ("Muhammad Zohaib", "Batsman"),
        ("Rohid Khan", "Bowler"), ("Sohaib Khan", "Batsman"), ("Simranjeet Singh", "Batsman"),
    ],
    "Canada": [
        ("Dilpreet Bajwa", "All-Rounder"), ("Navneet Dhaliwal", "Batsman"), ("Nicholas Kirton", "Batsman"),
        ("Saad Bin Zafar", "All-Rounder"), ("Kaleem Sana", "Bowler"), ("Dilon Heyliger", "Bowler"),
        ("Harsh Thaker", "All-Rounder"), ("Ravinderpal Singh", "Batsman"), ("Shreyas Movva", "Wicketkeeper"),
        ("Ajayveer Hundal", "Batsman"), ("Ansh Patel", "Bowler"), ("Jaskarandeep Buttar", "Bowler"),
        ("Kanwarpal Tathgur", "Batsman"), ("Shivam Sharma", "Bowler"), ("Yuvraj Samra", "Batsman"),
    ],
    "Italy": [
        ("Wayne Madsen", "Batsman"), ("JJ Smuts", "All-Rounder"), ("Harry Manenti", "All-Rounder"),
        ("Ben Manenti", "All-Rounder"), ("Grant Stewart", "Bowler"), ("Thomas Draca", "Bowler"),
        ("Marcus Campopiano", "Batsman"), ("Gian Piero Meade", "Batsman"), ("Zain Ali", "All-Rounder"),
        ("Ali Hasan", "Bowler"), ("Crishan Jorge Kalugamage", "All-Rounder"), ("Anthony Mosca", "Batsman"),
        ("Justin Mosca", "Batsman"), ("Syed Naqvi", "Wicketkeeper"), ("Jaspreet Singh", "Bowler"),
    ],
}


def seed_t20wc():
    db = SessionLocal()

    try:
        # Load fixtures JSON
        with open("seed_t20wc.json", "r") as f:
            fixtures = json.load(f)

        # Create Tournament
        print("Creating ICC Men's T20 World Cup 2026...")
        tournament = Tournament(
            name="ICC Men's T20 World Cup 2026",
            start_date=datetime(2026, 2, 7).date(),
            end_date=datetime(2026, 3, 8).date(),
        )
        db.add(tournament)
        db.commit()
        db.refresh(tournament)
        print(f"  Tournament ID: {tournament.id}")

        # Create Teams and Players
        print("\nCreating 20 teams and squads...")
        team_map = {}  # team_name -> team_id

        for team_name, short_name in TEAM_SHORT_NAMES.items():
            team = Team(name=team_name, short_name=short_name)
            db.add(team)
            db.commit()
            db.refresh(team)
            team_map[team_name] = team.id

            # Add players
            squad = SQUADS.get(team_name, [])
            for player_name, role in squad:
                player = Player(name=player_name, team_id=team.id, role=role)
                db.add(player)
            db.commit()
            print(f"  {short_name:>4} {team_name} — {len(squad)} players")

        # Create Group Stage + Super Eight Matches (skip Knockout — teams TBD)
        print("\nCreating group stage + Super Eight matches...")
        match_count = 0
        skipped = 0

        for fixture in fixtures:
            if fixture["group"] == "Knockout":
                skipped += 1
                continue

            teams_str = fixture["teams"]
            parts = teams_str.split(" vs ")
            if len(parts) != 2:
                print(f"  Skipping match {fixture['match_no']}: can't parse '{teams_str}'")
                skipped += 1
                continue

            team_1_name, team_2_name = parts[0].strip(), parts[1].strip()

            if team_1_name not in team_map or team_2_name not in team_map:
                print(f"  Skipping match {fixture['match_no']}: unknown team '{team_1_name}' or '{team_2_name}'")
                skipped += 1
                continue

            utc_time = TIME_MAP.get(fixture["time"], "13:30:00")
            start_time = datetime.fromisoformat(f"{fixture['date']}T{utc_time}+00:00")

            match = Match(
                tournament_id=tournament.id,
                team_1_id=team_map[team_1_name],
                team_2_id=team_map[team_2_name],
                start_time=start_time,
                status=MatchStatus.SCHEDULED,
            )
            db.add(match)
            match_count += 1
            print(f"  Match {fixture['match_no']:>2}: {team_1_name} vs {team_2_name} — {fixture['date']} {fixture['time']} ({fixture['venue']})")

        db.commit()

        print(f"\n{'='*50}")
        print(f"  Tournament : {tournament.name}")
        print(f"  Teams      : {len(TEAM_SHORT_NAMES)}")
        print(f"  Players    : {sum(len(s) for s in SQUADS.values())}")
        print(f"  Matches    : {match_count} seeded, {skipped} skipped (TBD)")
        print(f"{'='*50}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_t20wc()
