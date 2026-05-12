"""Unit tests for the Match Verdict service."""
import pytest
from datetime import datetime, timezone

from app.models import LeagueMember, MatchStatus, Player, Prediction
from app.services.auth import get_password_hash
from app.services.match_verdict import get_match_verdict
from app.services.scoring import calculate_scores


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def league_users(db_session):
    """Five extra users to populate a league for tie / spread scenarios."""
    from app.models.user import User
    users = []
    for i in range(5):
        u = User(
            username=f"member{i}",
            email=f"m{i}@example.com",
            hashed_password=get_password_hash("password123"),
            display_name=f"Member {i}",
        )
        db_session.add(u)
        users.append(u)
    db_session.commit()
    for u in users:
        db_session.refresh(u)
    return users


@pytest.fixture
def populated_league(db_session, test_league, league_users):
    """Add all 5 extra users to the existing test_league."""
    for u in league_users:
        db_session.add(LeagueMember(league_id=test_league.id, user_id=u.id))
    db_session.commit()
    return test_league


def _make_pred(
    db, user_id, match, team1_players, team2_players, *,
    correct_winner=True,
    correct_runs_t1=True,
    correct_runs_t2=True,
    correct_wkts_t1=True,
    correct_wkts_t2=True,
    correct_pom=True,
):
    """Build a Prediction whose hits match the requested flags. `match` must have results set."""
    wrong_team_id = match.team_1_id if match.result_winner_id != match.team_1_id else match.team_2_id
    # team1_players[0] is the actual top runs T1 (per `completed_match` fixture);
    # picking any other player will register as a miss.
    p = Prediction(
        user_id=user_id,
        match_id=match.id,
        predicted_winner_id=match.result_winner_id if correct_winner else wrong_team_id,
        predicted_most_runs_team1_player_id=(
            match.result_most_runs_team1_player_id if correct_runs_t1 else team1_players[1].id
        ),
        predicted_most_runs_team2_player_id=(
            match.result_most_runs_team2_player_id if correct_runs_t2 else team2_players[1].id
        ),
        predicted_most_wickets_team1_player_id=(
            match.result_most_wickets_team1_player_id if correct_wkts_t1 else team1_players[5].id
        ),
        predicted_most_wickets_team2_player_id=(
            match.result_most_wickets_team2_player_id if correct_wkts_t2 else team2_players[5].id
        ),
        predicted_pom_player_id=(
            match.result_pom_player_id if correct_pom else team2_players[2].id
        ),
    )
    db.add(p)
    return p


# ============================================================
# Tests
# ============================================================

def test_returns_none_for_incomplete_match(db_session, test_user, test_league, test_match):
    """Non-COMPLETED match yields no verdict."""
    assert test_match.status == MatchStatus.SCHEDULED
    assert get_match_verdict(db_session, test_league.id, test_match.id, test_user.id) is None


def test_returns_none_when_no_one_predicted(db_session, test_user, test_league, completed_match):
    """COMPLETED match with no predictions yields no verdict."""
    assert get_match_verdict(db_session, test_league.id, completed_match.id, test_user.id) is None


def test_solo_flawless_winner(db_session, populated_league, completed_match, test_teams, league_users):
    """One member nails all four categories; others miss everything."""
    team1, team2 = test_teams
    t1p = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2p = db_session.query(Player).filter(Player.team_id == team2.id).all()

    # league_users[0] = flawless; others = 0 pts
    _make_pred(db_session, league_users[0].id, completed_match, t1p, t2p)
    for u in league_users[1:3]:
        _make_pred(
            db_session, u.id, completed_match, t1p, t2p,
            correct_winner=False, correct_runs_t1=False, correct_runs_t2=False,
            correct_wkts_t1=False, correct_wkts_t2=False, correct_pom=False,
        )
    db_session.commit()
    calculate_scores(db_session, completed_match.id)

    verdict = get_match_verdict(db_session, populated_league.id, completed_match.id, league_users[0].id)
    assert verdict is not None
    assert verdict.top_score == 140
    assert len(verdict.winners) == 1
    w = verdict.winners[0]
    assert w.user_id == league_users[0].id
    assert w.points_earned == 140
    assert w.hits.winner and w.hits.runs_t1 and w.hits.runs_t2 and w.hits.wkts_t1 and w.hits.wkts_t2 and w.hits.pom
    # is_me reflects the viewer
    assert verdict.is_me is True
    # Two runner-ups, both 0
    assert len(verdict.runners_up) == 2
    assert all(r.points_earned == 0 for r in verdict.runners_up)
    assert verdict.runner_up_score == 0


