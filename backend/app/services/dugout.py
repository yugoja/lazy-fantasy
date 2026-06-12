from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import League, LeagueMember, Match, MatchStatus, Prediction, Tournament, User
from app.models.dugout_dismissal import DugoutDismissal
from app.schemas.dugout import DugoutEvent, DugoutEventType
from app.services.league import _compute_standings, get_user_leagues
from app.services.match_verdict import get_match_verdict


# Caps for verdict surfacing in the dugout feed
VERDICT_MATCHES_PER_LEAGUE = 3
VERDICT_WINDOW_DAYS = 7
VERDICT_MAX_TOTAL = 6

# Hard cap on how many events of each kind the feed will ever show. Extras are
# discarded even if the user hasn't dismissed them, so no single kind floods it.
MAX_EVENTS_PER_TYPE = 3


def _limit_per_type(events: list[DugoutEvent], n: int = MAX_EVENTS_PER_TYPE) -> list[DugoutEvent]:
    """Keep at most ``n`` events of each type, preserving order (best-first)."""
    seen: dict = defaultdict(int)
    kept: list[DugoutEvent] = []
    for e in events:
        if seen[e.type] < n:
            kept.append(e)
            seen[e.type] += 1
    return kept


def get_dugout_events(db: Session, user_id: int) -> list[DugoutEvent]:
    leagues = get_user_leagues(db, user_id)
    if not leagues:
        return []

    # Load all dismissals for this user upfront
    dismissals = db.query(DugoutDismissal).filter(DugoutDismissal.user_id == user_id).all()
    dismissed_keys = {
        (d.type, d.league_id, d.match_id if d.match_id else 0, d.subject_username)
        for d in dismissals
    }

    league_ids = [l.id for l in leagues]
    league_map = {l.id: l for l in leagues}

    # Batch-load all league members across all user's leagues
    all_members = (
        db.query(LeagueMember)
        .filter(LeagueMember.league_id.in_(league_ids))
        .all()
    )
    # Map league_id -> list of user_ids
    members_by_league: dict[int, list[int]] = defaultdict(list)
    for m in all_members:
        members_by_league[m.league_id].append(m.user_id)

    # Sort leagues by member count descending to prioritize largest leagues for event caps
    leagues.sort(key=lambda l: len(members_by_league[l.id]), reverse=True)

    all_member_ids = list({m.user_id for m in all_members})

    # For each league, find the most recent locked match (start_time < now)
    # that has at least one prediction from a league member
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Batch-load all predictions for all member+match combinations in one query
    # We'll filter by locked matches
    locked_match_ids_by_league: dict[int, int | None] = {}
    for league_id, member_ids in members_by_league.items():
        # The locked match must belong to the league's own sport. Members often
        # play both cricket and football, and without this filter the globally
        # most-recent match (e.g. a World Cup fixture) would leak into a cricket
        # league's dugout — producing nonsense agreement/contrarian events.
        league_sport = getattr(league_map.get(league_id), "sport", None)
        query = (
            db.query(Prediction.match_id)
            .join(Match, Prediction.match_id == Match.id)
            .join(Tournament, Match.tournament_id == Tournament.id)
            .filter(
                Prediction.user_id.in_(member_ids),
                Match.start_time < now,
            )
        )
        if league_sport:
            query = query.filter(Tournament.sport == league_sport)
        result = query.order_by(Match.start_time.desc()).first()
        locked_match_ids_by_league[league_id] = result[0] if result else None

    relevant_match_ids = list({mid for mid in locked_match_ids_by_league.values() if mid})
    if not relevant_match_ids:
        # No locked matches with predictions → only rank shifts + match verdicts possible
        events: list[DugoutEvent] = []
        events.extend(_tournament_picks_events(db, user_id, leagues))
        events.extend(_match_verdict_events(db, user_id, leagues))
        events.extend(_rank_shift_events(db, user_id, leagues, members_by_league))
        events = [
            e for e in events
            if (e.type, e.league_id, e.match_id if e.match_id else 0, e.username) not in dismissed_keys
        ]
        return _limit_per_type(events)

    # Batch-load all predictions for relevant matches across all members
    all_predictions = (
        db.query(Prediction)
        .filter(
            Prediction.match_id.in_(relevant_match_ids),
            Prediction.user_id.in_(all_member_ids),
        )
        .all()
    )

    # Batch-load users for display names
    user_objs = db.query(User).filter(User.id.in_(all_member_ids)).all()
    user_map = {u.id: u for u in user_objs}

    # Organise predictions: match_id -> user_id -> Prediction
    preds_by_match_user: dict[int, dict[int, Prediction]] = defaultdict(dict)
    for p in all_predictions:
        preds_by_match_user[p.match_id][p.user_id] = p

    # Locked matches (with sport + team ids), for sport-aware comparisons
    matches_by_id: dict[int, Match] = {
        m.id: m for m in db.query(Match).filter(Match.id.in_(relevant_match_ids)).all()
    }

    events = []
    events.extend(_tournament_picks_events(db, user_id, leagues))
    events.extend(_match_verdict_events(db, user_id, leagues))
    events.extend(_contrarian_events(db, user_id, leagues, members_by_league, locked_match_ids_by_league, preds_by_match_user, user_map, league_map, matches_by_id))
    events.extend(_agreement_events(user_id, leagues, members_by_league, locked_match_ids_by_league, preds_by_match_user, user_map, league_map, matches_by_id))
    events.extend(_streak_events(db, user_id, leagues, members_by_league, all_member_ids, user_map, league_map))
    events.extend(_rank_shift_events(db, user_id, leagues, members_by_league))

    # Filter dismissed events
    events = [
        e for e in events
        if (e.type, e.league_id, e.match_id if e.match_id else 0, e.username) not in dismissed_keys
    ]

    # Time-sensitive picks CTA surfaces first, then verdicts (freshest result),
    # rank shifts, then social signals.
    priority = {
        DugoutEventType.TOURNAMENT_PICKS: 0,
        DugoutEventType.MATCH_VERDICT: 1,
        DugoutEventType.RANK_SHIFT: 2,
        DugoutEventType.CONTRARIAN: 3,
        DugoutEventType.AGREEMENT: 4,
        DugoutEventType.STREAK: 5,
    }
    events = _limit_per_type(events)
    events.sort(key=lambda e: priority[e.type])
    return events


