"""Unit tests for one-off dugout announcements (audience, expiry, anchoring).

`_announcement_events` does not touch the DB, so these run with a stub league
and a patched announcement set — no DB fixture needed."""
from dataclasses import dataclass
from datetime import datetime, timedelta

import app.services.dugout as dugout
from app.services.announcements import Announcement
from app.schemas.dugout import DugoutEventType


@dataclass
class _League:
    id: int
    name: str
    sport: str = "football"


def _ann(audience, *, expired=False):
    when = datetime.utcnow() + (timedelta(days=-1) if expired else timedelta(days=7))
    return Announcement(
        key="test_ann",
        title="Scoring correction",
        body="We re-scored some matches.",
        expires_at=when,
        audience=frozenset(audience),
    )


def test_affected_user_gets_announcement(monkeypatch):
    monkeypatch.setattr(dugout, "ACTIVE_ANNOUNCEMENTS", (_ann({7, 8}),))
    leagues = [_League(1, "Alpha"), _League(2, "Beta")]
    events = dugout._announcement_events(None, 7, leagues)
    assert len(events) == 1
    e = events[0]
    assert e.type == DugoutEventType.ANNOUNCEMENT
    assert e.announcement_title == "Scoring correction"
    assert e.announcement_body
    # Anchored to a single league so it shows once, not per-league
    assert e.league_id == 1
    assert e.username == "test_ann"   # dismissal anchor
    assert e.match_id is None


def test_unaffected_user_gets_nothing(monkeypatch):
    monkeypatch.setattr(dugout, "ACTIVE_ANNOUNCEMENTS", (_ann({7, 8}),))
    leagues = [_League(1, "Alpha")]
    assert dugout._announcement_events(None, 99, leagues) == []


def test_expired_announcement_is_hidden(monkeypatch):
    monkeypatch.setattr(dugout, "ACTIVE_ANNOUNCEMENTS", (_ann({7}, expired=True),))
    leagues = [_League(1, "Alpha")]
    assert dugout._announcement_events(None, 7, leagues) == []


def test_no_leagues_no_announcement(monkeypatch):
    monkeypatch.setattr(dugout, "ACTIVE_ANNOUNCEMENTS", (_ann({7}),))
    assert dugout._announcement_events(None, 7, []) == []


def test_announcement_sorts_first():
    assert dugout._PRIORITY[DugoutEventType.ANNOUNCEMENT] < dugout._PRIORITY[DugoutEventType.TOURNAMENT_PICKS]
