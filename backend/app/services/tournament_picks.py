from sqlalchemy.orm import Session

from app.models import Tournament, TournamentPick, Team, Player, Match

# Points constants
TOP4_POINTS_W1 = 25
TOP4_POINTS_W2 = 12  # half of 25, rounded down
PLAYER_POINTS_W1 = 50
PLAYER_POINTS_W2 = 25  # half of 50


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
    best_batsman_player_id: int | None,
    best_bowler_player_id: int | None,
) -> TournamentPick:
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise ValueError("Tournament not found")

    if tournament.picks_window not in ("open", "open2"):
        raise ValueError(f"Picks are not open. Current window: {tournament.picks_window}")

    is_window2 = tournament.picks_window == "open2"

    # Normalize top4 list (pad to 4)
    team_ids = (top4_team_ids + [None, None, None, None])[:4]

    pick = get_tournament_picks(db, user_id, tournament_id)
    if pick:
        pick.top4_team1_id = team_ids[0]
        pick.top4_team2_id = team_ids[1]
        pick.top4_team3_id = team_ids[2]
        pick.top4_team4_id = team_ids[3]
        pick.best_batsman_player_id = best_batsman_player_id
        pick.best_bowler_player_id = best_bowler_player_id
        pick.is_window2 = is_window2
        pick.is_processed = False
    else:
        pick = TournamentPick(
            user_id=user_id,
            tournament_id=tournament_id,
            top4_team1_id=team_ids[0],
            top4_team2_id=team_ids[1],
            top4_team3_id=team_ids[2],
            top4_team4_id=team_ids[3],
            best_batsman_player_id=best_batsman_player_id,
            best_bowler_player_id=best_bowler_player_id,
            is_window2=is_window2,
            is_processed=False,
        )
        db.add(pick)

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

    for pick in picks:
        top4_pts = TOP4_POINTS_W2 if pick.is_window2 else TOP4_POINTS_W1
        player_pts = PLAYER_POINTS_W2 if pick.is_window2 else PLAYER_POINTS_W1

        points = 0
        pick_top4_ids = {
            pick.top4_team1_id,
            pick.top4_team2_id,
            pick.top4_team3_id,
            pick.top4_team4_id,
        } - {None}

        correct_top4 = len(pick_top4_ids & result_top4_ids)
        points += correct_top4 * top4_pts

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
