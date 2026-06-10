from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Tournament, TournamentPick, Team, Player, Match
from app.services.scoring_football import KNOCKOUT_STAGES

# Cricket points constants
TOP4_POINTS_W1 = 25
TOP4_POINTS_W2 = 12  # half of 25, rounded down
PLAYER_POINTS_W1 = 50
PLAYER_POINTS_W2 = 25  # half of 50

# Football tournament-pick points
FOOTBALL_SF_POINTS = 25  # per correct semi-finalist (max 4 -> 100)
FOOTBALL_AWARD_POINTS = 50  # golden ball / boot / glove, each


def get_group_stage_deadline(db: Session, tournament_id: int) -> datetime | None:
    """Kickoff of the earliest knockout match — the moment football picks lock.

    Returns None if no knockout matches are seeded yet (picks stay open).
    """
    first_ko = (
        db.query(Match)
        .filter(
            Match.tournament_id == tournament_id,
            Match.stage.in_(KNOCKOUT_STAGES),
        )
        .order_by(Match.start_time.asc())
        .first()
    )
    if not first_ko or first_ko.start_time is None:
        return None
    deadline = first_ko.start_time
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return deadline


def is_picks_open(db: Session, tournament: Tournament) -> tuple[bool, datetime | None]:
    """Whether picks can currently be submitted, and (for football) when they lock.

    Football: open until the first knockout kicks off (schedule-derived).
    Cricket: gated by the admin-controlled picks_window.
    """
    if tournament.sport == "football":
        deadline = get_group_stage_deadline(db, tournament.id)
        if deadline is None:
            return True, None
        return datetime.now(timezone.utc) < deadline, deadline
    return tournament.picks_window in ("open", "open2"), None


def get_tournament_picks(db: Session, user_id: int, tournament_id: int) -> TournamentPick | None:
    return (
        db.query(TournamentPick)
        .filter(
            TournamentPick.user_id == user_id,
            TournamentPick.tournament_id == tournament_id,
        )
        .first()
    )


def upsert_tournament_picks(
    db: Session,
    user_id: int,
    tournament_id: int,
    top4_team_ids: list[int],
    best_batsman_player_id: int | None = None,
    best_bowler_player_id: int | None = None,
    golden_ball_player_id: int | None = None,
    golden_boot_player_id: int | None = None,
    golden_glove_player_id: int | None = None,
) -> TournamentPick:
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise ValueError("Tournament not found")

    open_now, _ = is_picks_open(db, tournament)
    if not open_now:
        raise ValueError("Picks are closed for this tournament.")

    # Football uses a single full-points window; cricket may reopen at half points.
    is_window2 = tournament.sport != "football" and tournament.picks_window == "open2"

    # Normalize top4 list (pad to 4)
    team_ids = (top4_team_ids + [None, None, None, None])[:4]

    pick = get_tournament_picks(db, user_id, tournament_id)
    if not pick:
        pick = TournamentPick(user_id=user_id, tournament_id=tournament_id)
        db.add(pick)

    pick.top4_team1_id = team_ids[0]
    pick.top4_team2_id = team_ids[1]
    pick.top4_team3_id = team_ids[2]
    pick.top4_team4_id = team_ids[3]
    pick.best_batsman_player_id = best_batsman_player_id
    pick.best_bowler_player_id = best_bowler_player_id
    pick.golden_ball_player_id = golden_ball_player_id
    pick.golden_boot_player_id = golden_boot_player_id
    pick.golden_glove_player_id = golden_glove_player_id
    pick.is_window2 = is_window2
    pick.is_processed = False

    db.commit()
    db.refresh(pick)
    return pick


def get_tournament_teams(db: Session, tournament_id: int) -> list[Team]:
    """All unique teams participating in the tournament's matches."""
    matches = db.query(Match).filter(Match.tournament_id == tournament_id).all()
    team_ids = set()
    for m in matches:
        team_ids.add(m.team_1_id)
        team_ids.add(m.team_2_id)
    if not team_ids:
        return []
    return db.query(Team).filter(Team.id.in_(team_ids)).order_by(Team.name).all()


def get_tournament_players(db: Session, tournament_id: int) -> list[Player]:
    """All players from teams in the tournament."""
    teams = get_tournament_teams(db, tournament_id)
    team_ids = [t.id for t in teams]
    if not team_ids:
        return []
    return (
        db.query(Player)
        .filter(Player.team_id.in_(team_ids))
        .order_by(Player.name)
        .all()
    )


def score_tournament_picks(db: Session, tournament_id: int) -> int:
    """
    Compute and save points for all unprocessed picks after results are set.
    Returns number of picks scored.
    """
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise ValueError("Tournament not found")

    result_top4_ids = {
        tournament.result_top4_team1_id,
        tournament.result_top4_team2_id,
        tournament.result_top4_team3_id,
        tournament.result_top4_team4_id,
    } - {None}

    picks = (
        db.query(TournamentPick)
        .filter(
            TournamentPick.tournament_id == tournament_id,
            TournamentPick.is_processed == False,
        )
        .all()
    )

    is_football = tournament.sport == "football"

    for pick in picks:
        pick_top4_ids = {
            pick.top4_team1_id,
            pick.top4_team2_id,
            pick.top4_team3_id,
            pick.top4_team4_id,
        } - {None}
        correct_top4 = len(pick_top4_ids & result_top4_ids)

        if is_football:
            points = correct_top4 * FOOTBALL_SF_POINTS
            for pick_id, result_id in (
                (pick.golden_ball_player_id, tournament.result_golden_ball_player_id),
                (pick.golden_boot_player_id, tournament.result_golden_boot_player_id),
                (pick.golden_glove_player_id, tournament.result_golden_glove_player_id),
            ):
                if result_id and pick_id == result_id:
                    points += FOOTBALL_AWARD_POINTS
        else:
            top4_pts = TOP4_POINTS_W2 if pick.is_window2 else TOP4_POINTS_W1
            player_pts = PLAYER_POINTS_W2 if pick.is_window2 else PLAYER_POINTS_W1
            points = correct_top4 * top4_pts
            if (
                tournament.result_best_batsman_player_id
                and pick.best_batsman_player_id == tournament.result_best_batsman_player_id
            ):
                points += player_pts
            if (
                tournament.result_best_bowler_player_id
                and pick.best_bowler_player_id == tournament.result_best_bowler_player_id
            ):
                points += player_pts

        pick.points_earned = points
        pick.is_processed = True

    db.commit()
    return len(picks)
