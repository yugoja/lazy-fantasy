from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Match, MatchStatus, Team, Tournament, Player, User, MatchLineup
from app.schemas.admin import MatchCreate, MatchResultCreate, SetLineupRequest
from app.schemas.match import MatchResponse, TeamResponse, PlayerResponse
from app.services.auth import get_current_admin_user
from app.services.league import snapshot_league_ranks
from app.services.scoring import calculate_scores

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/matches/", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
async def create_match(
    match_data: MatchCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new match (Admin only).

    Requires admin privileges to create matches.
    """
    # Validate tournament exists
    tournament = db.query(Tournament).filter(Tournament.id == match_data.tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )
    
    # Validate teams exist
    team_1 = db.query(Team).filter(Team.id == match_data.team_1_id).first()
    team_2 = db.query(Team).filter(Team.id == match_data.team_2_id).first()
    if not team_1 or not team_2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or both teams not found",
        )
    
    if team_1.id == team_2.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team cannot play against itself",
        )
    
    # Ensure start_time is timezone-aware (UTC)
    start_time = match_data.start_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    
    # Create match
    match = Match(
        tournament_id=match_data.tournament_id,
        team_1_id=match_data.team_1_id,
        team_2_id=match_data.team_2_id,
        start_time=start_time,
        status=MatchStatus.SCHEDULED,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    
    return MatchResponse(
        id=match.id,
        tournament_id=match.tournament_id,
        team_1=TeamResponse.model_validate(team_1),
        team_2=TeamResponse.model_validate(team_2),
        start_time=match.start_time,
        status=match.status.value,
    )


@router.post("/matches/{match_id}/result")
async def set_match_result(
    match_id: int,
    result_data: MatchResultCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Set match results and trigger score calculation (Admin only).
    
    This endpoint:
    1. Updates the match with results
    2. Sets match status to COMPLETED
    3. Triggers automatic score calculation for all predictions
    
    Note: In a production app, this should be restricted to admin users.
    """
    # Get match
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )
    
    if match.status == MatchStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match results have already been set",
        )
    
    # Validate winner is one of the match teams
    if result_data.result_winner_id not in [match.team_1_id, match.team_2_id]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Winner must be one of the match teams",
        )
    
    # Validate per-team players
    team1_player_ids = [
        result_data.result_most_runs_team1_player_id,
        result_data.result_most_wickets_team1_player_id,
    ]
    team2_player_ids = [
        result_data.result_most_runs_team2_player_id,
        result_data.result_most_wickets_team2_player_id,
    ]
    pom_player_ids = [result_data.result_pom_player_id]

    valid_team_ids = {match.team_1_id, match.team_2_id}

    for player_id in team1_player_ids:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Player with ID {player_id} not found")
        if player.team_id != match.team_1_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Player {player.name} must belong to {match.team_1.name}")

    for player_id in team2_player_ids:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Player with ID {player_id} not found")
        if player.team_id != match.team_2_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Player {player.name} must belong to {match.team_2.name}")

    for player_id in pom_player_ids:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Player with ID {player_id} not found")
        if player.team_id not in valid_team_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Player {player.name} is not in either team")

    # Update match with results
    match.result_winner_id = result_data.result_winner_id
    match.result_most_runs_team1_player_id = result_data.result_most_runs_team1_player_id
    match.result_most_runs_team2_player_id = result_data.result_most_runs_team2_player_id
    match.result_most_wickets_team1_player_id = result_data.result_most_wickets_team1_player_id
    match.result_most_wickets_team2_player_id = result_data.result_most_wickets_team2_player_id
    match.result_pom_player_id = result_data.result_pom_player_id
    match.status = MatchStatus.COMPLETED
    
    db.commit()

    # Snapshot current ranks before scoring so deltas can be computed afterwards
    snapshot_league_ranks(db, match_id)

    # Calculate scores for all predictions
    predictions_processed = calculate_scores(db, match_id)
    
    return {
        "message": "Match results set successfully",
        "match_id": match_id,
        "status": "COMPLETED",
        "predictions_processed": predictions_processed,
    }


@router.get("/matches")
async def list_all_matches(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    List all matches with their status (Admin only).
    """
    from app.models import Prediction
    
    matches = db.query(Match).order_by(Match.start_time).all()
    
    result = []
    for match in matches:
        prediction_count = db.query(Prediction).filter(Prediction.match_id == match.id).count()
        result.append({
            "id": match.id,
            "tournament_id": match.tournament_id,
            "team_1": {"id": match.team_1.id, "name": match.team_1.name, "short_name": match.team_1.short_name},
            "team_2": {"id": match.team_2.id, "name": match.team_2.name, "short_name": match.team_2.short_name},
            "start_time": match.start_time.isoformat() if match.start_time.tzinfo else match.start_time.isoformat() + "+00:00",
            "status": match.status.value,
            "prediction_count": prediction_count,
        })
    
    return result


@router.get("/matches/{match_id}/predictions")
async def get_match_predictions(
    match_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get all predictions for a specific match (Admin only).
    """
    from app.models import Prediction
    
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )
    
    predictions = db.query(Prediction).filter(Prediction.match_id == match_id).all()
    
    result = []
    for pred in predictions:
        user = db.query(User).filter(User.id == pred.user_id).first()
        
        # Get player names
        winner_team = db.query(Team).filter(Team.id == pred.predicted_winner_id).first()
        runs_t1 = db.query(Player).filter(Player.id == pred.predicted_most_runs_team1_player_id).first()
        runs_t2 = db.query(Player).filter(Player.id == pred.predicted_most_runs_team2_player_id).first()
        wkts_t1 = db.query(Player).filter(Player.id == pred.predicted_most_wickets_team1_player_id).first()
        wkts_t2 = db.query(Player).filter(Player.id == pred.predicted_most_wickets_team2_player_id).first()
        pom_player = db.query(Player).filter(Player.id == pred.predicted_pom_player_id).first()

        result.append({
            "id": pred.id,
            "user_id": pred.user_id,
            "username": user.username if user else "Unknown",
            "predicted_winner": winner_team.name if winner_team else "Unknown",
            "predicted_most_runs_team1": runs_t1.name if runs_t1 else "Unknown",
            "predicted_most_runs_team2": runs_t2.name if runs_t2 else "Unknown",
            "predicted_most_wickets_team1": wkts_t1.name if wkts_t1 else "Unknown",
            "predicted_most_wickets_team2": wkts_t2.name if wkts_t2 else "Unknown",
            "predicted_pom": pom_player.name if pom_player else "Unknown",
            "points_earned": pred.points_earned,
            "is_processed": pred.is_processed,
        })
    
    return {
        "match_id": match_id,
        "team_1": {"id": match.team_1.id, "name": match.team_1.name, "short_name": match.team_1.short_name},
        "team_2": {"id": match.team_2.id, "name": match.team_2.name, "short_name": match.team_2.short_name},
        "status": match.status.value,
        "predictions": result,
    }


