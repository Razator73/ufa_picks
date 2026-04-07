# -*- coding: utf-8 -*-
"""User view tests."""


class TestUserViews:
    """Test user views."""

    def login(self, user, testapp):
        """Login user."""
        res = testapp.get("/")
        form = res.forms["loginForm"]
        form["username"] = user.username
        form["password"] = "myprecious"
        res = form.submit().follow()
        return res

    def test_members(self, user, testapp, db):
        """Test members page."""
        self.login(user, testapp)
        res = testapp.get("/users/")
        assert res.status_code == 200

        res = testapp.get("/users/2026/")
        assert res.status_code == 200

    def test_members_friends_tab(self, user, testapp, db):
        """Test members friends tab."""
        self.login(user, testapp)
        res = testapp.get("/users/?tab=friends")
        assert res.status_code == 200

    def test_members_all_tab(self, user, testapp, db):
        """Test members all tab."""
        from tests.factories import UserFactory

        other = UserFactory(
            username="other", active=True, first_name="Other", last_name="Guy"
        )
        db.session.add(other)
        db.session.commit()

        self.login(user, testapp)
        res = testapp.get("/users/?tab=all")
        assert res.status_code == 200
        assert "Other" in res.text

        res = testapp.get("/users/?tab=all&q=Other")
        assert res.status_code == 200
        assert "Other" in res.text

    def test_profile_page(self, user, testapp, db):
        """Test profile page."""
        self.login(user, testapp)
        res = testapp.get(f"/users/profile/{user.id}")
        assert res.status_code == 200
        assert user.full_name in res.text

    def test_follow_unfollow(self, user, testapp, db):
        """Test follow/unfollow logic."""
        from tests.factories import UserFactory

        other = UserFactory(username="target", active=True)
        db.session.add(other)
        db.session.commit()

        self.login(user, testapp)

        res = testapp.post(f"/users/follow/{other.id}").follow()
        assert res.status_code == 200
        assert "You are now following target" in res.text
        assert user.is_following(other)

        res = testapp.post(f"/users/unfollow/{other.id}").follow()
        assert res.status_code == 200
        assert "You are no longer following target" in res.text
        assert not user.is_following(other)

        res = testapp.post(f"/users/follow/{user.id}").follow()
        assert "You cannot follow yourself!" in res.text

        res = testapp.post(f"/users/unfollow/{user.id}").follow()
        assert "You cannot unfollow yourself!" in res.text
