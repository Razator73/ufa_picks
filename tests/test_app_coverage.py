# -*- coding: utf-8 -*-
"""App level coverage tests."""
from ufa_picks.public.views import load_user


def test_load_user(user, db):
    user.save()
    loaded = load_user(str(user.id))
    assert loaded == user


def test_error_handlers(testapp):
    # 404
    res = testapp.get("/not-found-route", expect_errors=True)
    assert res.status_code == 404

    # 401 is hard to trigger casually without a protected route returning it directly
    # 500 is also tricky without an unhandled exception route.
    # Coverage for `render_error(error)` is triggered by the 404.


def test_shell_context(app):
    ctx = app.make_shell_context()
    assert "db" in ctx
    assert "User" in ctx
    assert "Game" in ctx
