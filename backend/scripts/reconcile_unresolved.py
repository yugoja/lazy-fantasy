"""Reconcile unresolved football players across matches that recorded a
sync_error. For each unresolved API stat, find the DB player on the same team
whose surname token uniquely matches, and (with --apply) set that DB player's
api_football_player_id to the API id so future syncs resolve via tier-1.

Read-only by default. Pass --apply to write, then the caller should re-sync the
affected matches to rescore.

Usage:
  python scripts/reconcile_unresolved.py            # diagnostic
  python scripts/reconcile_unresolved.py --apply     # apply api_id fixes
"""
from __future__ import annotations

import sys

from app.database import SessionLocal
from app.config import settings
from app.models.match import Match
from app.models.player import Player
from app.models.football_prediction import FootballPrediction
from app.models.prediction import Prediction
from app.services.football_provider import ApiFootballProvider
from app.services import football_sync
from app.services.football_sync import _resolve_football_player, _normalize

# Name particles that are too common to match on (Arabic/Iberian/Dutch etc.).
PARTICLES = {"al", "el", "de", "da", "do", "di", "van", "von", "der", "den",
             "bin", "ben", "abu", "st", "le", "la", "dos", "das", "des", "ter"}


def _distinctive(name: str) -> set[str]:
    """Tokens distinctive enough to match a player on: length >= 4 and not a
    common name particle."""
    return {t for t in _normalize(name).split() if len(t) >= 4 and t not in PARTICLES}


def _picked_counts(db, match_id):
    rows = (
        db.query(FootballPrediction.player_pick_1_id,
                 FootballPrediction.player_pick_2_id,
                 FootballPrediction.player_pick_3_id)
        .join(Prediction, Prediction.id == FootballPrediction.prediction_id)
        .filter(Prediction.match_id == match_id).all()
    )
    counts = {}
    for r in rows:
        for pid in r:
            if pid:
                counts[pid] = counts.get(pid, 0) + 1
    return counts


def main(apply: bool):
    db = SessionLocal()
    football_sync.set_provider(
        ApiFootballProvider(settings.FOOTBALL_API_KEY, settings.FOOTBALL_API_BASE_URL))
    provider = football_sync.get_provider()

    matches = db.query(Match).filter(Match.sync_error != None).order_by(Match.id).all()  # noqa: E711
    print(f"matches with sync_error: {len(matches)}")

    proposals = []  # (player, api_id, match_id, picked_count)
    conflicts = []
    for m in matches:
        if not (m.external_match_id or "").lstrip("-").isdigit():
            continue
        fixture_id = int(m.external_match_id)
        result = provider.get_fixture_result(fixture_id)
        stats = provider.get_player_stats(fixture_id)
        if not result or not stats:
            print(f"  match {m.id}: no result/stats (skip)")
            continue
        home_api = result.home_team_api_id
        team1_db = db.query(Player).filter(Player.team_id == m.team_1_id).all()
        team2_db = db.query(Player).filter(Player.team_id == m.team_2_id).all()
        picks = _picked_counts(db, m.id)

        for stat in stats:
            same_team = team1_db if stat.team_api_id == home_api else team2_db
            if _resolve_football_player(stat, same_team, db):
                continue  # resolves fine
            # unresolved — rank DB players by how many distinctive tokens they
            # share with the API name; accept only an unambiguous best match.
            stat_tokens = _distinctive(stat.name)
            scored = [(len(_distinctive(p.name) & stat_tokens), p) for p in same_team]
            scored = [(n, p) for n, p in scored if n > 0]
            scored.sort(key=lambda x: -x[0])
            picked = sum(picks.get(p.id, 0) for _, p in scored)
            tag = f" [PICKED x{picked}]" if picked else ""
            best = scored[0] if scored else None
            runner = scored[1][0] if len(scored) > 1 else 0
            # Unambiguous = single candidate, or top strictly beats the rest.
            if best and best[0] > runner:
                p = best[1]
                cur = p.api_football_player_id
                # Only a fix if the api id differs / is missing, and that api id
                # isn't already held by another player.
                holder = db.query(Player).filter(
                    Player.api_football_player_id == str(stat.api_player_id)).first()
                if cur == str(stat.api_player_id):
                    continue
                if holder and holder.id != p.id:
                    conflicts.append((m.id, stat.name, stat.api_player_id, p.name, holder.name))
                    print(f"  match {m.id}: CONFLICT '{stat.name}' api {stat.api_player_id} "
                          f"-> '{p.name}' but id held by '{holder.name}'{tag}")
                    continue
                proposals.append((p, str(stat.api_player_id), m.id, picks.get(p.id, 0)))
                print(f"  match {m.id}: '{stat.name}' api {stat.api_player_id} -> "
                      f"DB '{p.name}' (id {p.id}, was api {cur}){tag}")
            else:
                names = [f"{p.name}({n})" for n, p in scored]
                print(f"  match {m.id}: '{stat.name}' api {stat.api_player_id} -> "
                      f"{len(scored)} candidates {names}{tag} (manual)")

    print("-" * 60)
    print(f"proposals: {len(proposals)} | conflicts: {len(conflicts)}")
    affected_matches = sorted({m for _, _, m, _ in proposals})
    print(f"matches that would change: {affected_matches}")

    if apply and proposals:
        for p, api_id, _m, _c in proposals:
            p.api_football_player_id = api_id
        db.commit()
        print(f"APPLIED {len(proposals)} api_id fixes.")
        print(f"Re-syncing affected matches: {affected_matches}")
        for mid in affected_matches:
            res = football_sync.sync_match_result(db, mid)
            print(f"  match {mid}: {res.get('status')} "
                  f"({res.get('predictions_processed')} preds) "
                  f"unresolved={len(res.get('unresolved_players') or [])}")
    elif apply:
        print("nothing to apply")
    else:
        print("(dry run — pass --apply to write)")
    db.close()


if __name__ == "__main__":
    main("--apply" in sys.argv)