def _tournament_picks_events(
    db: Session,
    user_id: int,
    leagues: list,
) -> list[DugoutEvent]:
    """A single CTA to make/edit tournament-level picks while the window is open.

    Football picks (semi-finalists + golden awards) stay open until the first
    knockout match kicks off. We surface at most one card — the most urgent
    (soonest-closing) open football tournament — to anyone with a league. A
    football league is preferred as the dismissal anchor, but the card is not
    league-specific (it never shows the league name), so any league works.
    """
    from app.models import Tournament
    from app.services.tournament_picks import get_group_stage_deadline, get_tournament_picks

    if not leagues:
        return []
    # leagues are pre-sorted by member count desc; prefer a football league as anchor.
    league = next((l for l in leagues if l.sport == "football"), leagues[0])

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    now = datetime.now(timezone.utc)
    tournaments = db.query(Tournament).filter(Tournament.sport == "football").all()

    # Keep only tournaments whose picks window is still open, then pick the most
    # urgent one (a real deadline outranks an undated/not-yet-seeded window).
    open_tournaments = []
    for t in tournaments:
        deadline = get_group_stage_deadline(db, t.id)
        if deadline is not None and now >= deadline:
            continue  # group stage over — picks already locked
        open_tournaments.append((t, deadline))
    if not open_tournaments:
        return []

    far_future = datetime.max.replace(tzinfo=timezone.utc)
    target, deadline = min(open_tournaments, key=lambda td: td[1] or far_future)

    pick = get_tournament_picks(db, user_id, target.id)
    has_picks = bool(
        pick
        and (
            any([pick.top4_team1_id, pick.top4_team2_id, pick.top4_team3_id, pick.top4_team4_id])
            or pick.golden_ball_player_id
            or pick.golden_boot_player_id
            or pick.golden_glove_player_id
        )
    )

    return [
        DugoutEvent(
            type=DugoutEventType.TOURNAMENT_PICKS,
            league_name=league.name,
            league_id=league.id,
            match_id=None,
            username=user.username,
            display_name=user.display_name,
            is_me=True,
            tournament_id=target.id,
            tournament_name=target.name,
            picks_lock_at=deadline,
            has_picks=has_picks,
        )
    ]


