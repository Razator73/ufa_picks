# -*- coding: utf-8 -*-
"""Test scoring logic."""
import pytest

from ufa_picks.game.models import Game, Team
from ufa_picks.user.models import Pick

from .factories import UserFactory


@pytest.mark.usefixtures("db")
class TestScoring2026:
    """Test 2026 scoring rules."""

    @pytest.fixture
    def setup_teams(self, db):
        """Setup teams for testing."""
        team_a = Team(id="A", team_city="City A", team_name="Team A")
        team_b = Team(id="B", team_city="City B", team_name="Team B")
        db.session.add(team_a)
        db.session.add(team_b)
        db.session.commit()
        return team_a, team_b

    def test_2026_pick_points(self, db, setup_teams, user):
        """Test 2026 pick points calculation."""
        team_a, team_b = setup_teams

        # 2026 game, Team A beats Team B 10-6
        game = Game(
            id="GAME1",
            home_team_id=team_a.id,
            away_team_id=team_b.id,
            home_score=10,
            away_score=6,
            status="Final",
            week=1,
            streaming_url="",
            has_roster_report=False,
            season="2026",
        )
        db.session.add(game)

        pick = Pick(user_id=user.id, game_id=game.id)
        db.session.add(pick)
        db.session.commit()

        # Incorrect winner
        pick.home_team_score = 6
        pick.away_team_score = 10
        db.session.commit()
        assert pick.points == 0

        # Correct winner only
        pick.home_team_score = 3
        pick.away_team_score = 0
        db.session.commit()
        assert pick.points == 3  # base winner score for 2026

        # Correct winner, exact home score
        pick.home_team_score = 10
        pick.away_team_score = 2
        db.session.commit()
        assert pick.points == 4  # 3 winner + 1 exact home

        # Correct winner, exact away score
        pick.home_team_score = 7
        pick.away_team_score = 6
        db.session.commit()
        assert pick.points == 4  # 3 winner + 1 exact away

        # Correct winner, exact margin (margin is 4)
        pick.home_team_score = 14
        pick.away_team_score = 10
        db.session.commit()
        assert pick.points == 4  # 3 winner + 1 exact margin

        # Correct winner, exact scores (which inherently hits margin)
        pick.home_team_score = 10
        pick.away_team_score = 6
        db.session.commit()
        assert pick.points == 6  # 3 win + 1 home + 1 away + 1 margin

    def test_2026_lowest_week_drop(self, db, setup_teams, user):
        """Test dropping the lowest week in 2026."""
        team_a, team_b = setup_teams

        # Create three regular season games and one playoff game in 2026
        for w in [1, 2, 3, 14]:
            g = Game(
                id=f"G{w}",
                home_team_id=team_a.id,
                away_team_id=team_b.id,
                home_score=10,
                away_score=6,
                status="Final",
                week=w,
                streaming_url="",
                has_roster_report=False,
                season="2026",
            )
            db.session.add(g)
            p = Pick(user_id=user.id, game_id=g.id)
            if w == 1:
                # 6 points total
                p.home_team_score = 10
                p.away_team_score = 6
            elif w == 2:
                # 3 points total (base winner)
                p.home_team_score = 3
                p.away_team_score = 0
            elif w == 3:
                # 4 points total
                p.home_team_score = 14
                p.away_team_score = 10
            elif w == 14:
                # 6 points total (playoffs, > 13)
                p.home_team_score = 10
                p.away_team_score = 6
            db.session.add(p)
        db.session.commit()

        # Total points:
        # Week 1: 6
        # Week 2: 3
        # Week 3: 4
        # Week 14: 6 (playoffs)
        # Lowest reg season is Week 2 (3 pts)
        # Expected = 6 + 3 + 4 + 6 = 19
        # Dropped = 19 - 3 = 16

        score = user.get_score(year=2026)
        assert score == 16


@pytest.mark.usefixtures("db")
class TestScoring2025:
    """Test legacy 2025 scoring rules."""

    @pytest.fixture
    def setup_teams(self, db):
        """Setup teams for 2025 testing."""
        team_a = Team(id="A", team_city="City A", team_name="Team A")
        team_b = Team(id="B", team_city="City B", team_name="Team B")
        db.session.add(team_a)
        db.session.add(team_b)
        db.session.commit()
        return team_a, team_b

    def test_2025_pick_points(self, db, setup_teams, user):
        """Test 2025 pick points calculation."""
        team_a, team_b = setup_teams

        # 2025 game, Team A beats Team B 10-6 (margin 4)
        game = Game(
            id="OLDE1",
            home_team_id=team_a.id,
            away_team_id=team_b.id,
            home_score=10,
            away_score=6,
            status="Final",
            week=1,
            streaming_url="",
            has_roster_report=False,
            season="2025",
        )
        db.session.add(game)

        pick = Pick(user_id=user.id, game_id=game.id)
        db.session.add(pick)
        db.session.commit()

        # Incorrect winner
        pick.home_team_score = 6
        pick.away_team_score = 10
        db.session.commit()
        assert pick.points == 0

        # Correct winner only (base 1)
        # Note: closest_margin logic depends on other picks. If only one pick, it is always the closest.
        pick.home_team_score = 3
        pick.away_team_score = 0
        db.session.commit()
        assert pick.points == 2  # 1 win + 1 closest margin (margin 3 vs actual 4)

        # Better pick shows up
        user2 = UserFactory()
        db.session.add(user2)
        pick2 = Pick(
            user_id=user2.id, game_id=game.id, home_team_score=9, away_team_score=5
        )  # margin 4 (exact)
        db.session.add(pick2)
        db.session.commit()

        # Now pick1 is NOT the closest margin anymore
        assert pick.points == 1  # 1 win, and it's no longer the closest.
        assert pick2.points == 2  # 1 win + 1 closest margin (exact)

        # Correct winner, exact scores (including margin)
        pick.home_team_score = 10
        pick.away_team_score = 6
        db.session.commit()
        assert pick.points == 4  # 1 win + 1 home + 1 away + 1 closest margin

    def test_2025_no_week_drop(self, db, setup_teams, user):
        """Test that 2025 does not drop the lowest week."""
        team_a, team_b = setup_teams

        # Create two regular season games in 2025
        # 2025 should NOT drop the lowest week
        for w in [1, 2]:
            g = Game(
                id=f"G25_{w}",
                home_team_id=team_a.id,
                away_team_id=team_b.id,
                home_score=10,
                away_score=6,
                status="Final",
                week=w,
                streaming_url="",
                has_roster_report=False,
                season="2025",
            )
            db.session.add(g)
            p = Pick(user_id=user.id, game_id=g.id)
            if w == 1:
                # 1 win + 1 home + 1 away + 1 margin = 4
                p.home_team_score = 10
                p.away_team_score = 6
            elif w == 2:
                # 1 win = 1 (assuming another pick exists to take closest margin)
                p.home_team_score = 100
                p.away_team_score = 0
                user3 = UserFactory()
                db.session.add(user3)
                p_competitor = Pick(
                    user_id=user3.id,
                    game_id=g.id,
                    home_team_score=10,
                    away_team_score=6,
                )
                db.session.add(p_competitor)
            db.session.add(p)
        db.session.commit()

        # Week 1: 4 points
        # Week 2: 1 point
        # Expected = 5 (No drop!)

        score = user.get_score(year=2025)
        assert score == 5
