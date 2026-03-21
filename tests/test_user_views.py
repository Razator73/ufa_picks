# -*- coding: utf-8 -*-
"""User view tests."""
import pytest
from flask import url_for


class TestUserViews:
    def login(self, user, testapp):
        res = testapp.get("/")
        form = res.forms["loginForm"]
        form["username"] = user.username
        form["password"] = "myprecious"
        res = form.submit().follow()
        return res

    def test_members(self, user, testapp, db):
        self.login(user, testapp)
        res = testapp.get("/users/")
        assert res.status_code == 200

        res = testapp.get("/users/2026/")
        assert res.status_code == 200
