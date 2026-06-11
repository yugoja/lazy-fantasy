from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import (
    League,
    LeagueMember,
    Match,
    MatchStatus,
    Player,
    Prediction,
    User,
)
from app.schemas.dugout import (
    DugoutEvent,
    DugoutEventType,
    VerdictHits,
    VerdictRunner,
    VerdictWinner,
)
from app.services.league import _compute_standings
from app.services.scoring import football_score_breakdown
from app.services.scoring_cricket import compute_hits


def _sign(a: int, b: int) -> int:
    return (a > b) - (a < b)


def _football_hits(pred, match) -> dict:
    """Per-category football 'hits' for the verdict card: correct outcome, exact
    scoreline, and which of the three player picks scored."""
    fp = getattr(pred, "football", None)
    fr = match.football_result
    if fp is None or fr is None:
        return {}
    at1 = fr.team1_goals_reg + (fr.team1_goals_et or 0)
    at2 = fr.team2_goals_reg + (fr.team2_goals_et or 0)
    scores = football_score_breakdown(pred, match, fr)["player_scores"]
    return {
        "outcome": _sign(fp.team1_goals, fp.team2_goals) == _sign(at1, at2),
        "exact_score": fp.team1_goals == at1 and fp.team2_goals == at2,
        "pick_1": bool(len(scores) > 0 and (scores[0] or 0) > 0),
        "pick_2": bool(len(scores) > 1 and (scores[1] or 0) > 0),
        "pick_3": bool(len(scores) > 2 and (scores[2] or 0) > 0),
    }


