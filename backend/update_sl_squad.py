"""
One-time script to update Sri Lanka squad with injury replacements.
Adds Kamil Mishara and Dilshan Madushanka, fixes Dushan Hemantha role.
Run: python update_sl_squad.py
"""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Team, Player

db = SessionLocal()
try:
    sl = db.query(Team).filter(Team.short_name == 'SL').first()
    if not sl:
        print('Sri Lanka team not found')
        sys.exit(1)

    # Add Kamil Mishara if not exists
    if not db.query(Player).filter(Player.name == 'Kamil Mishara', Player.team_id == sl.id).first():
        db.add(Player(name='Kamil Mishara', team_id=sl.id, role='Wicketkeeper'))
        print('Added Kamil Mishara (WK)')
    else:
        print('Kamil Mishara already exists')

    # Add Dilshan Madushanka if not exists
    if not db.query(Player).filter(Player.name == 'Dilshan Madushanka', Player.team_id == sl.id).first():
        db.add(Player(name='Dilshan Madushanka', team_id=sl.id, role='Bowler'))
        print('Added Dilshan Madushanka (Bowler)')
    else:
        print('Dilshan Madushanka already exists')

    # Fix Dushan Hemantha role
    dh = db.query(Player).filter(Player.name == 'Dushan Hemantha', Player.team_id == sl.id).first()
    if dh and dh.role != 'All-Rounder':
        dh.role = 'All-Rounder'
        print('Updated Dushan Hemantha role to All-Rounder')
    else:
        print('Dushan Hemantha role already correct')

    db.commit()
    print(f'\nSri Lanka squad now has {db.query(Player).filter(Player.team_id == sl.id).count()} players')
finally:
    db.close()
