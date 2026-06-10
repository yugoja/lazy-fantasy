"""Football tournament-level picks: schedule-derived locking + award scoring."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Tournament, Team, Player, Match, TournamentPick
from app.models.match import MatchStatus
from app.services.tournament_picks import (
    get_group_stage_deadline,
    is_picks_open,
    upsert_tournament_picks,
    score_tournament_picks,
    FOOTBALL_SF_POINTS,
    FOOTBALL_AWARD_POINTS,
)


@pytest.fixture
def wc(db_session):
    """A small football tournament: 6 teams, a few players, group + knockout matches."""
    t = Tournament(
        name="WC Test",
        sport="football",
        start_date=datetime.now(timezone.utc).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=30)).date(),
    )
    db_session.add(t)
    db_session.commit()

    teams = [Team(name=f"Team {i}", short_name=f"T{i}", sport="football") for i in range(6)]
    db_session.add_all(teams)
    db_session.commit()

    players = []
    for tm in teams:
        gk = Player(name=f"{tm.short_name} GK", team_id=tm.id, role="Goalkeeper")
        fw = Player(name=f"{tm.short_name} FW", team_id=tm.id, role="Forward")
        db_session.add_all([gk, fw])
        players.extend([gk, fw])
    db_session.commit()

    now = datetime.now(timezone.utc)
    # Group matches
    db_session.add(Match(tournament_id=t.id, team_1_id=teams[0].id, team_2_id=teams[1].id,
                         start_time=now + timedelta(days=1), status=MatchStatus.SCHEDULED, stage="GROUP"))
    # Knockout matches — earliest one defines the lock deadline
    first_ko = now + timedelta(days=10)
    db_session.add(Match(tournament_id=t.id, team_1_id=teams[0].id, team_2_id=teams[2].id,
                         start_time=first_ko + timedelta(days=2), status=MatchStatus.SCHEDULED, stage="QF"))
    db_session.add(Match(tournament_id=t.id, team_1_id=teams[1].id, team_2_id=teams[3].id,
                         start_time=first_ko, status=MatchStatus.SCHEDULED, stage="R16"))
    db_session.commit()
    db_session.refresh(t)
    return t, teams, players, first_ko


def test_deadline_is_earliest_knockout(db_session, wc):
    t, _teams, _players, first_ko = wc
    deadline = get_group_stage_deadline(db_session, t.id)
    assert deadline is not None
    assert abs((deadline - first_ko).total_seconds()) < 1


def test_picks_open_before_deadline_closed_after(db_session, wc):
    t, _teams, _players, _first_ko = wc
    open_now, locks_at = is_picks_open(db_session, t)
    assert open_now is True
    assert locks_at is not None

    # Move the earliest knockout into the past -> picks close.
    earliest = (
        db_session.query(Match)
        .filter(Match.tournament_id == t.id, Match.stage == "R16")
        .first()
    )
    earliest.start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()
    open_now, _ = is_picks_open(db_session, t)
    assert open_now is False


def test_upsert_rejected_when_closed(db_session, wc, test_user):
    t, teams, _players, _first_ko = wc
    earliest = (
        db_session.query(Match)
        .filter(Match.tournament_id == t.id, Match.stage == "R16")
        .first()
    )
    earliest.start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    with pytest.raises(ValueError):
        upsert_tournament_picks(
            db_session, user_id=test_user.id, tournament_id=t.id,
            top4_team_ids=[teams[0].id, teams[1].id, teams[2].id, teams[3].id],
        )


def test_score_football_awards(db_session, wc, test_user):
    t, teams, players, _first_ko = wc
    gk0 = next(p for p in players if p.team_id == teams[0].id and p.role == "Goalkeeper")
    fw0 = next(p for p in players if p.team_id == teams[0].id and p.role == "Forward")
    fw1 = next(p for p in players if p.team_id == teams[1].id and p.role == "Forward")

    # User picks 4 semis (3 will be correct) and 3 awards (boot + glove correct, ball wrong).
    upsert_tournament_picks(
        db_session, user_id=test_user.id, tournament_id=t.id,
        top4_team_ids=[teams[0].id, teams[1].id, teams[2].id, teams[5].id],
        golden_boot_player_id=fw0.id,
        golden_ball_player_id=fw1.id,
        golden_glove_player_id=gk0.id,
    )

    # Results: semis = teams 0,1,2,3 ; boot=fw0 (correct), ball=fw0 (user said fw1 -> wrong), glove=gk0 (correct)
    t.result_top4_team1_id = teams[0].id
    t.result_top4_team2_id = teams[1].id
    t.result_top4_team3_id = teams[2].id
    t.result_top4_team4_id = teams[3].id
    t.result_golden_boot_player_id = fw0.id
    t.result_golden_ball_player_id = fw0.id
    t.result_golden_glove_player_id = gk0.id
    db_session.commit()

    scored = score_tournament_picks(db_session, t.id)
    assert scored == 1

    pick = (
        db_session.query(TournamentPick)
        .filter(TournamentPick.user_id == test_user.id, TournamentPick.tournament_id == t.id)
        .first()
    )
    expected = 3 * FOOTBALL_SF_POINTS + 2 * FOOTBALL_AWARD_POINTS  # 3*25 + 2*50 = 175
    assert pick.points_earned == expected
    assert pick.is_processed is True