def _match_verdict_events(
    db: Session,
    user_id: int,
    leagues: list,
) -> list[DugoutEvent]:
    """One verdict per (league, recent completed match) pair, capped per the constants above."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=VERDICT_WINDOW_DAYS)

    # Recent completed matches, across all tournaments. We don't filter on
    # result_winner_id here: football matches can end in a draw (no winner) yet
    # still have a verdict. get_match_verdict() gates per-sport on whether the
    # result is actually recorded, returning None for unscored matches.
    recent_matches = (
        db.query(Match.id, Match.start_time)
        .filter(
            Match.status == MatchStatus.COMPLETED,
            Match.start_time >= cutoff,
        )
        .order_by(Match.start_time.desc())
        .all()
    )
    if not recent_matches:
        return []

    events: list[DugoutEvent] = []
    for league in leagues:
        if len(events) >= VERDICT_MAX_TOTAL:
            break
        per_league = 0
        for match_id, _start in recent_matches:
            if per_league >= VERDICT_MATCHES_PER_LEAGUE:
                break
            if len(events) >= VERDICT_MAX_TOTAL:
                break
            verdict = get_match_verdict(db, league.id, match_id, user_id)
            if verdict is None:
                continue
            events.append(verdict)
            per_league += 1
    return events


def _called_winner_id(pred: Prediction, match: Match) -> int | None:
    """The team the user predicted to win, per sport. None for a predicted draw
    or an incomplete pick."""
    sport = match.tournament.sport if match.tournament else "cricket"
    if sport == "football":
        fp = getattr(pred, "football", None)
        if fp is None:
            return None
        if fp.advance_winner_id:
            return fp.advance_winner_id
        if fp.team1_goals > fp.team2_goals:
            return match.team_1_id
        if fp.team2_goals > fp.team1_goals:
            return match.team_2_id
        return None  # predicted draw — not a "lone backer"
    return pred.predicted_winner_id


def _contrarian_events(
    db: Session,
    user_id: int,
    leagues: list,
    members_by_league: dict,
    locked_match_ids_by_league: dict,
    preds_by_match_user: dict,
    user_map: dict,
    league_map: dict,
    matches_by_id: dict,
) -> list[DugoutEvent]:
    events = []
    for league in leagues:
        match_id = locked_match_ids_by_league.get(league.id)
        match = matches_by_id.get(match_id) if match_id else None
        if not match:
            continue
        league_member_ids = set(members_by_league[league.id])
        member_preds = {
            uid: pred
            for uid, pred in preds_by_match_user.get(match_id, {}).items()
            if uid in league_member_ids
        }
        if len(member_preds) < 2:
            continue

        # Count how many backed each winner (sport-aware; skip draws / no-pick)
        winner_counts: dict[int, list[int]] = defaultdict(list)
        for uid, pred in member_preds.items():
            wid = _called_winner_id(pred, match)
            if wid is not None:
                winner_counts[wid].append(uid)

        lone_picks = [(team_id, uids[0]) for team_id, uids in winner_counts.items() if len(uids) == 1]
        if not lone_picks:
            continue

        # Batch-load teams
        from app.models.team import Team
        team_ids = [t for t, _ in lone_picks]
        teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        team_short_map = {t.id: t.short_name for t in teams}

        count = 0
        for team_id, lone_uid in lone_picks:
            if count >= 2:
                break
            user = user_map.get(lone_uid)
            if not user:
                continue
            events.append(DugoutEvent(
                type=DugoutEventType.CONTRARIAN,
                league_name=league.name,
                league_id=league.id,
                match_id=match_id,
                username=user.username,
                display_name=user.display_name,
                is_me=(lone_uid == user_id),
                team_short_name=team_short_map.get(team_id),
            ))
            count += 1

    return events


def _agreement_events(
    user_id: int,
    leagues: list,
    members_by_league: dict,
    locked_match_ids_by_league: dict,
    preds_by_match_user: dict,
    user_map: dict,
    league_map: dict,
    matches_by_id: dict,
) -> list[DugoutEvent]:
    events = []
    for league in leagues:
        match_id = locked_match_ids_by_league.get(league.id)
        match = matches_by_id.get(match_id) if match_id else None
        if not match:
            continue
        league_member_ids = set(members_by_league[league.id])
        member_preds = {
            uid: pred
            for uid, pred in preds_by_match_user.get(match_id, {}).items()
            if uid in league_member_ids
        }
        my_pred = member_preds.get(user_id)
        if not my_pred:
            continue

        count = 0
        for uid, pred in member_preds.items():
            if count >= 2:
                break
            if uid == user_id:
                continue
            agreement, total = _count_agreement(my_pred, pred, match)
            # Surface only strong overlaps: 4/6 (cricket) or 3/4 (football).
            if agreement >= total - 2 and agreement >= 3:
                user = user_map.get(uid)
                if not user:
                    continue
                events.append(DugoutEvent(
                    type=DugoutEventType.AGREEMENT,
                    league_name=league.name,
                    league_id=league.id,
                    match_id=match_id,
                    username=user.username,
                    display_name=user.display_name,
                    is_me=False,
                    agreement_count=agreement,
                    agreement_total=total,
                ))
                count += 1

    return events


def _count_agreement(p1: Prediction, p2: Prediction, match: Match) -> tuple[int, int]:
    """(agreed categories, total categories) between two predictions, sport-aware.
    Never counts two empty/null fields as agreement."""
    sport = match.tournament.sport if match.tournament else "cricket"
    if sport == "football":
        fp1, fp2 = getattr(p1, "football", None), getattr(p2, "football", None)
        if fp1 is None or fp2 is None:
            return 0, 4
        agree = 0
        if (fp1.team1_goals, fp1.team2_goals) == (fp2.team1_goals, fp2.team2_goals):
            agree += 1
        picks1 = {fp1.player_pick_1_id, fp1.player_pick_2_id, fp1.player_pick_3_id} - {None}
        picks2 = {fp2.player_pick_1_id, fp2.player_pick_2_id, fp2.player_pick_3_id} - {None}
        agree += len(picks1 & picks2)
        return agree, 4

    fields = [
        "predicted_winner_id",
        "predicted_most_runs_team1_player_id",
        "predicted_most_runs_team2_player_id",
        "predicted_most_wickets_team1_player_id",
        "predicted_most_wickets_team2_player_id",
        "predicted_pom_player_id",
    ]
    agree = sum(
        1 for f in fields
        if getattr(p1, f) is not None and getattr(p1, f) == getattr(p2, f)
    )
    return agree, 6


def _streak_events(
    db: Session,
    user_id: int,
    leagues: list,
    members_by_league: dict,
    all_member_ids: list,
    user_map: dict,
    league_map: dict,
) -> list[DugoutEvent]:
    # Batch-load all processed predictions ordered by match start_time desc
    processed_preds = (
        db.query(Prediction, Match)
        .join(Match, Prediction.match_id == Match.id)
        .filter(
            Prediction.user_id.in_(all_member_ids),
            Prediction.is_processed == True,
            Match.result_winner_id != None,
        )
        .order_by(Prediction.user_id, Match.start_time.desc())
        .all()
    )

    # Group by user_id and compute streak
    preds_by_user: dict[int, list] = defaultdict(list)
    for pred, match in processed_preds:
        preds_by_user[pred.user_id].append((pred, match))

    def compute_streak(preds_matches: list) -> int:
        streak = 0
        for pred, match in preds_matches:
            if pred.predicted_winner_id == match.result_winner_id:
                streak += 1
            else:
                break
        return streak

    streaks = {uid: compute_streak(pms) for uid, pms in preds_by_user.items()}

    events = []
    for league in leagues:
        member_ids = members_by_league[league.id]
        # Find top streak in league (>= 3), emit one per league
        best_uid = None
        best_streak = 2  # must exceed this
        for uid in member_ids:
            s = streaks.get(uid, 0)
            if s > best_streak:
                best_streak = s
                best_uid = uid

        if best_uid is not None:
            user = user_map.get(best_uid)
            if user:
                events.append(DugoutEvent(
                    type=DugoutEventType.STREAK,
                    league_name=league.name,
                    league_id=league.id,
                    username=user.username,
                    display_name=user.display_name,
                    is_me=(best_uid == user_id),
                    streak_count=best_streak,
                ))

    return events


def _rank_shift_events(
    db: Session,
    user_id: int,
    leagues: list,
    members_by_league: dict,
) -> list[DugoutEvent]:
    events = []
    for league in leagues:
        member_ids = members_by_league[league.id]
        if user_id not in member_ids:
            continue

        standings = _compute_standings(db, league.id)
        current_rank_map = dict(standings)
        current_rank = current_rank_map.get(user_id)
        if current_rank is None:
            continue

        prev_member = (
            db.query(LeagueMember)
            .filter(LeagueMember.league_id == league.id, LeagueMember.user_id == user_id)
            .first()
        )
        prev_rank = prev_member.prev_rank if prev_member else None
        if prev_rank is None or prev_rank == current_rank:
            continue

        rank_delta = prev_rank - current_rank  # positive = moved up
        # Load current user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            continue

        events.append(DugoutEvent(
            type=DugoutEventType.RANK_SHIFT,
            league_name=league.name,
            league_id=league.id,
            username=user.username,
            display_name=user.display_name,
            is_me=True,
            rank=current_rank,
            rank_delta=rank_delta,
        ))

    return events
