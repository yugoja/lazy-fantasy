from datetime import datetime, timedelta, timezone

from app.models.match import Match, MatchStatus


def test_match_players_includes_recent_team_form(client, db_session, test_tournament, test_teams):
    team1, team2 = test_teams
    now = datetime.now(timezone.utc)

    historical_results = [
        team1.id,
        team2.id,
        team1.id,
        None,
        team1.id,
        team2.id,
    ]

    for index, winner_id in enumerate(historical_results):
        db_session.add(
            Match(
                tournament_id=test_tournament.id,
                team_1_id=team1.id,
                team_2_id=team2.id,
                start_time=now - timedelta(days=6 - index),
                status=MatchStatus.COMPLETED,
                result_winner_id=winner_id,
            )
        )

    upcoming_match = Match(
        tournament_id=test_tournament.id,
        team_1_id=team1.id,
        team_2_id=team2.id,
        start_time=now + timedelta(hours=3),
        status=MatchStatus.SCHEDULED,
    )
    db_session.add(upcoming_match)
    db_session.commit()
    db_session.refresh(upcoming_match)

    response = client.get(f"/matches/{upcoming_match.id}/players")

    assert response.status_code == 200
    payload = response.json()

    assert [entry["result"] for entry in payload["team_1_form"]] == ["L", "W", "NR", "W", "L"]
    assert [entry["result"] for entry in payload["team_2_form"]] == ["W", "L", "NR", "L", "W"]
    assert len(payload["team_1_form"]) == 5
    assert len(payload["team_2_form"]) == 5
    assert all(entry["opponent_short_name"] == team2.short_name for entry in payload["team_1_form"])
    assert all(entry["opponent_short_name"] == team1.short_name for entry in payload["team_2_form"])
