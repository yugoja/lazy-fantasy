from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import Match, MatchStatus, Player, Team


def get_upcoming_matches(
    db: Session, 
    tournament_id: int | None = None,
    include_all: bool = False
) -> list[Match]:
    """
    Get matches. By default returns only upcoming (scheduled) matches.
    If include_all is True, returns all matches.
    """
    query = db.query(Match)
    
    if tournament_id:
        query = query.filter(Match.tournament_id == tournament_id)
    
    if not include_all:
        query = query.filter(Match.status == MatchStatus.SCHEDULED)
    
    return query.order_by(Match.start_time).all()


def get_match_by_id(db: Session, match_id: int) -> Match | None:
    """Get a match by ID."""
    return db.query(Match).filter(Match.id == match_id).first()


def get_team_by_id(db: Session, team_id: int) -> Team | None:
    """Get a team by ID."""
    return db.query(Team).filter(Team.id == team_id).first()


def get_players_by_team(db: Session, team_id: int) -> list[Player]:
    """Get all players for a team."""
    return db.query(Player).filter(Player.team_id == team_id).all()


def get_match_players(db: Session, match_id: int) -> tuple[list[Player], list[Player]] | None:
    """
    Get all players from both teams in a match.
    Returns (team_1_players, team_2_players) or None if match not found.
    """
    match = get_match_by_id(db, match_id)
    if not match:
        return None
    
    team_1_players = get_players_by_team(db, match.team_1_id)
    team_2_players = get_players_by_team(db, match.team_2_id)
    
    return team_1_players, team_2_players
