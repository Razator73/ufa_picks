# -*- coding: utf-8 -*-
"""Tests for excluding cancelled games from views and scoring."""
import datetime as dt

import pytest
from flask import url_for

from ufa_picks.game.models import CancelledGame, Game, Team
from ufa_picks.user.models import Pick


@pytest.mark.usefixtures("db")
class TestCancelledGameScoring:
    """Cancelled games must not score or block a week from completing."""

    @pytest.fixture
    def teams(self, db):
        """Create two teams to play the games."""
        team_a = Team(id="A", team_city="City A", team_name="Team A")
        team_b = Team(id="B", team_city="City B", team_name="Team B")
        db.session.add_all([team_a, team_b])
        db.session.commit()
        return team_a, team_b

    def _game(self, db, teams, gid, week, status="Final", home=10, away=0, days_ago=5):
        """Create and stage a game."""
        team_a, team_b = teams
        game = Game(
            id=gid,
            home_team_id=team_a.id,
            away_team_id=team_b.id,
            home_score=home,
            away_score=away,
            status=status,
            week=week,
            season="2026",
            streaming_url="",
            has_roster_report=False,
            start_timestamp=dt.datetime.now() - dt.timedelta(days=days_ago),
        )
        db.session.add(game)
        return game

    def test_cancelled_game_does_not_block_week_completion(self, db, teams, user):
        """A cancelled (never-Final) game must not keep its week from being dropped."""
        # Week 1 fully played: correct winner + exact score = 6 pts.
        g1 = self._game(db, teams, "W1", week=1)
        db.session.add(
            Pick(user_id=user.id, game_id=g1.id, home_team_score=10, away_team_score=0)
        )
        # Week 2 fully played: correct winner only (no exact/margin) = 3 pts.
        g2 = self._game(db, teams, "W2", week=2)
        db.session.add(
            Pick(user_id=user.id, game_id=g2.id, home_team_score=5, away_team_score=3)
        )
        # Week 2 also has a cancelled game that will never go Final.
        gc = self._game(db, teams, "W2-CANCELLED", week=2, status="Upcoming")
        db.session.add(CancelledGame(game_id=gc.id))
        db.session.commit()

        # Both weeks complete, so the lowest (week 2 = 3) is dropped -> 6 remains.
        assert user.get_score(year="2026") == 6

    def test_non_cancelled_upcoming_game_blocks_drop(self, db, teams, user):
        """Contrast: a real Upcoming game keeps its week incomplete (not dropped)."""
        g1 = self._game(db, teams, "N1", week=1)
        db.session.add(
            Pick(user_id=user.id, game_id=g1.id, home_team_score=10, away_team_score=0)
        )  # 6 pts
        g2 = self._game(db, teams, "N2", week=2)
        db.session.add(
            Pick(user_id=user.id, game_id=g2.id, home_team_score=5, away_team_score=3)
        )  # 3 pts
        # A normal (non-cancelled) Upcoming game leaves week 2 incomplete.
        self._game(db, teams, "N2-PENDING", week=2, status="Upcoming")
        db.session.commit()

        # Only week 1 is complete -> nothing dropped -> 6 + 3 = 9.
        assert user.get_score(year="2026") == 9

    def test_cancelled_final_game_pick_does_not_score(self, db, teams, user):
        """Even if a cancelled game is marked Final, its pick earns 0 points."""
        gc = self._game(db, teams, "C-FINAL", week=4, status="Final", home=10, away=0)
        db.session.add(CancelledGame(game_id=gc.id))
        db.session.add(
            Pick(user_id=user.id, game_id=gc.id, home_team_score=10, away_team_score=0)
        )  # would be 6 pts if it counted
        db.session.commit()

        assert user.get_weekly_score("2026", 4) == 0
        assert user.get_game_score(gc.id) == 0


@pytest.mark.usefixtures("db")
class TestCancelledGameViews:
    """Cancelled games must not appear in or accept picks through the UI."""

    def login(self, user, testapp):
        """Login helper (posts to the auth route directly; CSRF is off in tests)."""
        return testapp.post(
            "/login/",
            {"username": user.username, "password": "myprecious"},
        ).follow()

    def _future_game(self, db, gid, week=1):
        """Create a future game (week not yet locked) with fresh teams."""
        team_a = Team(id=f"{gid}A", team_city="C", team_name="N")
        team_b = Team(id=f"{gid}B", team_city="C", team_name="N")
        db.session.add_all([team_a, team_b])
        future = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(
            days=1
        )
        game = Game(
            id=gid,
            home_team_id=team_a.id,
            away_team_id=team_b.id,
            status="Upcoming",
            week=week,
            season="2026",
            streaming_url="",
            has_roster_report=False,
            start_timestamp=future,
        )
        db.session.add(game)
        return game

    def test_game_details_cancelled_redirects(self, user, testapp, db):
        """Game details for a cancelled game redirects away instead of rendering."""
        game = self._future_game(db, "DET-CANCEL")
        db.session.add(CancelledGame(game_id=game.id))
        db.session.commit()

        self.login(user, testapp)
        res = testapp.get(f"/games/2026/game/{game.id}").follow()
        assert res.status_code == 200
        assert "cancelled" in res.text.lower()

    def test_update_pick_cancelled_blocked(self, user, testapp, db):
        """The pick API rejects updates for a cancelled game."""
        game = self._future_game(db, "PICK-CANCEL")
        db.session.add(CancelledGame(game_id=game.id))
        db.session.commit()

        self.login(user, testapp)
        res = testapp.post_json(
            f"/games/update_pick/{game.id}",
            {"home_team_score": 10, "away_team_score": 5},
            expect_errors=True,
        )
        assert res.status_code == 400
        assert "cancelled" in res.json["message"].lower()

    def test_cancelled_game_excluded_from_week_view(self, user, testapp, db):
        """A cancelled game is not listed on its week's picks page."""
        live = self._future_game(db, "LIVE-GAME", week=1)
        cancelled = self._future_game(db, "GONE-GAME", week=1)
        db.session.add(CancelledGame(game_id=cancelled.id))
        db.session.commit()

        self.login(user, testapp)
        res = testapp.get(url_for("game.week", year="2026", week_num=1))
        assert res.status_code == 200
        assert live.id in res.text
        assert cancelled.id not in res.text
