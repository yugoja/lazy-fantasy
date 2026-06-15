"""store_match_formation persists the announced formation + per-player grid,
mapping API player ids to DB players (skipping unresolved ones)."""
import json
from types import SimpleNamespace as NS

import pytest

from app.models.player import Player
from app.services.football_provider import TeamFormation, LineupSlot
from app.services.player_form_service import store_match_formation


@pytest.fixture
def football_match_with_ids(db_session, test_match, test_teams):
    team1, team2 = test_teams
    # give players known api ids so the API->DB mapping resolves
    for p in db_session.query(Player).filter(Player.team_id.in_([team1.id, team2.id])).all():
        p.api_football_player_id = f"api{p.id}"
    test_match.external_match_id = "555"
    db_session.commit()
    return test_match, team1, team2


def test_stores_formation_and_grid(db_session, football_match_with_ids):
    match, team1, team2 = football_match_with_ids
    t1 = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2 = db_session.query(Player).filter(Player.team_id == team2.id).all()

    home = TeamFormation(formation="4-2-3-1", starters=[
        LineupSlot(api_player_id=int(t1[0].id), row=1, col=1),
        LineupSlot(api_player_id=int(t1[1].id), row=2, col=1),
        LineupSlot(api_player_id=999999, row=2, col=2),  # unresolved -> skipped
    ])
    away = TeamFormation(formation="3-5-2", starters=[
        LineupSlot(api_player_id=int(t2[0].id), row=1, col=1),
    ])

    # provider maps api id -> "api<db_id>", matching how we seeded the ids
    class P:
        def get_fixture_formations(self, fid):
            assert fid == 555
            # remap to the stored "api<id>" form
            for tf in (home, away):
                for s in tf.starters:
                    s.api_player_id = f"api{s.api_player_id}"
            return home, away

    ok = store_match_formation(db_session, match, P())
    assert ok is True

    data = json.loads(match.lineup_data)
    assert data["team1_formation"] == "4-2-3-1"
    assert data["team2_formation"] == "3-5-2"
    assert data["slots"][str(t1[0].id)] == [1, 1]
    assert data["slots"][str(t1[1].id)] == [2, 1]
    assert str(t2[0].id) in data["slots"]
    # the unresolved api id contributed no slot
    assert len(data["slots"]) == 3


def test_returns_false_when_no_lineup(db_session, football_match_with_ids):
    match, _, _ = football_match_with_ids

    class P:
        def get_fixture_formations(self, fid):
            return None

    assert store_match_formation(db_session, match, P()) is False
    assert match.lineup_data is None
