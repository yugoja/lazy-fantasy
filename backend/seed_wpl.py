"""
Seed script for Women's Premier League 2026 data.
Adds the tournament, teams, players, and matches to the database.
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Tournament, Team, Player, Match, MatchStatus

# Time slots in IST (UTC+5:30) converted to UTC
TIME_SLOTS = {
    "Afternoon": "09:30:00",  # 3:00 PM IST = 9:30 AM UTC
    "Evening": "14:00:00",    # 7:30 PM IST = 2:00 PM UTC
}

# WPL Teams and their players
WPL_TEAMS = {
    "Mumbai Indians": {
        "short_name": "MI",
        "players": [
            ("Harmanpreet Kaur", "All-Rounder"),
            ("Nat Sciver-Brunt", "All-Rounder"),
            ("Hayley Matthews", "All-Rounder"),
            ("Amelia Kerr", "All-Rounder"),
            ("Pooja Vastrakar", "All-Rounder"),
            ("Yastika Bhatia", "Wicketkeeper"),
            ("Saika Ishaque", "Bowler"),
            ("Issy Wong", "Bowler"),
            ("Shabnim Ismail", "Bowler"),
            ("Jemimah Rodrigues", "Batsman"),
            ("Keerthana T", "Batsman"),
        ]
    },
    "Royal Challengers Bengaluru": {
        "short_name": "RCB",
        "players": [
            ("Smriti Mandhana", "Batsman"),
            ("Ellyse Perry", "All-Rounder"),
            ("Sophie Devine", "All-Rounder"),
            ("Richa Ghosh", "Wicketkeeper"),
            ("Renuka Singh", "Bowler"),
            ("Sophie Molineux", "Bowler"),
            ("Shreyanka Patil", "All-Rounder"),
            ("Kanika Ahuja", "All-Rounder"),
            ("Asha Sobhana", "Bowler"),
            ("Georgia Wareham", "Bowler"),
            ("Sabbhineni Meghana", "Batsman"),
        ]
    },
    "UP Warriorz": {
        "short_name": "UPW",
        "players": [
            ("Alyssa Healy", "Wicketkeeper"),
            ("Tahlia McGrath", "All-Rounder"),
            ("Deepti Sharma", "All-Rounder"),
            ("Sophie Ecclestone", "Bowler"),
            ("Grace Harris", "All-Rounder"),
            ("Shweta Sehrawat", "Batsman"),
            ("Rajeshwari Gayakwad", "Bowler"),
            ("Anjali Sarvani", "Bowler"),
            ("Kiran Navgire", "All-Rounder"),
            ("Vrinda Dinesh", "Batsman"),
            ("Parshavi Chopra", "Bowler"),
        ]
    },
    "Gujarat Giants": {
        "short_name": "GG",
        "players": [
            ("Beth Mooney", "Wicketkeeper"),
            ("Ashleigh Gardner", "All-Rounder"),
            ("Laura Wolvaardt", "Batsman"),
            ("Kim Garth", "Bowler"),
            ("Dayalan Hemalatha", "All-Rounder"),
            ("Harleen Deol", "Batsman"),
            ("Tanuja Kanwar", "Bowler"),
            ("Phoebe Litchfield", "Batsman"),
            ("Shabnam Shakil", "Bowler"),
            ("Bharti Fulmali", "All-Rounder"),
            ("Priya Mishra", "Bowler"),
        ]
    },
    "Delhi Capitals": {
        "short_name": "DC",
        "players": [
            ("Meg Lanning", "Batsman"),
            ("Shafali Verma", "Batsman"),
            ("Marizanne Kapp", "All-Rounder"),
            ("Jess Jonassen", "All-Rounder"),
            ("Alice Capsey", "All-Rounder"),
            ("Radha Yadav", "Bowler"),
            ("Titas Sadhu", "Bowler"),
            ("Jemimah Rodrigues", "Batsman"),
            ("Minnu Mani", "All-Rounder"),
            ("Arundhati Reddy", "Bowler"),
            ("Taniyaa Bhatia", "Wicketkeeper"),
        ]
    },
}

# WPL Matches
WPL_MATCHES = [
    {"match_number": 1, "date": "2026-01-09", "team_1": "Mumbai Indians", "team_2": "Royal Challengers Bengaluru", "time_slot": "Evening"},
    {"match_number": 2, "date": "2026-01-10", "team_1": "UP Warriorz", "team_2": "Gujarat Giants", "time_slot": "Afternoon"},
    {"match_number": 3, "date": "2026-01-10", "team_1": "Mumbai Indians", "team_2": "Delhi Capitals", "time_slot": "Evening"},
    {"match_number": 4, "date": "2026-01-11", "team_1": "Delhi Capitals", "team_2": "Gujarat Giants", "time_slot": "Evening"},
    {"match_number": 5, "date": "2026-01-12", "team_1": "Royal Challengers Bengaluru", "team_2": "UP Warriorz", "time_slot": "Evening"},
    {"match_number": 6, "date": "2026-01-13", "team_1": "Mumbai Indians", "team_2": "Gujarat Giants", "time_slot": "Evening"},
    {"match_number": 7, "date": "2026-01-14", "team_1": "UP Warriorz", "team_2": "Delhi Capitals", "time_slot": "Evening"},
    {"match_number": 8, "date": "2026-01-15", "team_1": "Mumbai Indians", "team_2": "UP Warriorz", "time_slot": "Evening"},
    {"match_number": 9, "date": "2026-01-16", "team_1": "Royal Challengers Bengaluru", "team_2": "Gujarat Giants", "time_slot": "Evening"},
    {"match_number": 10, "date": "2026-01-17", "team_1": "UP Warriorz", "team_2": "Mumbai Indians", "time_slot": "Afternoon"},
    {"match_number": 11, "date": "2026-01-17", "team_1": "Delhi Capitals", "team_2": "Royal Challengers Bengaluru", "time_slot": "Evening"},
    {"match_number": 12, "date": "2026-01-19", "team_1": "Gujarat Giants", "team_2": "Royal Challengers Bengaluru", "time_slot": "Evening"},
    {"match_number": 13, "date": "2026-01-20", "team_1": "Delhi Capitals", "team_2": "Mumbai Indians", "time_slot": "Evening"},
    {"match_number": 14, "date": "2026-01-22", "team_1": "Gujarat Giants", "team_2": "UP Warriorz", "time_slot": "Evening"},
    {"match_number": 15, "date": "2026-01-24", "team_1": "Royal Challengers Bengaluru", "team_2": "Delhi Capitals", "time_slot": "Evening"},
    {"match_number": 16, "date": "2026-01-26", "team_1": "Royal Challengers Bengaluru", "team_2": "Mumbai Indians", "time_slot": "Evening"},
    {"match_number": 17, "date": "2026-01-27", "team_1": "Gujarat Giants", "team_2": "Delhi Capitals", "time_slot": "Evening"},
    {"match_number": 18, "date": "2026-01-29", "team_1": "UP Warriorz", "team_2": "Royal Challengers Bengaluru", "time_slot": "Evening"},
    {"match_number": 19, "date": "2026-01-30", "team_1": "Gujarat Giants", "team_2": "Mumbai Indians", "time_slot": "Evening"},
    {"match_number": 20, "date": "2026-02-01", "team_1": "Delhi Capitals", "team_2": "UP Warriorz", "time_slot": "Evening"},
]

def seed_wpl():
    db = SessionLocal()
    
    try:
        # Create WPL Tournament
        print("Creating WPL 2026 tournament...")
        tournament = Tournament(
            name="Women's Premier League 2026",
            start_date=datetime(2026, 1, 9),
            end_date=datetime(2026, 2, 5),
        )
        db.add(tournament)
        db.commit()
        db.refresh(tournament)
        print(f"  Created: {tournament.name} (ID: {tournament.id})")
        
        # Create Teams and Players
        print("\nCreating teams and players...")
        team_map = {}  # team_name -> team_id
        
        for team_name, team_data in WPL_TEAMS.items():
            team = Team(
                name=team_name,
                short_name=team_data["short_name"],
            )
            db.add(team)
            db.commit()
            db.refresh(team)
            team_map[team_name] = team.id
            print(f"  Created team: {team_name} ({team_data['short_name']})")
            
            # Add players
            for player_name, role in team_data["players"]:
                player = Player(
                    name=player_name,
                    team_id=team.id,
                    role=role,
                )
                db.add(player)
            db.commit()
            print(f"    Added {len(team_data['players'])} players")
        
        # Create Matches
        print("\nCreating matches...")
        for match_data in WPL_MATCHES:
            time_str = TIME_SLOTS[match_data["time_slot"]]
            start_time = datetime.fromisoformat(f"{match_data['date']}T{time_str}+00:00")
            
            match = Match(
                tournament_id=tournament.id,
                team_1_id=team_map[match_data["team_1"]],
                team_2_id=team_map[match_data["team_2"]],
                start_time=start_time,
                status=MatchStatus.SCHEDULED,
            )
            db.add(match)
            print(f"  Match {match_data['match_number']}: {match_data['team_1']} vs {match_data['team_2']} on {match_data['date']}")
        
        db.commit()
        
        print("\n✅ WPL 2026 data seeded successfully!")
        print(f"\n📊 Summary:")
        print(f"  Tournament: {tournament.name}")
        print(f"  Teams: {len(WPL_TEAMS)}")
        print(f"  Players: {sum(len(t['players']) for t in WPL_TEAMS.values())}")
        print(f"  Matches: {len(WPL_MATCHES)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_wpl()
