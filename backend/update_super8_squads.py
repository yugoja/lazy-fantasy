"""
One-time script to update Super Eight team squads with confirmed replacements.
Run: python update_super8_squads.py
"""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Team, Player

db = SessionLocal()

def swap(team_short, old_name, new_name, new_role=None):
    team = db.query(Team).filter(Team.short_name == team_short).first()
    if not team:
        print(f'  TEAM NOT FOUND: {team_short}')
        return
    player = db.query(Player).filter(Player.name == old_name, Player.team_id == team.id).first()
    if not player:
        print(f'  ALREADY DONE or NOT FOUND: {old_name} in {team_short}')
        return
    old_role = player.role
    player.name = new_name
    if new_role:
        player.role = new_role
    print(f'  {team_short}: {old_name} -> {new_name} ({new_role or old_role})')

def add_player(team_short, name, role):
    team = db.query(Team).filter(Team.short_name == team_short).first()
    if not team:
        print(f'  TEAM NOT FOUND: {team_short}')
        return
    existing = db.query(Player).filter(Player.name == name, Player.team_id == team.id).first()
    if existing:
        print(f'  ALREADY EXISTS: {name} in {team_short}')
        return
    db.add(Player(name=name, team_id=team.id, role=role))
    print(f'  {team_short}: Added {name} ({role})')

def fix_role(team_short, name, new_role):
    team = db.query(Team).filter(Team.short_name == team_short).first()
    if not team:
        return
    player = db.query(Player).filter(Player.name == name, Player.team_id == team.id).first()
    if player and player.role != new_role:
        player.role = new_role
        print(f'  {team_short}: {name} role -> {new_role}')

try:
    print('Updating Super Eight squads...\n')

    print('India:')
    swap('IND', 'Mohammed Siraj', 'Harshit Rana', 'Bowler')

    print('South Africa:')
    swap('SA', 'Heinrich Klaasen', 'Jason Smith', 'All-Rounder')

    print('West Indies:')
    swap('WI', 'Andre Russell', 'Roston Chase', 'All-Rounder')
    swap('WI', 'Alzarri Joseph', 'Jayden Seales', 'Bowler')
    swap('WI', 'Nicholas Pooran', 'Quentin Sampson', 'Bowler')

    print('New Zealand:')
    swap('NZ', 'Michael Bracewell', 'Cole McConchie', 'All-Rounder')

    print('Sri Lanka:')
    add_player('SL', 'Kamil Mishara', 'Wicketkeeper')
    add_player('SL', 'Dilshan Madushanka', 'Bowler')
    fix_role('SL', 'Dushan Hemantha', 'All-Rounder')

    db.commit()
    print('\nDone!')
finally:
    db.close()