@router.get("/matches/{match_id}/squad")
async def get_match_squad(
    match_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get full squad for both teams in a match (Admin only). Ignores lineup filtering."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    team_1_players = db.query(Player).filter(Player.team_id == match.team_1_id).all()
    team_2_players = db.query(Player).filter(Player.team_id == match.team_2_id).all()

    return {
        "match_id": match_id,
        "team_1": {"id": match.team_1.id, "name": match.team_1.name, "short_name": match.team_1.short_name},
        "team_2": {"id": match.team_2.id, "name": match.team_2.name, "short_name": match.team_2.short_name},
        "team_1_players": [PlayerResponse.model_validate(p).model_dump() for p in team_1_players],
        "team_2_players": [PlayerResponse.model_validate(p).model_dump() for p in team_2_players],
    }


@router.get("/matches/{match_id}/lineup")
async def get_match_lineup(
    match_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get current lineup for a match (Admin only)."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    lineup_rows = db.query(MatchLineup).filter(MatchLineup.match_id == match_id).all()
    player_ids = [row.player_id for row in lineup_rows]

    return {"match_id": match_id, "player_ids": player_ids}


@router.get("/matches/{match_id}/previous-lineup")
async def get_previous_lineup(
    match_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Return player IDs from the most recent prior lineup for each team in this match.
    Used to pre-fill the lineup form so admins only need to make small adjustments.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    # Current squad player IDs (to filter out any stale IDs from old matches)
    current_squad_ids = {
        p.id for p in db.query(Player).filter(
            Player.team_id.in_([match.team_1_id, match.team_2_id])
        ).all()
    }

    def last_lineup_for_team(team_id: int) -> list[int]:
        """Find the most recent completed match for this team that has a lineup."""
        prior_matches = (
            db.query(Match)
            .filter(
                Match.id != match_id,
                Match.start_time < match.start_time,
                (Match.team_1_id == team_id) | (Match.team_2_id == team_id),
            )
            .order_by(Match.start_time.desc())
            .all()
        )
        for m in prior_matches:
            rows = db.query(MatchLineup).filter(MatchLineup.match_id == m.id).all()
            if rows:
                # Return only players that belong to this team
                return [
                    r.player_id for r in rows
                    if r.player_id in current_squad_ids
                    and db.query(Player).filter(Player.id == r.player_id, Player.team_id == team_id).first()
                ]
        return []

    team_1_ids = last_lineup_for_team(match.team_1_id)
    team_2_ids = last_lineup_for_team(match.team_2_id)

    return {
        "match_id": match_id,
        "player_ids": team_1_ids + team_2_ids,
        "team_1_count": len(team_1_ids),
        "team_2_count": len(team_2_ids),
    }


@router.post("/matches/{match_id}/lineup")
async def set_match_lineup(
    match_id: int,
    lineup_data: SetLineupRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Set playing XI for a match (Admin only).

    Accepts 22 player IDs (11 per team). Validates all players belong to
    one of the two match teams and that exactly 11 are selected per team.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    if len(lineup_data.player_ids) != 22:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected 22 players (11 per team), got {len(lineup_data.player_ids)}",
        )

    if len(set(lineup_data.player_ids)) != 22:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate player IDs found",
        )

    valid_team_ids = {match.team_1_id, match.team_2_id}
    players = db.query(Player).filter(Player.id.in_(lineup_data.player_ids)).all()

    if len(players) != 22:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some player IDs are invalid",
        )

    team_1_count = sum(1 for p in players if p.team_id == match.team_1_id)
    team_2_count = sum(1 for p in players if p.team_id == match.team_2_id)
    invalid_count = sum(1 for p in players if p.team_id not in valid_team_ids)

    if invalid_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some players don't belong to either match team",
        )

    if team_1_count != 11 or team_2_count != 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Need exactly 11 per team. Got {team_1_count} for {match.team_1.short_name} and {team_2_count} for {match.team_2.short_name}",
        )

    # Upsert: delete existing, insert new
    db.query(MatchLineup).filter(MatchLineup.match_id == match_id).delete()
    for pid in lineup_data.player_ids:
        db.add(MatchLineup(match_id=match_id, player_id=pid))
    db.commit()

    return {
        "match_id": match_id,
        "player_ids": lineup_data.player_ids,
        "message": "Lineup set successfully",
    }

