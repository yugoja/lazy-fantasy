"""One-off dugout announcements.

These are temporary, hand-curated system messages surfaced in the dugout feed.
Each has a stable ``key`` (used as the dismissal anchor's subject_username),
an expiry after which it stops showing, and an audience (None = all users).

To add a new announcement: create an ``Announcement`` instance below, add it to
``ACTIVE_ANNOUNCEMENTS``, and remove it (or leave ``ACTIVE_ANNOUNCEMENTS = ()``)
once its expiry has passed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Announcement:
    key: str                          # stable id; also the dismissal subject_username
    title: str
    body: str
    expires_at: datetime              # naive UTC; not shown after this
    audience: Optional[frozenset[int]]  # user_ids who should see it; None = everyone
    link: Optional[str] = None        # frontend href shown as a CTA button


WORLD_CUP_PICKS_OPEN = Announcement(
    key="wc2026_picks_closing_soon",
    title="Make your World Cup picks!",
    body=(
        "Tournament picks are open now — pick your 4 semi-finalists plus "
        "Golden Boot, Ball & Glove winners. Picks lock when the knockout stage "
        "kicks off. Up to 250 pts!"
    ),
    expires_at=datetime(2026, 6, 28, 19, 0),  # first R32 kickoff (SoFi, 19:00 UTC)
    audience=None,                    # show to all users
    link="/tournaments",
)


# All active announcements considered by the dugout generator.
ACTIVE_ANNOUNCEMENTS: tuple[Announcement, ...] = (WORLD_CUP_PICKS_OPEN,)
