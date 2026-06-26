"""Add squad players that exist in api-football but are missing from our DB.

Our squads were seeded from the pre-tournament FIFA PDF, which diverges from
api-football's current squads (late call-ups / replacements) and omitted
api_football_player_id. This inserts any API squad player whose api_id isn't
already on the team, with the api_id set (so result-sync resolves them via
tier-1) and the position mapped to our role vocabulary.

It never deletes/edits existing players. Re-runnable (e.g. before each knockout
round). Dry-run by default; pass --apply to write.
"""
from __future__ import annotations

import sys
import time

import requests

from app.database import SessionLocal
from app.config import settings
from app.models.team import Team
from app.models.player import Player
from app.services.football_sync import _normalize

# api-football position -> our Player.role / scoring Position value.
POS_MAP = {"Goalkeeper": "Goalkeeper", "Defender": "Defender",
           "Midfielder": "Midfielder", "Attacker": "Forward"}

# Name particles too common to match on (mirror reconcile_unresolved.py).
PARTICLES = {"al", "el", "de", "da", "do", "di", "van", "von", "der", "den",
             "bin", "ben", "abu", "st", "le", "la", "dos", "das", "des", "ter"}


def _distinctive(name: str) -> set[str]:
    return {t for t in _normalize(name).split() if len(t) >= 4 and t not in PARTICLES}

H = {"x-apisports-key": settings.FOOTBALL_API_KEY}
BASE = "https://v3.football.api-sports.io"


def _full_name(api_id: int, fallback: str) -> str:
    """Best display name in our 'SURNAME First' convention, via players/profiles."""
    try:
        r = requests.get(f"{BASE}/players/profiles", headers=H, params={"player": api_id}, timeout=15)
        resp = (r.json().get("response") or [])
        if resp:
            p = resp[0].get("player", {})
            fn, ln = (p.get("firstname") or "").strip(), (p.get("lastname") or "").strip()
            if ln:
                return f"{ln.upper()} {fn}".strip()
            if p.get("name"):
                return p["name"]
    except Exception:
        pass
    return fallback


def main(apply: bool):
    db = SessionLocal()
    teams = db.query(Team).filter(Team.sport == "football", Team.api_football_team_id != None).all()  # noqa: E711
    to_add = []      # (team, api_id, name, role)
    collisions = []  # (team, api_name, api_id, existing_db_name) — same player, different api_id
    for t in teams:
        db_players = db.query(Player).filter(Player.team_id == t.id).all()
        db_apiids = {p.api_football_player_id for p in db_players if p.api_football_player_id}
        # token -> db players holding it; a token unique to one player is a
        # reliable identifier (a surname), unlike a common given name shared by
        # many ("joao", "mohammed").
        from collections import defaultdict
        tok_owner: dict[str, list] = defaultdict(list)
        for dp in db_players:
            for tok in _distinctive(dp.name):
                tok_owner[tok].append(dp)
        r = requests.get(f"{BASE}/players/squads", headers=H, params={"team": t.api_football_team_id}, timeout=15)
        api = (r.json().get("response") or [{}])[0].get("players", [])
        for p in api:
            apid = str(p.get("id"))
            if apid in db_apiids:
                continue
            # Name-collision guard: api-football sometimes lists a different id in
            # the squad endpoint than in match stats. Treat as the same player
            # only when they share a token unique to one DB player (a surname) —
            # skip (adding would duplicate) and flag for review.
            api_tokens = _distinctive(p.get("name", ""))
            existing = next(
                (tok_owner[tok][0] for tok in api_tokens if len(tok_owner.get(tok, [])) == 1),
                None,
            )
            if existing:
                collisions.append((t.name, p.get("name"), apid, existing.name))
                continue
            pos = p.get("position") or "Attacker"
            role = POS_MAP.get(pos)
            if role is None:
                print(f"  WARN unknown position {pos!r} for {p.get('name')} ({t.name}) — skipping")
                continue
            name = _full_name(int(p["id"]), p.get("name", ""))
            to_add.append((t, apid, name, role))
            print(f"  {t.name}: + {name} (api {apid}, {role})")
        time.sleep(0.1)

    print("-" * 60)
    if collisions:
        print(f"name collisions skipped (same player, different api_id — review): {len(collisions)}")
        for tname, api_name, apid, db_name in collisions:
            print(f"  {tname}: API '{api_name}' (api {apid}) ~ DB '{db_name}'")
        print("-" * 60)
    print(f"missing players to add: {len(to_add)} across {len({t.id for t,_,_,_ in to_add})} teams")
    if apply and to_add:
        for t, apid, name, role in to_add:
            db.add(Player(name=name, role=role, team_id=t.id, api_football_player_id=apid))
        db.commit()
        print(f"APPLIED: inserted {len(to_add)} players.")
    elif apply:
        print("nothing to add")
    else:
        print("(dry run — pass --apply to write)")
    db.close()


if __name__ == "__main__":
    main("--apply" in sys.argv)
