"""One-off dugout announcements.

These are temporary, hand-curated system messages surfaced in the dugout feed.
Each has a stable ``key`` (used as the dismissal anchor's subject_username),
an expiry after which it stops showing, and an audience (None = all users).

GK_SCORING_FIX (2026-06-25): on 2026-06-24 a parser bug was fixed that had been
crediting goalkeepers +5 for every routine save (it read total saves instead of
penalty saves). All completed matches were re-scored; the users below are those
whose total *dropped* as a result. Safe to delete this module's entry after the
expiry passes.
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


GK_SCORING_FIX = Announcement(
    key="gk_scoring_fix_2026_06",
    title="Scoring correction",
    body=(
        "We found and fixed a bug that was over-crediting goalkeeper saves, so "
        "we re-scored the matches it touched. Your total dropped a little as a "
        "result — the leaderboards are accurate now. Sorry for the mix-up!"
    ),
    expires_at=datetime(2026, 7, 2),  # ~1 week
    audience=frozenset({
        51, 73, 47, 2, 57, 46, 4, 74, 71, 43,
        75, 60, 70, 38, 66, 72, 62, 39, 59,
    }),
)

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
)


# All active announcements considered by the dugout generator.
ACTIVE_ANNOUNCEMENTS: tuple[Announcement, ...] = (GK_SCORING_FIX, WORLD_CUP_PICKS_OPEN)