def test_two_way_tie(db_session, populated_league, completed_match, test_teams, league_users):
    """Two members tied at 80, third trails."""
    team1, team2 = test_teams
    t1p = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2p = db_session.query(Player).filter(Player.team_id == team2.id).all()

    # Member 0: winner(10) + runs_t1(20) + wkts_t1(20) + pom(50) = 100? need 80
    # 80 paths: pom(50) + winner(10) + runs_t1(20) = 80  OR  4*20 = 80
    # Member 0: pom + winner + runs_t1 = 80
    _make_pred(
        db_session, league_users[0].id, completed_match, t1p, t2p,
        correct_runs_t2=False, correct_wkts_t1=False, correct_wkts_t2=False,
    )
    # Member 1: winner(10) + 4 * 20 — but that's 90. So drop one 20: 70.
    # Need a different combo summing to 80: pom(50) + winner(10) + wkts_t2(20) = 80
    _make_pred(
        db_session, league_users[1].id, completed_match, t1p, t2p,
        correct_runs_t1=False, correct_runs_t2=False, correct_wkts_t1=False,
    )
    # Member 2: winner(10) + 20 = 30 (single 20-pt hit)
    _make_pred(
        db_session, league_users[2].id, completed_match, t1p, t2p,
        correct_runs_t2=False, correct_wkts_t1=False, correct_wkts_t2=False, correct_pom=False,
    )
    db_session.commit()
    calculate_scores(db_session, completed_match.id)

    verdict = get_match_verdict(db_session, populated_league.id, completed_match.id, league_users[2].id)
    assert verdict is not None
    assert verdict.top_score == 80
    assert len(verdict.winners) == 2
    winner_ids = {w.user_id for w in verdict.winners}
    assert winner_ids == {league_users[0].id, league_users[1].id}
    assert len(verdict.runners_up) == 1
    assert verdict.runners_up[0].user_id == league_users[2].id
    assert verdict.runners_up[0].points_earned == 30
    assert verdict.is_me is False  # viewer is the runner-up


def test_three_way_tie(db_session, populated_league, completed_match, test_teams, league_users):
    """Three members tied at 60."""
    team1, team2 = test_teams
    t1p = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2p = db_session.query(Player).filter(Player.team_id == team2.id).all()

    # 60 via winner(10) + pom(50)
    for i in range(3):
        _make_pred(
            db_session, league_users[i].id, completed_match, t1p, t2p,
            correct_runs_t1=False, correct_runs_t2=False,
            correct_wkts_t1=False, correct_wkts_t2=False,
        )
    # 4th at 30
    _make_pred(
        db_session, league_users[3].id, completed_match, t1p, t2p,
        correct_runs_t2=False, correct_wkts_t1=False, correct_wkts_t2=False, correct_pom=False,
    )
    db_session.commit()
    calculate_scores(db_session, completed_match.id)

    verdict = get_match_verdict(db_session, populated_league.id, completed_match.id, league_users[0].id)
    assert verdict is not None
    assert verdict.top_score == 60
    assert len(verdict.winners) == 3
    assert all(w.points_earned == 60 for w in verdict.winners)
    # Runner-up is the 30-pt user
    assert len(verdict.runners_up) == 1
    assert verdict.runners_up[0].points_earned == 30


def test_hit_map_per_category(db_session, populated_league, completed_match, test_teams, league_users):
    """Hits dict tracks each category independently."""
    team1, team2 = test_teams
    t1p = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2p = db_session.query(Player).filter(Player.team_id == team2.id).all()

    _make_pred(
        db_session, league_users[0].id, completed_match, t1p, t2p,
        correct_winner=True, correct_runs_t1=False, correct_runs_t2=True,
        correct_wkts_t1=False, correct_wkts_t2=True, correct_pom=False,
    )
    db_session.commit()
    calculate_scores(db_session, completed_match.id)

    verdict = get_match_verdict(db_session, populated_league.id, completed_match.id, league_users[0].id)
    w = verdict.winners[0]
    assert w.hits.winner is True
    assert w.hits.runs_t1 is False
    assert w.hits.runs_t2 is True
    assert w.hits.wkts_t1 is False
    assert w.hits.wkts_t2 is True
    assert w.hits.pom is False
    # Sum: 10 + 20 + 20 = 50
    assert w.points_earned == 50


def test_header_carries_pom_and_team_shorts(db_session, populated_league, completed_match, test_teams, league_users):
    """Header fields populated correctly: POM name, winning/losing team short, match label."""
    team1, team2 = test_teams
    t1p = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2p = db_session.query(Player).filter(Player.team_id == team2.id).all()
    _make_pred(db_session, league_users[0].id, completed_match, t1p, t2p)
    db_session.commit()
    calculate_scores(db_session, completed_match.id)

    verdict = get_match_verdict(db_session, populated_league.id, completed_match.id, league_users[0].id)
    # POM is team1's player[0] per the completed_match fixture
    expected_pom = t1p[0].name
    assert verdict.pom_player_name == expected_pom
    assert verdict.winning_team_short == "TMA"
    assert verdict.losing_team_short == "TMB"
    assert verdict.match_label.startswith("M")


def test_returns_none_when_predictions_unprocessed(db_session, populated_league, completed_match, test_teams, league_users):
    """Verdict only surfaces after scoring runs (is_processed must be True)."""
    team1, team2 = test_teams
    t1p = db_session.query(Player).filter(Player.team_id == team1.id).all()
    t2p = db_session.query(Player).filter(Player.team_id == team2.id).all()
    _make_pred(db_session, league_users[0].id, completed_match, t1p, t2p)
    db_session.commit()
    # Deliberately NOT calling calculate_scores

    assert get_match_verdict(db_session, populated_league.id, completed_match.id, league_users[0].id) is None
