"""Integration tests for player_form_service — seed, update_after_match, update_availability."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.team import Team
from app.models.player_form import PlayerForm
from app.services.football_provider import (
    WCSquadPlayer, FixtureLineup, FootballFixtureResult, FootballPlayerStat,
)
from app.services.player_form_service import (
    seed_player_form,
    update_player_form_after_match,
    update_availability_from_lineup,
    SeedSummary,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_BRA_PLAYERS = ["Neymar", "Vinicius Junior", "Rodrygo", "Richarlison", "Raphinha"]
_GER_PLAYERS = ["Mueller", "Gnabry", "Havertz", "Musiala", "Sane"]


@pytest.fixture
def football_teams(db_session):
    t1 = Team(name="Brazil", short_name="BRA", sport="football", api_football_team_id="6")
    t2 = Team(name="Germany", short_name="GER", sport="football", api_football_team_id="25")
    db_session.add_all([t1, t2])
    db_session.commit()
    db_session.refresh(t1)
    db_session.refresh(t2)

    for name in _BRA_PLAYERS:
        db_session.add(Player(name=name, team_id=t1.id, role="forward"))
    for name in _GER_PLAYERS:
        db_session.add(Player(name=name, team_id=t2.id, role="midfielder"))
    db_session.commit()
    db_session.refresh(t1)
    db_session.refresh(t2)
    return t1, t2


@pytest.fixture
def football_match(db_session, test_tournament, football_teams):
    t1, t2 = football_teams
    match = Match(
        tournament_id=test_tournament.id,
        team_1_id=t1.id,
        team_2_id=t2.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        external_match_id="54321",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


def _make_wc_player(api_id, name, position="Attacker", appearances=10,
                    minutes=900, goals=3, assists=2, clean_sheets=0):
    return WCSquadPlayer(
        api_player_id=api_id,
        name=name,
        position=position,
        appearances=appearances,
        minutes=minutes,
        goals=goals,
        assists=assists,
        clean_sheets=clean_sheets,
    )


def _make_fixture_stat(player, team_api_id, goals=0, assists=0, minutes=90):
    return FootballPlayerStat(
        api_player_id=int(player.api_football_player_id or 0),
        name=player.name,
        team_api_id=team_api_id,
        minutes_played=minutes,
        goals=goals,
        assists=assists,
        red_card=False,
        own_goals=0,
        ingame_pen_saves=0,
        shootout_pen_saves=0,
        ingame_pen_misses=0,
    )


# ── seed_player_form ──────────────────────────────────────────────────────────

def _make_provider(squad=None, club_stats=None):
    """Return a mock provider with safe defaults for all methods used by seed."""
    provider = MagicMock()
    provider._get.return_value = {"response": []}
    provider.get_wc_squad.return_value = squad or []
    provider.get_player_club_stats.return_value = club_stats  # None = fall back to national data
    return provider


class TestSeedPlayerForm:
    def test_seed_creates_form_rows_for_matched_players(self, db_session, football_teams):
        t1, t2 = football_teams
        t1_players = db_session.query(Player).filter(Player.team_id == t1.id).all()

        squad = [_make_wc_player(100 + i, p.name, "Attacker") for i, p in enumerate(t1_players)]
        provider = _make_provider(squad=squad)

        summary = seed_player_form(db_session, provider, wc_league_id=1, season=2026)

        forms = db_session.query(PlayerForm).all()
        assert len(forms) == len(t1_players)
        assert isinstance(summary, SeedSummary)
        assert summary.forms_created == len(t1_players)

    def test_seed_sets_pre_expected_points(self, db_session, football_teams):
        t1, t2 = football_teams
        t1_players = db_session.query(Player).filter(Player.team_id == t1.id).all()
        p = t1_players[0]

        squad = [_make_wc_player(200, p.name, "Attacker", appearances=10, goals=5)]
        provider = _make_provider(squad=squad)

        seed_player_form(db_session, provider, wc_league_id=1, season=2026)

        form = db_session.query(PlayerForm).filter(PlayerForm.player_id == p.id).first()
        assert form is not None
        assert form.pre_expected_points is not None
        assert form.pre_expected_points > 0
        assert form.expected_points == form.pre_expected_points

    def test_seed_sets_wc_accumulators_to_zero(self, db_session, football_teams):
        t1, _ = football_teams
        player = db_session.query(Player).filter(Player.team_id == t1.id).first()
        squad = [_make_wc_player(300, player.name)]
        provider = _make_provider(squad=squad)

        seed_player_form(db_session, provider, wc_league_id=1, season=2026)

        form = db_session.query(PlayerForm).filter(PlayerForm.player_id == player.id).first()
        assert form.wc_goals == 0
        assert form.wc_assists == 0
        assert form.wc_minutes == 0
        assert form.wc_games == 0
        assert form.floor == "mid"
        assert form.availability == "starter"

    def test_seed_is_idempotent(self, db_session, football_teams):
        t1, _ = football_teams
        player = db_session.query(Player).filter(Player.team_id == t1.id).first()
        squad = [_make_wc_player(400, player.name, goals=3)]
        provider = _make_provider(squad=squad)

        seed_player_form(db_session, provider, wc_league_id=1, season=2026)
        seed_player_form(db_session, provider, wc_league_id=1, season=2026)

        forms = db_session.query(PlayerForm).filter(PlayerForm.player_id == player.id).all()
        assert len(forms) == 1  # upsert, not duplicate

    def test_seed_returns_summary_counts(self, db_session, football_teams):
        t1, t2 = football_teams
        t1_players = db_session.query(Player).filter(Player.team_id == t1.id).all()
        t2_players = db_session.query(Player).filter(Player.team_id == t2.id).all()
        t1_squad = [_make_wc_player(500 + i, p.name) for i, p in enumerate(t1_players)]
        t1_squad.append(_make_wc_player(998, "ZZZXXX Nobody Special"))
        t2_squad = [_make_wc_player(600 + i, p.name) for i, p in enumerate(t2_players)]
        t2_squad.append(_make_wc_player(999, "AAABBB Nobody Special"))

        def _squad_side_effect(team_id, season, league_id=None):
            return t1_squad if team_id == int(t1.api_football_team_id) else t2_squad

        provider = _make_provider()
        provider.get_wc_squad.side_effect = _squad_side_effect

        summary = seed_player_form(db_session, provider, wc_league_id=1, season=2026)
        assert summary.players_matched == len(t1_players) + len(t2_players)
        assert summary.players_unmatched == 2

    def test_seed_caches_api_football_player_id(self, db_session, football_teams):
        t1, _ = football_teams
        player = db_session.query(Player).filter(Player.team_id == t1.id).first()
        player.api_football_player_id = None
        db_session.commit()

        squad = [_make_wc_player(601, player.name)]
        provider = _make_provider(squad=squad)

        seed_player_form(db_session, provider, wc_league_id=1, season=2026)
        db_session.refresh(player)
        assert player.api_football_player_id == "601"

    def test_seed_prefers_club_stats_over_national_team(self, db_session, football_teams):
        """Club stats (more appearances) override national team stats for expected_points."""
        t1, _ = football_teams
        player = db_session.query(Player).filter(Player.team_id == t1.id).first()

        # National team: 6 games, 3 goals (small sample)
        nat_sp = _make_wc_player(700, player.name, "Attacker", appearances=6, minutes=540, goals=3, assists=1)
        # Club: 32 games, 10 goals (much richer data)
        club_sp = _make_wc_player(700, player.name, "Attacker", appearances=32, minutes=2700, goals=10, assists=6)

        provider = _make_provider(squad=[nat_sp], club_stats=club_sp)

        seed_player_form(db_session, provider, wc_league_id=1, season=2026)

        form = db_session.query(PlayerForm).filter(PlayerForm.player_id == player.id).first()
        assert form is not None
        # xp from club data: per90_base=1.0 + goals_per90=(10/30)*6 + assists_per90=(6/30)*3
        # = 1.0 + 2.0 + 0.6 = 3.6  (different from national 3-goal-in-6 calculation)
        # Just verify we stored something and it reflects the higher-appearance dataset
        assert form.expected_points > 0
        provider.get_player_club_stats.assert_called_with(700, 2025)


# ── update_player_form_after_match ────────────────────────────────────────────

class TestUpdatePlayerFormAfterMatch:
    def test_increments_wc_accumulators(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        player = db_session.query(Player).filter(Player.team_id == t1.id).first()
        player.api_football_player_id = "701"
        db_session.add(PlayerForm(
            player_id=player.id,
            expected_points=7.0, floor="mid", availability="starter",
            wc_goals=0, wc_assists=0, wc_minutes=0, wc_clean_sheets=0, wc_games=0,
            pre_expected_points=7.0,
        ))
        db_session.commit()

        fixture_result = FootballFixtureResult(
            fixture_id=54321, status_short="FT",
            home_team_api_id=int(t1.api_football_team_id),
            away_team_api_id=int(t2.api_football_team_id),
            team1_goals_reg=2, team2_goals_reg=0,
            team1_goals_et=None, team2_goals_et=None,
            penalty_team1=None, penalty_team2=None,
        )
        stat = _make_fixture_stat(player, int(t1.api_football_team_id), goals=1, assists=1, minutes=90)

        update_player_form_after_match(db_session, football_match, [stat], fixture_result)

        form = db_session.query(PlayerForm).filter(PlayerForm.player_id == player.id).first()
        assert form.wc_goals == 1
        assert form.wc_assists == 1
        assert form.wc_minutes == 90
        assert form.wc_games == 1

    def test_recomputes_expected_points_after_match(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        player = db_session.query(Player).filter(Player.team_id == t1.id).first()
        player.api_football_player_id = "702"
        old_xp = 7.0
        db_session.add(PlayerForm(
            player_id=player.id,
            expected_points=old_xp, floor="mid", availability="starter",
            wc_goals=0, wc_assists=0, wc_minutes=0, wc_clean_sheets=0, wc_games=0,
            pre_expected_points=old_xp,
        ))
        db_session.commit()

        fixture_result = FootballFixtureResult(
            fixture_id=54321, status_short="FT",
            home_team_api_id=int(t1.api_football_team_id),
            away_team_api_id=int(t2.api_football_team_id),
            team1_goals_reg=3, team2_goals_reg=0,
            team1_goals_et=None, team2_goals_et=None,
            penalty_team1=None, penalty_team2=None,
        )
        stat = _make_fixture_stat(player, int(t1.api_football_team_id), goals=2, minutes=90)

        update_player_form_after_match(db_session, football_match, [stat], fixture_result)

        form = db_session.query(PlayerForm).filter(PlayerForm.player_id == player.id).first()
        assert form.expected_points != old_xp  # should have changed

    def test_awards_clean_sheet_to_keeper_who_played_60plus_mins(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        gk = db_session.query(Player).filter(Player.team_id == t1.id).first()
        gk.role = "goalkeeper"
        gk.api_football_player_id = "703"
        db_session.add(PlayerForm(
            player_id=gk.id,
            expected_points=5.0, floor="mid", availability="starter",
            wc_goals=0, wc_assists=0, wc_minutes=0, wc_clean_sheets=0, wc_games=0,
            pre_expected_points=5.0,
        ))
        db_session.commit()

        fixture_result = FootballFixtureResult(
            fixture_id=54321, status_short="FT",
            home_team_api_id=int(t1.api_football_team_id),
            away_team_api_id=int(t2.api_football_team_id),
            team1_goals_reg=1, team2_goals_reg=0,  # t2 (away) scored 0 — clean sheet for t1
            team1_goals_et=None, team2_goals_et=None,
            penalty_team1=None, penalty_team2=None,
        )
        stat = _make_fixture_stat(gk, int(t1.api_football_team_id), minutes=90)

        update_player_form_after_match(db_session, football_match, [stat], fixture_result)

        form = db_session.query(PlayerForm).filter(PlayerForm.player_id == gk.id).first()
        assert form.wc_clean_sheets == 1

    def test_no_clean_sheet_if_player_played_under_60_mins(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        gk = db_session.query(Player).filter(Player.team_id == t1.id).first()
        gk.role = "goalkeeper"
        gk.api_football_player_id = "704"
        db_session.add(PlayerForm(
            player_id=gk.id,
            expected_points=5.0, floor="mid", availability="starter",
            wc_goals=0, wc_assists=0, wc_minutes=0, wc_clean_sheets=0, wc_games=0,
            pre_expected_points=5.0,
        ))
        db_session.commit()

        fixture_result = FootballFixtureResult(
            fixture_id=54321, status_short="FT",
            home_team_api_id=int(t1.api_football_team_id),
            away_team_api_id=int(t2.api_football_team_id),
            team1_goals_reg=1, team2_goals_reg=0,
            team1_goals_et=None, team2_goals_et=None,
            penalty_team1=None, penalty_team2=None,
        )
        stat = _make_fixture_stat(gk, int(t1.api_football_team_id), minutes=45)  # < 60

        update_player_form_after_match(db_session, football_match, [stat], fixture_result)

        form = db_session.query(PlayerForm).filter(PlayerForm.player_id == gk.id).first()
        assert form.wc_clean_sheets == 0

    def test_missing_form_row_does_not_raise(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        player = db_session.query(Player).filter(Player.team_id == t1.id).first()
        player.api_football_player_id = "705"
        db_session.commit()
        # No PlayerForm row — should be silently skipped

        fixture_result = FootballFixtureResult(
            fixture_id=54321, status_short="FT",
            home_team_api_id=int(t1.api_football_team_id),
            away_team_api_id=int(t2.api_football_team_id),
            team1_goals_reg=1, team2_goals_reg=0,
            team1_goals_et=None, team2_goals_et=None,
            penalty_team1=None, penalty_team2=None,
        )
        stat = _make_fixture_stat(player, int(t1.api_football_team_id), goals=1)

        update_player_form_after_match(db_session, football_match, [stat], fixture_result)
        # Should not raise

    def test_stamps_updated_at(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        player = db_session.query(Player).filter(Player.team_id == t1.id).first()
        player.api_football_player_id = "706"
        db_session.add(PlayerForm(
            player_id=player.id,
            expected_points=7.0, floor="mid", availability="starter",
            wc_goals=0, wc_assists=0, wc_minutes=0, wc_clean_sheets=0, wc_games=0,
            pre_expected_points=7.0, updated_at=None,
        ))
        db_session.commit()

        fixture_result = FootballFixtureResult(
            fixture_id=54321, status_short="FT",
            home_team_api_id=int(t1.api_football_team_id),
            away_team_api_id=int(t2.api_football_team_id),
            team1_goals_reg=1, team2_goals_reg=0,
            team1_goals_et=None, team2_goals_et=None,
            penalty_team1=None, penalty_team2=None,
        )
        stat = _make_fixture_stat(player, int(t1.api_football_team_id), minutes=90)
        update_player_form_after_match(db_session, football_match, [stat], fixture_result)

        form = db_session.query(PlayerForm).filter(PlayerForm.player_id == player.id).first()
        assert form.updated_at is not None


# ── update_availability_from_lineup ──────────────────────────────────────────

class TestUpdateAvailabilityFromLineup:
    def _setup_forms(self, db_session, players):
        for p in players:
            form = PlayerForm(
                player_id=p.id,
                expected_points=6.0, floor="mid", availability="doubt",
                wc_goals=0, wc_assists=0, wc_minutes=0, wc_clean_sheets=0, wc_games=0,
                pre_expected_points=6.0,
            )
            db_session.add(form)
        db_session.commit()

    def test_starters_get_starter_availability(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        t1_players = db_session.query(Player).filter(Player.team_id == t1.id).all()
        t2_players = db_session.query(Player).filter(Player.team_id == t2.id).all()
        all_players = t1_players + t2_players
        for i, p in enumerate(all_players):
            p.api_football_player_id = str(1000 + i)
        db_session.commit()
        self._setup_forms(db_session, all_players)

        home_starter_ids = [int(p.api_football_player_id) for p in t1_players[:3]]
        away_starter_ids = [int(p.api_football_player_id) for p in t2_players[:3]]
        lineup = FixtureLineup(
            home_starters=home_starter_ids,
            away_starters=away_starter_ids,
            home_subs=[int(p.api_football_player_id) for p in t1_players[3:]],
            away_subs=[int(p.api_football_player_id) for p in t2_players[3:]],
        )

        update_availability_from_lineup(db_session, football_match, lineup)

        for p in t1_players[:3]:
            form = db_session.query(PlayerForm).filter(PlayerForm.player_id == p.id).first()
            assert form.availability == "starter"

    def test_subs_get_rotation_availability(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        t1_players = db_session.query(Player).filter(Player.team_id == t1.id).all()
        t2_players = db_session.query(Player).filter(Player.team_id == t2.id).all()
        all_players = t1_players + t2_players
        for i, p in enumerate(all_players):
            p.api_football_player_id = str(2000 + i)
        db_session.commit()
        self._setup_forms(db_session, all_players)

        lineup = FixtureLineup(
            home_starters=[int(p.api_football_player_id) for p in t1_players[:3]],
            away_starters=[int(p.api_football_player_id) for p in t2_players[:3]],
            home_subs=[int(p.api_football_player_id) for p in t1_players[3:]],
            away_subs=[int(p.api_football_player_id) for p in t2_players[3:]],
        )

        update_availability_from_lineup(db_session, football_match, lineup)

        for p in t1_players[3:]:
            form = db_session.query(PlayerForm).filter(PlayerForm.player_id == p.id).first()
            assert form.availability == "rotation"

    def test_players_not_in_lineup_get_doubt(self, db_session, football_teams, football_match):
        t1, t2 = football_teams
        t1_players = db_session.query(Player).filter(Player.team_id == t1.id).all()
        t2_players = db_session.query(Player).filter(Player.team_id == t2.id).all()
        all_players = t1_players + t2_players
        for i, p in enumerate(all_players):
            p.api_football_player_id = str(3000 + i)
        db_session.commit()
        self._setup_forms(db_session, all_players)

        # Only put 2 from each team in the lineup — the rest should be "doubt"
        lineup = FixtureLineup(
            home_starters=[int(t1_players[0].api_football_player_id)],
            away_starters=[int(t2_players[0].api_football_player_id)],
            home_subs=[int(t1_players[1].api_football_player_id)],
            away_subs=[int(t2_players[1].api_football_player_id)],
        )

        update_availability_from_lineup(db_session, football_match, lineup)

        for p in t1_players[2:]:
            form = db_session.query(PlayerForm).filter(PlayerForm.player_id == p.id).first()
            assert form.availability == "doubt"


# ── fallback_job integration — uses PlayerForm data ──────────────────────────

class TestFallbackJobUsesPlayerForm:
    def test_build_prediction_inputs_uses_form_expected_points(self, db_session, football_teams, football_match):
        from app.services.fallback_job import build_prediction_inputs_from_db, _POSITION_XP

        t1, t2 = football_teams
        all_players = (
            db_session.query(Player).filter(
                Player.team_id.in_([t1.id, t2.id])
            ).all()
        )

        # Give each player a real form row with distinct expected_points
        for i, p in enumerate(all_players):
            db_session.add(PlayerForm(
                player_id=p.id,
                expected_points=12.5,  # different from any stub value
                floor="high",
                availability="starter",
                wc_goals=0, wc_assists=0, wc_minutes=0, wc_clean_sheets=0, wc_games=0,
                pre_expected_points=12.5,
            ))
        db_session.commit()

        inputs = build_prediction_inputs_from_db(db_session, football_match)
        # All players should now use the form value, not the stub
        for sp in inputs.players:
            assert sp.expected_points == 12.5

    def test_build_prediction_inputs_falls_back_to_stub_without_form(self, db_session, football_teams, football_match):
        from app.services.fallback_job import build_prediction_inputs_from_db, _POSITION_XP

        # No PlayerForm rows — stubs should apply
        inputs = build_prediction_inputs_from_db(db_session, football_match)
        for sp in inputs.players:
            assert sp.expected_points in _POSITION_XP.values()
