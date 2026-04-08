# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from flask_login import UserMixin
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property

from ufa_picks.database import Column, PkModel, db, reference_col, relationship
from ufa_picks.extensions import bcrypt

followers = db.Table(
    "followers",
    db.Column("follower_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("followed_id", db.Integer, db.ForeignKey("users.id")),
)


class Role(PkModel):
    """A role for a user."""

    __tablename__ = "roles"
    name = Column(db.String(80), unique=True, nullable=False)
    user_id = reference_col("users", nullable=True)
    user = relationship("User", backref="roles")

    def __init__(self, name, **kwargs):
        """Create instance."""
        super().__init__(name=name, **kwargs)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Role({self.name})>"


class User(UserMixin, PkModel):
    """A user of the app."""

    __tablename__ = "users"
    username = Column(db.String(80), unique=True, nullable=False)
    email = Column(db.String(80), unique=True, nullable=False)
    _password = Column("password", db.LargeBinary(128), nullable=True)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )
    first_name = Column(db.String(30), nullable=False)
    last_name = Column(db.String(30), nullable=False)
    active = Column(db.Boolean(), default=False)
    is_admin = Column(db.Boolean(), default=False)

    picks = db.relationship("Pick", back_populates="user", lazy="dynamic")

    followed = db.relationship(
        "User",
        secondary=followers,
        primaryjoin="followers.c.follower_id == User.id",
        secondaryjoin="followers.c.followed_id == User.id",
        backref=db.backref("followers", lazy="dynamic"),
        lazy="dynamic",
    )

    @hybrid_property
    def password(self):
        """Hashed password."""
        return self._password

    @password.setter
    def password(self, value):
        """Set password."""
        self._password = bcrypt.generate_password_hash(value)

    def check_password(self, value):
        """Check password."""
        return bcrypt.check_password_hash(self._password, value)

    @property
    def full_name(self):
        """Full user name."""
        return f"{self.first_name} {self.last_name}"

    def _get_score_2025(self, year):
        score = 0
        for p in self.picks:
            if p.game.season == year:
                score += p.points
        return score

    def _get_score_2026(self, year):
        """2026 and later logic: drop lowest regular season week if > 1 week played/passed."""
        breakdown = self.get_weekly_breakdown(year)
        return sum(item["score"] for item in breakdown if not item["is_dropped"])

    def get_weekly_breakdown(self, year):
        """Get a detailed breakdown of weekly scores, including the dropped week."""
        from ufa_picks.game.models import Game

        # Identify all regular season weeks (1-13) that have already started/passed.
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        active_weeks_query = (
            db.session.query(Game.week)
            .filter(Game.season == year, Game.week <= 13, Game.start_timestamp <= now)
            .distinct()
        )
        active_weeks = [w[0] for w in active_weeks_query.all()]

        # Initialize scores with 0 for all active weeks to account for missed weeks
        reg_season_scores = {w: 0 for w in active_weeks}
        playoff_scores = {}

        for p in self.picks:
            if p.game.season == year:
                w = p.game.week
                if w <= 13:
                    if w in reg_season_scores:
                        reg_season_scores[w] += p.points
                else:
                    playoff_scores[w] = playoff_scores.get(w, 0) + p.points

        dropped_week = None
        # Drop lowest regular season week if at least 2 weeks have occurred
        if len(reg_season_scores) > 1:
            lowest_val = min(reg_season_scores.values())
            # Find the earliest week with that lowest score to drop
            for w in sorted(reg_season_scores.keys()):
                if reg_season_scores[w] == lowest_val:
                    dropped_week = w
                    break

        breakdown = []
        # Add Regular Season
        for w in sorted(reg_season_scores.keys()):
            breakdown.append(
                {
                    "week": w,
                    "score": reg_season_scores[w],
                    "is_dropped": w == dropped_week,
                    "is_playoff": False,
                }
            )

        # Add Playoffs
        for w in sorted(playoff_scores.keys()):
            breakdown.append(
                {
                    "week": w,
                    "score": playoff_scores[w],
                    "is_dropped": False,
                    "is_playoff": True,
                }
            )

        return breakdown

    def get_weekly_score(self, year, week):
        """Get the user's score for a specific week."""
        year = str(year)
        week = int(week)
        score = 0
        for p in self.picks:
            if p.game.season == year and p.game.week == week:
                score += p.points
        return score

    def get_game_score(self, game_id):
        """Get the points earned for a specific game."""
        for p in self.picks:
            if p.game_id == str(game_id):
                return p.points
        return 0

    def get_score(self, year=None):
        """Get the user's total score for a specific year."""
        if year is None:
            year = str(dt.datetime.now().year)
        else:
            year = str(year)

        if year == "2025":
            return self._get_score_2025(year)
        elif year == "2026":
            return self._get_score_2026(year)
        else:
            return 0

    def follow(self, user):
        """Follow another user."""
        if self.id == user.id:
            return
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        """Unfollow another user."""
        if self.id == user.id:
            return
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        """Check if the user is following another user."""
        if self.id == user.id:
            return True
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<User({self.username!r})>"


db.Index("ix_users_username", func.lower(User.username), unique=True)
db.Index("ix_users_email", func.lower(User.email), unique=True)


class Pick(PkModel):
    """A users picks."""

    __tablename__ = "picks"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    game_id = db.Column(db.String(18), db.ForeignKey("games.id"))
    home_team_score = db.Column(db.Integer)
    away_team_score = db.Column(db.Integer)

    game = relationship("Game", foreign_keys=[game_id], back_populates="picks")
    user = relationship("User", foreign_keys=[user_id], back_populates="picks")

    __table_args__ = (
        db.UniqueConstraint("user_id", "game_id", name="unique_user_game"),
    )

    @property
    def winner(self):
        """The winner picked."""
        return (
            self.game.home_team
            if self.home_team_score > self.away_team_score
            else self.game.away_team
        )

    @property
    def loser(self):
        """The loser picked."""
        return (
            self.game.home_team
            if self.home_team_score < self.away_team_score
            else self.game.away_team
        )

    @property
    def higher_score(self):
        """The higher score of the pick."""
        return (
            self.home_team_score
            if self.home_team_score > self.away_team_score
            else self.away_team_score
        )

    @property
    def lower_score(self):
        """The lower score of the pick."""
        return (
            self.home_team_score
            if self.home_team_score < self.away_team_score
            else self.away_team_score
        )

    @property
    def pick_str(self):
        """Return the winner and score."""
        return f"{self.winner.team_name} {self.higher_score} - {self.lower_score}"

    def _points_2025(self):
        score = 1
        if self.home_team_score == self.game.home_score:
            score += 1
        if self.away_team_score == self.game.away_score:
            score += 1
        if (
            abs(self.game.margin - (self.higher_score - self.lower_score))
            == self.game.closest_margin
        ):
            score += 1
        return score

    def _points_2026(self):
        score = 3
        if self.home_team_score == self.game.home_score:
            score += 1
        if self.away_team_score == self.game.away_score:
            score += 1
        if (self.higher_score - self.lower_score) == self.game.margin:
            score += 1
        return score

    @property
    def points(self):
        """Calculate points for the pick based on the game's actual results."""
        if self.game.status != "Final":
            return 0
        if not self.winner.id == self.game.winner.id:
            return 0

        season_year = int(self.game.season) if self.game.season else 2025
        if season_year < 2026:
            return self._points_2025()
        else:
            return self._points_2026()
