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

# Representative T20I squads (15 players each)
SQUADS = {
    "India": [
        ("Rohit Sharma", "Batsman"), ("Virat Kohli", "Batsman"), ("Suryakumar Yadav", "Batsman"),
        ("Yashasvi Jaiswal", "Batsman"), ("Rishabh Pant", "Wicketkeeper"), ("Hardik Pandya", "All-Rounder"),
        ("Ravindra Jadeja", "All-Rounder"), ("Axar Patel", "All-Rounder"), ("Jasprit Bumrah", "Bowler"),
        ("Mohammed Siraj", "Bowler"), ("Arshdeep Singh", "Bowler"), ("Kuldeep Yadav", "Bowler"),
        ("Shivam Dube", "All-Rounder"), ("Sanju Samson", "Wicketkeeper"), ("Rinku Singh", "Batsman"),
    ],
    "Pakistan": [
        ("Babar Azam", "Batsman"), ("Mohammad Rizwan", "Wicketkeeper"), ("Fakhar Zaman", "Batsman"),
        ("Shaheen Afridi", "Bowler"), ("Naseem Shah", "Bowler"), ("Shadab Khan", "All-Rounder"),
        ("Iftikhar Ahmed", "All-Rounder"), ("Imad Wasim", "All-Rounder"), ("Haris Rauf", "Bowler"),
        ("Mohammad Nawaz", "All-Rounder"), ("Saim Ayub", "Batsman"), ("Abbas Afridi", "Bowler"),
        ("Azam Khan", "Wicketkeeper"), ("Usman Khan", "Batsman"), ("Abrar Ahmed", "Bowler"),
    ],
    "Australia": [
        ("Travis Head", "Batsman"), ("David Warner", "Batsman"), ("Mitchell Marsh", "All-Rounder"),
        ("Glenn Maxwell", "All-Rounder"), ("Marcus Stoinis", "All-Rounder"), ("Tim David", "Batsman"),
        ("Josh Inglis", "Wicketkeeper"), ("Pat Cummins", "Bowler"), ("Mitchell Starc", "Bowler"),
        ("Adam Zampa", "Bowler"), ("Josh Hazlewood", "Bowler"), ("Cameron Green", "All-Rounder"),
        ("Matthew Wade", "Wicketkeeper"), ("Steve Smith", "Batsman"), ("Nathan Ellis", "Bowler"),
    ],
    "England": [
        ("Jos Buttler", "Wicketkeeper"), ("Phil Salt", "Batsman"), ("Harry Brook", "Batsman"),
        ("Liam Livingstone", "All-Rounder"), ("Moeen Ali", "All-Rounder"), ("Sam Curran", "All-Rounder"),
        ("Jofra Archer", "Bowler"), ("Mark Wood", "Bowler"), ("Adil Rashid", "Bowler"),
        ("Chris Jordan", "Bowler"), ("Jonny Bairstow", "Batsman"), ("Ben Duckett", "Batsman"),
        ("Reece Topley", "Bowler"), ("Will Jacks", "All-Rounder"), ("Tom Hartley", "Bowler"),
    ],
    "South Africa": [
        ("Quinton de Kock", "Wicketkeeper"), ("Aiden Markram", "Batsman"), ("Heinrich Klaasen", "Wicketkeeper"),
        ("David Miller", "Batsman"), ("Tristan Stubbs", "Batsman"), ("Marco Jansen", "All-Rounder"),
        ("Keshav Maharaj", "Bowler"), ("Kagiso Rabada", "Bowler"), ("Anrich Nortje", "Bowler"),
        ("Tabraiz Shamsi", "Bowler"), ("Reeza Hendricks", "Batsman"), ("Rassie van der Dussen", "Batsman"),
        ("Gerald Coetzee", "Bowler"), ("Wiaan Mulder", "All-Rounder"), ("Ryan Rickelton", "Batsman"),
    ],
    "New Zealand": [
        ("Kane Williamson", "Batsman"), ("Devon Conway", "Batsman"), ("Daryl Mitchell", "All-Rounder"),
        ("Glenn Phillips", "Wicketkeeper"), ("Mark Chapman", "Batsman"), ("Mitchell Santner", "All-Rounder"),
        ("Rachin Ravindra", "All-Rounder"), ("Trent Boult", "Bowler"), ("Tim Southee", "Bowler"),
        ("Lockie Ferguson", "Bowler"), ("Ish Sodhi", "Bowler"), ("Michael Bracewell", "All-Rounder"),
        ("Tom Latham", "Wicketkeeper"), ("Finn Allen", "Batsman"), ("Matt Henry", "Bowler"),
    ],
    "West Indies": [
        ("Nicholas Pooran", "Wicketkeeper"), ("Shai Hope", "Batsman"), ("Brandon King", "Batsman"),
        ("Rovman Powell", "Batsman"), ("Shimron Hetmyer", "Batsman"), ("Andre Russell", "All-Rounder"),
        ("Jason Holder", "All-Rounder"), ("Akeal Hosein", "Bowler"), ("Alzarri Joseph", "Bowler"),
        ("Obed McCoy", "Bowler"), ("Gudakesh Motie", "Bowler"), ("Kyle Mayers", "All-Rounder"),
        ("Johnson Charles", "Batsman"), ("Romario Shepherd", "All-Rounder"), ("Fabian Allen", "All-Rounder"),
    ],
    "Sri Lanka": [
        ("Pathum Nissanka", "Batsman"), ("Kusal Mendis", "Wicketkeeper"), ("Charith Asalanka", "Batsman"),
        ("Dhananjaya de Silva", "All-Rounder"), ("Dasun Shanaka", "All-Rounder"), ("Wanindu Hasaranga", "All-Rounder"),
        ("Maheesh Theekshana", "Bowler"), ("Matheesha Pathirana", "Bowler"), ("Dilshan Madushanka", "Bowler"),
        ("Dunith Wellalage", "All-Rounder"), ("Kusal Perera", "Batsman"), ("Sadeera Samarawickrama", "Batsman"),
        ("Nuwan Thushara", "Bowler"), ("Bhanuka Rajapaksa", "Batsman"), ("Dushmantha Chameera", "Bowler"),
    ],
    "Afghanistan": [
        ("Rahmanullah Gurbaz", "Wicketkeeper"), ("Ibrahim Zadran", "Batsman"), ("Najibullah Zadran", "Batsman"),
        ("Rashid Khan", "All-Rounder"), ("Mohammad Nabi", "All-Rounder"), ("Gulbadin Naib", "All-Rounder"),
        ("Fazalhaq Farooqi", "Bowler"), ("Naveen-ul-Haq", "Bowler"), ("Mujeeb Ur Rahman", "Bowler"),
        ("Azmatullah Omarzai", "All-Rounder"), ("Hazratullah Zazai", "Batsman"), ("Karim Janat", "All-Rounder"),
        ("Nangeyalia Kharote", "Bowler"), ("Sediqullah Atal", "Batsman"), ("Rahmat Shah", "Batsman"),
    ],
    "Netherlands": [
        ("Max ODowd", "Batsman"), ("Vikramjit Singh", "Batsman"), ("Bas de Leede", "All-Rounder"),
        ("Scott Edwards", "Wicketkeeper"), ("Tom Cooper", "All-Rounder"), ("Teja Nidamanuru", "Batsman"),
        ("Logan van Beek", "All-Rounder"), ("Ryan Klein", "Bowler"), ("Paul van Meekeren", "Bowler"),
        ("Tim Pringle", "Bowler"), ("Aryan Dutt", "Bowler"), ("Wesley Barresi", "Batsman"),
        ("Shariz Ahmad", "Bowler"), ("Kyle Klein", "Bowler"), ("Sybrand Engelbrecht", "Batsman"),
    ],
    "Scotland": [
        ("George Munsey", "Batsman"), ("Michael Jones", "Batsman"), ("Brandon McMullen", "All-Rounder"),
        ("Richie Berrington", "All-Rounder"), ("Matthew Cross", "Wicketkeeper"), ("Chris Greaves", "All-Rounder"),
        ("Mark Watt", "Bowler"), ("Safyaan Sharif", "Bowler"), ("Brad Wheal", "Bowler"),
        ("Josh Davey", "All-Rounder"), ("Ollie Hairs", "Batsman"), ("Michael Leask", "All-Rounder"),
        ("Chris Sole", "Bowler"), ("Charlie Tear", "Wicketkeeper"), ("Jack Jarvis", "Bowler"),
    ],
    "Ireland": [
        ("Paul Stirling", "Batsman"), ("Andrew Balbirnie", "Batsman"), ("Lorcan Tucker", "Wicketkeeper"),
        ("Harry Tector", "Batsman"), ("Curtis Campher", "All-Rounder"), ("George Dockrell", "All-Rounder"),
        ("Gareth Delany", "All-Rounder"), ("Mark Adair", "All-Rounder"), ("Josh Little", "Bowler"),
        ("Barry McCarthy", "Bowler"), ("Craig Young", "Bowler"), ("Ben White", "Bowler"),
        ("Ross Adair", "Batsman"), ("Neil Rock", "Wicketkeeper"), ("Graham Hume", "Bowler"),
    ],
    "Zimbabwe": [
        ("Craig Ervine", "Batsman"), ("Sean Williams", "All-Rounder"), ("Sikandar Raza", "All-Rounder"),
        ("Regis Chakabva", "Wicketkeeper"), ("Wesley Madhevere", "All-Rounder"), ("Ryan Burl", "All-Rounder"),
        ("Luke Jongwe", "All-Rounder"), ("Blessing Muzarabani", "Bowler"), ("Richard Ngarava", "Bowler"),
        ("Tendai Chatara", "Bowler"), ("Tadiwanashe Marumani", "Batsman"), ("Clive Madande", "Wicketkeeper"),
        ("Brian Bennett", "Batsman"), ("Dion Myers", "All-Rounder"), ("Brad Evans", "All-Rounder"),
    ],
    "Namibia": [
        ("Gerhard Erasmus", "All-Rounder"), ("Stephan Baard", "Batsman"), ("Jan Nicol Loftie-Eaton", "All-Rounder"),
        ("Zane Green", "Wicketkeeper"), ("Michael van Lingen", "All-Rounder"), ("David Wiese", "All-Rounder"),
        ("JJ Smit", "All-Rounder"), ("Jan Frylinck", "All-Rounder"), ("Ruben Trumpelmann", "Bowler"),
        ("Ben Shikongo", "Bowler"), ("Bernard Scholtz", "Bowler"), ("Tangeni Lungameni", "Bowler"),
        ("Niko Davin", "Batsman"), ("Lohan Louwrens", "Wicketkeeper"), ("Jack Brassell", "Batsman"),
    ],
    "USA": [
        ("Monank Patel", "Wicketkeeper"), ("Steven Taylor", "Batsman"), ("Aaron Jones", "Batsman"),
        ("Andries Gous", "Wicketkeeper"), ("Corey Anderson", "All-Rounder"), ("Nitish Kumar", "All-Rounder"),
        ("Harmeet Singh", "All-Rounder"), ("Shadley van Schalkwyk", "Bowler"), ("Ali Khan", "Bowler"),
        ("Saurabh Netravalkar", "Bowler"), ("Nosthush Kenjige", "Bowler"), ("Milind Kumar", "Batsman"),
        ("Gajanand Singh", "All-Rounder"), ("Jasdeep Singh", "Bowler"), ("Shayan Jahangir", "Batsman"),
    ],
    "Nepal": [
        ("Kushal Bhurtel", "Batsman"), ("Aasif Sheikh", "Wicketkeeper"), ("Rohit Paudel", "Batsman"),
        ("Kushal Malla", "Batsman"), ("Dipendra Singh Airee", "All-Rounder"), ("Sompal Kami", "All-Rounder"),
        ("Sandeep Lamichhane", "Bowler"), ("Karan KC", "All-Rounder"), ("Abinash Bohara", "Bowler"),
        ("Lalit Rajbanshi", "Bowler"), ("Gulshan Jha", "All-Rounder"), ("Aarif Sheikh", "Batsman"),
        ("Bibek Yadav", "Bowler"), ("Sundeep Jora", "Batsman"), ("Pratish GC", "Batsman"),
    ],
    "Oman": [
        ("Aqib Ilyas", "All-Rounder"), ("Kashyap Prajapati", "Batsman"), ("Zeeshan Maqsood", "All-Rounder"),
        ("Ayaan Khan", "All-Rounder"), ("Naseem Khushi", "Wicketkeeper"), ("Shoaib Khan", "Batsman"),
        ("Mehran Khan", "Bowler"), ("Bilal Khan", "Bowler"), ("Kaleemullah", "Bowler"),
        ("Fayyaz Butt", "All-Rounder"), ("Rafiullah", "Bowler"), ("Pratik Athavale", "Batsman"),
        ("Sufyan Mehmood", "Batsman"), ("Jatinder Singh", "Batsman"), ("Shakeel Ahmad", "Bowler"),
    ],
    "UAE": [
        ("Muhammad Waseem", "Batsman"), ("Chirag Suri", "Batsman"), ("Vriitya Aravind", "Wicketkeeper"),
        ("CP Rizwan", "All-Rounder"), ("Basil Hameed", "Batsman"), ("Kashif Daud", "All-Rounder"),
        ("Ahmed Raza", "All-Rounder"), ("Junaid Siddique", "Bowler"), ("Zahoor Khan", "Bowler"),
        ("Alishan Sharafu", "All-Rounder"), ("Karthik Meiyappan", "Bowler"), ("Aayan Afzal Khan", "Bowler"),
        ("Ethan DSouza", "Batsman"), ("Aryansh Sharma", "Wicketkeeper"), ("Sanchit Sharma", "Bowler"),
    ],
    "Canada": [
        ("Aaron Johnson", "Batsman"), ("Navneet Dhaliwal", "Batsman"), ("Nicholas Kirton", "Batsman"),
        ("Shreyas Movva", "Wicketkeeper"), ("Ravinderpal Singh", "All-Rounder"), ("Saad Bin Zafar", "All-Rounder"),
        ("Dilpreet Bajwa", "All-Rounder"), ("Kaleem Sana", "Bowler"), ("Jeremy Gordon", "Bowler"),
        ("Dillon Heyliger", "All-Rounder"), ("Junaid Siddiqui", "Bowler"), ("Pargat Singh", "Batsman"),
        ("Rishiv Joshi", "Batsman"), ("Harsh Thaker", "Batsman"), ("Dilon Heyliger", "Bowler"),
    ],
    "Italy": [
        ("Gareth Berg", "All-Rounder"), ("Baljit Singh", "Batsman"), ("Amir Sharif", "Bowler"),
        ("Nikolai Smith", "Batsman"), ("Grant Stewart", "All-Rounder"), ("Damian Crowley", "Batsman"),
        ("Jaspreet Singh", "All-Rounder"), ("Ravi Shankar", "Bowler"), ("Manpreet Singh", "Bowler"),
        ("Crishan Kalugamage", "Batsman"), ("Ali Ferrario", "Wicketkeeper"), ("Joy Perera", "Batsman"),
        ("Dinidu Marage", "All-Rounder"), ("Haseeb Khan", "Bowler"), ("Gian Ghia", "Batsman"),
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
