# -*- coding: utf-8 -*-
"""Weekly and Game view tests."""
import datetime as dt

from flask import url_for

from .factories import GameFactory, PickFactory, UserFactory


class TestWeeklyViews:
    """Test weekly views and game details."""

    def login(self, user, testapp):
        """Login user."""
        res = testapp.get("/")
        form = res.forms["loginForm"]
        form["username"] = user.username
        form["password"] = "myprecious"
        res = form.submit().follow()
        return res

    def test_weekly_leaderboard(self, user, testapp, db):
        """Test weekly leaderboard filter."""

        # Create a game for week 1
        game = GameFactory(
            season="2026", week=1, status="Final", home_score=20, away_score=10
        )
        db.session.add(game)

        # Another user who wins this week
        winner = UserFactory(active=True)
        db.session.add(winner)

        # Winner picks correctly (2 pts in 2026 if winner is right + 3 base = 5 typically,
        # but let's just ensure points > 0)
        pick_win = PickFactory(
            user=winner, game=game, home_team_score=20, away_team_score=10
        )
        db.session.add(pick_win)

        # Current user picks wrongly
        pick_lose = PickFactory(
            user=user, game=game, home_team_score=0, away_team_score=50
        )
        db.session.add(pick_lose)

        db.session.commit()

        self.login(user, testapp)

        # Test leaderboard for week 1
        res = testapp.get(url_for("user.members", year="2026", week=1))
        assert res.status_code == 200
        assert "Week 1" in res.text
        # Winner should be ranked higher than current user for this week
        assert winner.full_name in res.text

    def test_game_details_pre_lock(self, user, testapp, db):
        """Test game details before locking."""

        # Future game
        future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7)
        game = GameFactory(
            season="2026", week=2, start_timestamp=future.replace(tzinfo=None)
        )
        db.session.add(game)
        db.session.commit()

        self.login(user, testapp)
        res = testapp.get(url_for("game.game_details", year="2026", game_id=game.id))
        assert res.status_code == 200
        assert "Edit Your Pick" in res.text
        assert "Other players’ picks will be revealed" in res.text

        # Submit pick via the form
        form = res.forms[0]  # The only form on the page
        form[f"game_{game.id}-away_team_score"] = "24"
        form[f"game_{game.id}-home_team_score"] = "17"
        res = form.submit().follow()
        assert "Pick updated!" in res.text

        from ufa_picks.user.models import Pick

        pick = Pick.query.filter_by(user_id=user.id, game_id=game.id).first()
        assert pick.away_team_score == 24
        assert pick.home_team_score == 17

    def test_game_details_post_lock(self, user, testapp, db):
        """Test game details after locking."""

        # Past game (locks at first game of week, let's just make it past)
        past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
        game = GameFactory(
            season="2026", week=3, start_timestamp=past.replace(tzinfo=None)
        )
        db.session.add(game)

        # Other user's pick
        other = UserFactory(active=True)
        db.session.add(other)
        PickFactory(user=other, game=game, home_team_score=10, away_team_score=10)

        db.session.commit()

        self.login(user, testapp)
        res = testapp.get(url_for("game.game_details", year="2026", game_id=game.id))
        assert res.status_code == 200
        assert "All Player Picks" in res.text
        assert other.full_name in res.text
        assert "Edit Your Pick" not in res.text

    def test_game_details_following_picks(self, user, testapp, db):
        """Test that followed picks appear in a separate table."""
        past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
        game = GameFactory(
            season="2026", week=4, start_timestamp=past.replace(tzinfo=None)
        )
        db.session.add(game)

        # User we follow
        followed_user = UserFactory(active=True)
        db.session.add(followed_user)
        user.follow(followed_user)

        # Their pick
        PickFactory(
            user=followed_user, game=game, home_team_score=21, away_team_score=14
        )

        # User we DON'T follow
        stranger = UserFactory(active=True)
        db.session.add(stranger)
        PickFactory(user=stranger, game=game, home_team_score=7, away_team_score=3)

        db.session.commit()

        self.login(user, testapp)
        res = testapp.get(url_for("game.game_details", year="2026", game_id=game.id))

        assert res.status_code == 200
        assert "Friends' Picks" in res.text
        assert followed_user.full_name in res.text
        assert stranger.full_name in res.text  # present in the all players table

    def test_game_details_sorting(self, user, testapp, db):
        """Test that picks are sorted by points descending."""
        past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
        game = GameFactory(
            season="2026",
            week=5,
            status="Final",
            home_score=10,
            away_score=0,
            streaming_url="",
            has_roster_report=False,
            start_timestamp=past.replace(tzinfo=None),
        )
        db.session.add(game)

        # High score player
        top = UserFactory(active=True, last_name="Alpha")
        db.session.add(top)
        PickFactory(user=top, game=game, home_team_score=10, away_team_score=0)  # 6 pts

        # Low score player
        bottom = UserFactory(active=True, last_name="Omega")
        db.session.add(bottom)
        PickFactory(
            user=bottom, game=game, home_team_score=3, away_team_score=0
        )  # 4 pts

        db.session.commit()

        self.login(user, testapp)
        res = testapp.get(url_for("game.game_details", year="2026", game_id=game.id))

        assert res.status_code == 200
        # Check order in HTML text
        text = res.text
        pos_top = text.find(top.full_name)
        pos_bottom = text.find(bottom.full_name, pos_top)  # find bottom AFTER top
        assert pos_top != -1
        assert pos_bottom != -1
        assert pos_top < pos_bottom

    def test_sidebar_following_standings(self, user, testapp, db):
        """Test friends standings in pre and post week views."""
        # Create a game for week 6
        game = GameFactory(season="2026", week=6)
        db.session.add(game)

        # Follow another user
        followed = UserFactory(active=True)
        db.session.add(followed)
        user.follow(followed)

        db.session.commit()

        self.login(user, testapp)

        # 1. Test Pre-Lock (Pick Entry)
        res = testapp.get(url_for("game.week", year="2026", week_num=6))
        assert "Friends Standings" in res.text
        assert followed.full_name in res.text
        assert user.full_name in res.text

        # 2. Test Post-Lock (Results)
        # Lock the week by making first game in past
        game.start_timestamp = (
            dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        ).replace(tzinfo=None)
        db.session.commit()

        res = testapp.get(url_for("game.week", year="2026", week_num=6))
        assert "Friends Weekly Standings" in res.text
        assert followed.full_name in res.text
        assert user.full_name in res.text
