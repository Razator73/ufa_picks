# -*- coding: utf-8 -*-
"""Game view tests."""
import datetime as dt

import pytest
from flask import url_for

from ufa_picks.game.models import Game, Team


class TestGameViews:
    def login(self, user, testapp):
        res = testapp.get("/")
        form = res.forms["loginForm"]
        form["username"] = user.username
        form["password"] = "myprecious"
        res = form.submit().follow()
        return res

    def test_games_main(self, user, testapp, db):
        self.login(user, testapp)
        res = testapp.get("/games/")
        assert res.status_code == 200

        res = testapp.get("/games/2026/")
        assert res.status_code == 200

    def test_games_week_pre_lock(self, user, testapp, db):
        self.login(user, testapp)

        team1 = Team(id="T1", team_city="C1", team_name="N1")
        team2 = Team(id="T2", team_city="C2", team_name="N2")
        db.session.add_all([team1, team2])
        future_time = dt.datetime.now(dt.timezone.utc).replace(
            tzinfo=None
        ) + dt.timedelta(days=1)
        game = Game(
            id="G1",
            home_team_id="T1",
            away_team_id="T2",
            status="Scheduled",
            week=1,
            season="2026",
            streaming_url="",
            has_roster_report=False,
            start_timestamp=future_time,
        )
        db.session.add(game)
        db.session.commit()

        res = testapp.get("/games/2026/week-1")
        assert res.status_code == 200

        res = testapp.post(
            "/games/2026/week-1",
            {"game_G1-home_team_score": "10", "game_G1-away_team_score": "5"},
        ).follow()
        assert "Your picks have been saved!" in res.text

        # Post again to update the existing pick
        res = testapp.post(
            "/games/2026/week-1",
            {"game_G1-home_team_score": "12", "game_G1-away_team_score": "7"},
        ).follow()
        assert "Your picks have been saved!" in res.text

    def test_games_week_post_lock(self, user, testapp, db):
        self.login(user, testapp)
        team1 = Team(id="T3", team_city="C3", team_name="N3")
        team2 = Team(id="T4", team_city="C4", team_name="N4")
        db.session.add_all([team1, team2])
        past_time = dt.datetime.now(dt.timezone.utc).replace(
            tzinfo=None
        ) - dt.timedelta(days=1)
        game = Game(
            id="G2",
            home_team_id="T3",
            away_team_id="T4",
            status="Final",
            home_score=10,
            away_score=5,
            week=2,
            season="2026",
            streaming_url="",
            has_roster_report=False,
            start_timestamp=past_time,
        )
        db.session.add(game)
        db.session.commit()

        res = testapp.get("/games/2026/week-2")
        assert res.status_code == 200

    def test_games_post_season(self, user, testapp, db):
        self.login(user, testapp)
        res = testapp.get("/games/2026/week-14")
        assert res.status_code == 200

    def test_games_no_games(self, user, testapp, db):
        self.login(user, testapp)
        res = testapp.get("/games/2026/week-3").follow()
        assert "No games found for this week." in res.text

        # Test week when year is None
        res = testapp.get("/games/week-3").follow()
        assert "No games found for this week." in res.text

    def test_update_pick_api(self, user, testapp, db):
        self.login(user, testapp)
        team1 = Team(id="T5", team_city="C5", team_name="N5")
        team2 = Team(id="T6", team_city="C6", team_name="N6")
        db.session.add_all([team1, team2])
        future_time = dt.datetime.now(dt.timezone.utc).replace(
            tzinfo=None
        ) + dt.timedelta(days=1)
        game = Game(
            id="G3",
            home_team_id="T5",
            away_team_id="T6",
            status="Scheduled",
            week=4,
            season="2026",
            streaming_url="",
            has_roster_report=False,
            start_timestamp=future_time,
        )
        db.session.add(game)
        db.session.commit()

        res = testapp.post_json(
            "/games/update_pick/G3", {"home_team_score": 10, "away_team_score": 5}
        )
        assert res.json["status"] == "success"

        # Update again
        res = testapp.post_json(
            "/games/update_pick/G3", {"home_team_score": 12, "away_team_score": 7}
        )
        assert res.json["status"] == "success"

        # Try to update past game
        past_time = dt.datetime.now(dt.timezone.utc).replace(
            tzinfo=None
        ) - dt.timedelta(days=1)
        game.start_timestamp = past_time
        db.session.commit()

        res = testapp.post_json(
            "/games/update_pick/G3",
            {"home_team_score": 10, "away_team_score": 5},
            expect_errors=True,
        )
        assert res.status_code == 400
        assert res.json["message"] == "Game has already started."

        # Test bad inputs on future game
        game.start_timestamp = future_time
        db.session.commit()

        # No data JSON (empty dict)
        res = testapp.post_json("/games/update_pick/G3", {}, expect_errors=True)
        assert res.status_code == 400
        assert res.json["message"] == "Invalid data."

        # Bad format resulting in ValueError
        res = testapp.post_json(
            "/games/update_pick/G3",
            {"home_team_score": "bad", "away_team_score": 5},
            expect_errors=True,
        )
        assert res.status_code == 400
        assert res.json["message"] == "Scores must be integers."

        # Negative values
        res = testapp.post_json(
            "/games/update_pick/G3",
            {"home_team_score": -1, "away_team_score": 5},
            expect_errors=True,
        )
        assert res.status_code == 400
        assert res.json["message"] == "Scores must be non-negative."
