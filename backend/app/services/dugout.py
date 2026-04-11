from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import League, LeagueMember, Match, Prediction, User
from app.models.dugout_dismissal import DugoutDismissal
from app.schemas.dugout import DugoutEvent, DugoutEventType
from app.services.league import _compute_standings, get_user_leagues


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

    all_member_ids = list({m.user_id for m in all_members})

    # For each league, find the most recent locked match (start_time < now)
    # that has at least one prediction from a league member
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Batch-load all predictions for all member+match combinations in one query
    # We'll filter by locked matches
    locked_match_ids_by_league: dict[int, int | None] = {}
    for league_id, member_ids in members_by_league.items():
        result = (
            db.query(Prediction.match_id)
            .join(Match, Prediction.match_id == Match.id)
            .filter(
                Prediction.user_id.in_(member_ids),
                Match.start_time < now,
            )
            .order_by(Match.start_time.desc())
            .first()
        )
        locked_match_ids_by_league[league_id] = result[0] if result else None

    relevant_match_ids = list({mid for mid in locked_match_ids_by_league.values() if mid})
    if not relevant_match_ids:
        # No locked matches with predictions → only rank shifts possible
        events: list[DugoutEvent] = []
        events.extend(_rank_shift_events(db, user_id, leagues, members_by_league))
        events = [
            e for e in events
            if (e.type, e.league_id, e.match_id if e.match_id else 0, e.username) not in dismissed_keys
        ]
        return events[:10]

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

    events = []
    events.extend(_contrarian_events(db, user_id, leagues, members_by_league, locked_match_ids_by_league, preds_by_match_user, user_map, league_map))
    events.extend(_agreement_events(user_id, leagues, members_by_league, locked_match_ids_by_league, preds_by_match_user, user_map, league_map))
    events.extend(_streak_events(db, user_id, leagues, members_by_league, all_member_ids, user_map, league_map))
    events.extend(_rank_shift_events(db, user_id, leagues, members_by_league))

    # Filter dismissed events
    events = [
        e for e in events
        if (e.type, e.league_id, e.match_id if e.match_id else 0, e.username) not in dismissed_keys
    ]

    # Sort: rank_shift first, then contrarian, agreement, streak
    priority = {
        DugoutEventType.RANK_SHIFT: 0,
        DugoutEventType.CONTRARIAN: 1,
        DugoutEventType.AGREEMENT: 2,
        DugoutEventType.STREAK: 3,
    }
    events.sort(key=lambda e: priority[e.type])
    return events[:10]


def _contrarian_events(
    db: Session,
    user_id: int,
    leagues: list,
    members_by_league: dict,
    locked_match_ids_by_league: dict,
    preds_by_match_user: dict,
    user_map: dict,
    league_map: dict,
) -> list[DugoutEvent]:
    events = []
    for league in leagues:
        match_id = locked_match_ids_by_league.get(league.id)
        if not match_id:
            continue
        league_member_ids = set(members_by_league[league.id])
        member_preds = {
            uid: pred
            for uid, pred in preds_by_match_user.get(match_id, {}).items()
            if uid in league_member_ids
        }
        if len(member_preds) < 2:
            continue

        # Count how many picked each winner
        winner_counts: dict[int, list[int]] = defaultdict(list)
        for uid, pred in member_preds.items():
            winner_counts[pred.predicted_winner_id].append(uid)

        # Load team short names for lone picks
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
) -> list[DugoutEvent]:
    events = []
    for league in leagues:
        match_id = locked_match_ids_by_league.get(league.id)
        if not match_id:
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
            agreement = _count_agreement(my_pred, pred)
            if agreement >= 4:
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
                ))
                count += 1

    return events


def _count_agreement(p1: Prediction, p2: Prediction) -> int:
    fields = [
        "predicted_winner_id",
        "predicted_most_runs_team1_player_id",
        "predicted_most_runs_team2_player_id",
        "predicted_most_wickets_team1_player_id",
        "predicted_most_wickets_team2_player_id",
        "predicted_pom_player_id",
    ]
    return sum(1 for f in fields if getattr(p1, f) == getattr(p2, f))


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
