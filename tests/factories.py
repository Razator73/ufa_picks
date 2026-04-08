"""Factories for creating test data."""

import datetime as dt

from factory import Sequence, SubFactory
from factory.alchemy import SQLAlchemyModelFactory

from ufa_picks.database import db
from ufa_picks.game.models import Game, Team
from ufa_picks.user.models import Pick, User


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory."""

    class Meta:
        """Factory configuration."""

        abstract = True
        sqlalchemy_session = db.session


class UserFactory(BaseFactory):
    """User factory."""

    username = Sequence(lambda n: f"user{n}")
    email = Sequence(lambda n: f"user{n}@example.com")
    first_name = Sequence(lambda n: f"First{n}")
    last_name = Sequence(lambda n: f"Last{n}")
    active = True

    class Meta:
        """Factory configuration."""

        model = User


class TeamFactory(BaseFactory):
    """Team factory."""

    id = Sequence(lambda n: f"T{n}")
    team_city = Sequence(lambda n: f"City {n}")
    team_name = Sequence(lambda n: f"Team {n}")

    class Meta:
        """Factory configuration."""

        model = Team


class GameFactory(BaseFactory):
    """Game factory."""

    id = Sequence(lambda n: f"G{n}")
    season = "2026"
    week = 1
    status = "Upcoming"
    home_team = SubFactory(TeamFactory)
    away_team = SubFactory(TeamFactory)
    streaming_url = "http://example.com"
    has_roster_report = False
    start_timestamp = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

    class Meta:
        """Factory configuration."""

        model = Game


class PickFactory(BaseFactory):
    """Pick factory."""

    user = SubFactory(UserFactory)
    game = SubFactory(GameFactory)
    home_team_score = 0
    away_team_score = 0

    class Meta:
        """Factory configuration."""

        model = Pick
