# -*- coding: utf-8 -*-
"""Extra model coverage tests."""
import datetime as dt

import pytest

from ufa_picks.game.models import Game, Team
from ufa_picks.user.models import Pick, User


@pytest.mark.usefixtures("db")
class TestGameCoverage:
    def test_team_methods(self, db):
        team1 = Team(id="T1", team_city="City1", team_name="Name1")
        team2 = Team(id="T2", team_city="City2", team_name="Name2")
        db.session.add_all([team1, team2])

        assert team1.full_name == "City1 Name1"

        game1 = Game(
            id="G1",
            home_team_id=team1.id,
            away_team_id=team2.id,
            status="Final",
            home_score=10,
            away_score=5,
            season="2025",
            week=1,
            streaming_url="",
            has_roster_report=False,
        )
        game2 = Game(
            id="G2",
            home_team_id=team2.id,
            away_team_id=team1.id,
            status="Final",
            home_score=5,
            away_score=10,
            season="2025",
            week=2,
            streaming_url="",
            has_roster_report=False,
        )
        game3 = Game(
            id="G3",
            home_team_id=team1.id,
            away_team_id=team2.id,
            status="Final",
            home_score=5,
            away_score=10,
            season="2025",
            week=3,
            streaming_url="",
            has_roster_report=False,
        )
        db.session.add_all([game1, game2, game3])
        db.session.commit()

        assert team1.wins(2025) == 2
        assert team1.losses(2025) == 1
        assert team1.record(2025) == "2 - 1"
        assert team2.wins(2025) == 1
        assert team2.losses(2025) == 2

    def test_game_methods(self):
        game = Game(
            id="G4",
            status="Scheduled",
            week=4,
            streaming_url="",
            has_roster_report=False,
            home_score=10,
            away_score=5,
        )
        assert game.winner is None

        game2 = Game(
            id="G5",
            status="Scheduled",
            week=5,
            streaming_url="",
            has_roster_report=False,
            home_score=None,
            away_score=None,
        )
        assert game2.higher_score is None
        assert game2.lower_score is None


@pytest.mark.usefixtures("db")
class TestUserCoverage:
    def test_user_get_score(self, db, user):
        user.save()
        # year is None (uses current year)
        assert user.get_score() == 0
        # year is unknown
        assert user.get_score(year=1999) == 0

    def test_pick_methods(self, db, user):
        team1 = Team(id="T3", team_city="City3", team_name="Name3")
        team2 = Team(id="T4", team_city="City4", team_name="Name4")
        db.session.add_all([team1, team2])

        game = Game(
            id="G6",
            home_team_id=team1.id,
            away_team_id=team2.id,
            status="Scheduled",
            home_score=10,
            away_score=5,
            season="2025",
            week=1,
            streaming_url="",
            has_roster_report=False,
        )
        db.session.add(game)

        pick = Pick(
            user_id=user.id, game_id=game.id, home_team_score=10, away_team_score=5
        )
        db.session.add(pick)
        db.session.commit()

        # When home score > away score
        assert pick.loser.id == team2.id
        assert pick.pick_str == "Name3 10 - 5"

        # Points when game status != Final
        assert pick.points == 0

        # Another case for loser
        pick.home_team_score = 5
        pick.away_team_score = 10
        db.session.commit()
        assert pick.loser.id == team1.id