def get_match_verdict(
    db: Session,
    league_id: int,
    match_id: int,
    viewer_user_id: int,
) -> DugoutEvent | None:
    """
    Build a Match Verdict event for a (league, match) pair.

    Returns None if the match isn't completed, no league member predicted,
    or scoring hasn't run yet.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or match.status != MatchStatus.COMPLETED:
        return None

    sport = match.tournament.sport if match.tournament else "cricket"
    if sport == "football":
        # Football can end in a draw (no winner), so gate on the result row, not
        # result_winner_id.
        if match.football_result is None:
            return None
    elif match.result_winner_id is None:
        return None

    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        return None

    member_ids = [
        uid for (uid,) in db.query(LeagueMember.user_id)
        .filter(LeagueMember.league_id == league_id)
        .all()
    ]
    if not member_ids:
        return None

    predictions = (
        db.query(Prediction)
        .filter(
            Prediction.match_id == match_id,
            Prediction.user_id.in_(member_ids),
            Prediction.is_processed == True,
        )
        .all()
    )
    if not predictions:
        return None

    # Per-user data: points + hits
    by_user_points: dict[int, int] = {p.user_id: p.points_earned for p in predictions}
    by_user_hits: dict[int, dict[str, bool]] = {
        p.user_id: (_football_hits(p, match) if sport == "football" else compute_hits(p, match))
        for p in predictions
    }

    # Tier the entries: top score = winners, then runners-up
    sorted_users = sorted(by_user_points.items(), key=lambda x: -x[1])
    top_score = sorted_users[0][1]
    winner_uids = [uid for uid, pts in sorted_users if pts == top_score]
    rest = [(uid, pts) for uid, pts in sorted_users if pts < top_score]

    runner_up_score = rest[0][1] if rest else None
    # Take up to 2 runner-ups (post-tier)
    runner_uids = [uid for uid, _ in rest[:2]]

    # Fetch users for the surfaced rows
    surfaced_ids = list({*winner_uids, *runner_uids, viewer_user_id})
    user_objs = db.query(User).filter(User.id.in_(surfaced_ids)).all()
    user_map = {u.id: u for u in user_objs}

    # Current ranks in the league (post-scoring) + previous ranks
    standings = dict(_compute_standings(db, league_id))  # user_id -> rank
    prev_rank_rows = (
        db.query(LeagueMember.user_id, LeagueMember.prev_rank)
        .filter(LeagueMember.league_id == league_id, LeagueMember.user_id.in_(surfaced_ids))
        .all()
    )
    prev_rank_map = {uid: prev for uid, prev in prev_rank_rows}

    def _to_winner(uid: int) -> VerdictWinner:
        u = user_map[uid]
        return VerdictWinner(
            user_id=uid,
            username=u.username,
            display_name=u.display_name,
            points_earned=by_user_points[uid],
            hits=VerdictHits(**by_user_hits[uid]),
            prev_rank=prev_rank_map.get(uid),
            new_rank=standings.get(uid, 0),
        )

    def _to_runner(uid: int) -> VerdictRunner:
        u = user_map[uid]
        return VerdictRunner(
            user_id=uid,
            username=u.username,
            display_name=u.display_name,
            points_earned=by_user_points[uid],
            prev_rank=prev_rank_map.get(uid),
            new_rank=standings.get(uid, 0),
        )

    winners = [_to_winner(uid) for uid in winner_uids]
    runners_up = [_to_runner(uid) for uid in runner_uids]

    winning_team_short: str | None = None
    losing_team_short: str | None = None
    fb_team1_goals: int | None = None
    fb_team2_goals: int | None = None
    is_draw: bool | None = None

    if sport == "football" and match.football_result is not None:
        # Derive the winner from the scoreline + shootout, not result_winner_id —
        # that column may be unset on legacy rows, and a draw legitimately has no
        # winner.
        fr = match.football_result
        fb_team1_goals = fr.team1_goals_reg + (fr.team1_goals_et or 0)
        fb_team2_goals = fr.team2_goals_reg + (fr.team2_goals_et or 0)
        if fr.shootout_winner_id is not None:
            winner_id = fr.shootout_winner_id
        elif fb_team1_goals > fb_team2_goals:
            winner_id = match.team_1_id
        elif fb_team2_goals > fb_team1_goals:
            winner_id = match.team_2_id
        else:
            winner_id = None
        is_draw = winner_id is None
        if winner_id is not None:
            winning_team_short = match.team_1.short_name if winner_id == match.team_1_id else match.team_2.short_name
            losing_team_short = match.team_2.short_name if winner_id == match.team_1_id else match.team_1.short_name
    elif match.result_winner_id is not None:
        winning_team_short = (
            match.team_1.short_name if match.result_winner_id == match.team_1_id else match.team_2.short_name
        )
        losing_team_short = (
            match.team_2.short_name if match.result_winner_id == match.team_1_id else match.team_1.short_name
        )

    # POM player name (cricket only)
    pom_name: str | None = None
    if sport != "football" and match.result_pom_player_id:
        pom = db.query(Player).filter(Player.id == match.result_pom_player_id).first()
        if pom:
            pom_name = pom.name

    # Human-friendly match label: 1-based index within the tournament by start_time
    match_index = (
        db.query(Match)
        .filter(
            Match.tournament_id == match.tournament_id,
            Match.start_time <= match.start_time,
        )
        .count()
    )
    match_label = f"M{match_index}"

    # Top-line "is_me": frontend uses winners[].user_id == viewer to flip the variant,
    # but DugoutEvent.is_me is also a useful shortcut.
    viewer_is_winner = viewer_user_id in winner_uids
    headline_user = user_map.get(winner_uids[0])

    return DugoutEvent(
        type=DugoutEventType.MATCH_VERDICT,
        league_name=league.name,
        league_id=league_id,
        match_id=match_id,
        username=headline_user.username if headline_user else "",
        display_name=headline_user.display_name if headline_user else None,
        is_me=viewer_is_winner,
        winners=winners,
        runners_up=runners_up,
        pom_player_name=pom_name,
        winning_team_short=winning_team_short,
        losing_team_short=losing_team_short,
        match_label=match_label,
        top_score=top_score,
        runner_up_score=runner_up_score,
        sport=sport,
        team1_short=match.team_1.short_name,
        team2_short=match.team_2.short_name,
        team1_goals=fb_team1_goals,
        team2_goals=fb_team2_goals,
        is_draw=is_draw,
    )
