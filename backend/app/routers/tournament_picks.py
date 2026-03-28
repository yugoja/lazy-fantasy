from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tournament, User
from app.schemas.tournament_picks import (
    TournamentPicksSubmit,
    TournamentPicksResponse,
    TeamPickOption,
    PlayerPickOption,
)
from app.services.auth import get_current_user
from app.services.tournament_picks import (
    get_tournament_picks,
    upsert_tournament_picks,
    get_tournament_teams,
    get_tournament_players,
)

router = APIRouter(prefix="/tournaments", tags=["tournament-picks"])


@router.get("/", response_model=list[dict])
async def list_tournaments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all tournaments."""
    tournaments = db.query(Tournament).order_by(Tournament.start_date.desc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "start_date": t.start_date.isoformat(),
            "end_date": t.end_date.isoformat(),
            "picks_window": t.picks_window,
        }
        for t in tournaments
    ]


@router.get("/{tournament_id}/picks", response_model=TournamentPicksResponse)
async def get_my_picks(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's tournament picks and window state."""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")

    pick = get_tournament_picks(db, current_user.id, tournament_id)

    if pick:
        top4 = [pick.top4_team1_id, pick.top4_team2_id, pick.top4_team3_id, pick.top4_team4_id]
        return TournamentPicksResponse(
            tournament_id=tournament.id,
            tournament_name=tournament.name,
            picks_window=tournament.picks_window,
            top4_team_ids=top4,
            best_batsman_player_id=pick.best_batsman_player_id,
            best_bowler_player_id=pick.best_bowler_player_id,
            points_earned=pick.points_earned,
            is_window2=pick.is_window2,
            is_processed=pick.is_processed,
        )

    return TournamentPicksResponse(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        picks_window=tournament.picks_window,
        top4_team_ids=[None, None, None, None],
        best_batsman_player_id=None,
        best_bowler_player_id=None,
        points_earned=0,
        is_window2=False,
        is_processed=False,
    )


@router.post("/{tournament_id}/picks", response_model=TournamentPicksResponse)
async def submit_picks(
    tournament_id: int,
    data: TournamentPicksSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit or update tournament picks (only when window is open or open2)."""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")

    if tournament.picks_window not in ("open", "open2"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Picks window is currently '{tournament.picks_window}'. Picks are not accepted.",
        )

    if len(data.top4_team_ids) > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can select at most 4 teams for Top 4.",
        )

    try:
        pick = upsert_tournament_picks(
            db=db,
            user_id=current_user.id,
            tournament_id=tournament_id,
            top4_team_ids=data.top4_team_ids,
            best_batsman_player_id=data.best_batsman_player_id,
            best_bowler_player_id=data.best_bowler_player_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    top4 = [pick.top4_team1_id, pick.top4_team2_id, pick.top4_team3_id, pick.top4_team4_id]
    return TournamentPicksResponse(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        picks_window=tournament.picks_window,
        top4_team_ids=top4,
        best_batsman_player_id=pick.best_batsman_player_id,
        best_bowler_player_id=pick.best_bowler_player_id,
        points_earned=pick.points_earned,
        is_window2=pick.is_window2,
        is_processed=pick.is_processed,
    )


@router.get("/{tournament_id}/teams", response_model=list[TeamPickOption])
async def list_teams(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all teams participating in the tournament."""
    teams = get_tournament_teams(db, tournament_id)
    return [TeamPickOption.model_validate(t) for t in teams]


@router.get("/{tournament_id}/players", response_model=list[PlayerPickOption])
async def list_players(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all players in the tournament for pick dropdowns."""
    players = get_tournament_players(db, tournament_id)
    result = []
    for p in players:
        result.append(
            PlayerPickOption(
                id=p.id,
                name=p.name,
                role=p.role,
                team_id=p.team_id,
                team_name=p.team.name if p.team else None,
            )
        )
    return result
