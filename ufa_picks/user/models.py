# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from flask_login import UserMixin
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property

from ufa_picks.database import Column, PkModel, db, reference_col, relationship
from ufa_picks.extensions import bcrypt


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

    picks = db.relationship('Pick', back_populates='user', lazy='dynamic')

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
    
    @property
    def score(self):
        score = 0
        for p in self.picks:
            score += p.points
        return score

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<User({self.username!r})>"


db.Index('ix_users_username', func.lower(User.username), unique=True)
db.Index('ix_users_email', func.lower(User.email), unique=True)


class Pick(PkModel):
    """A users picks."""

    __tablename__ = "picks"
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    game_id = db.Column(db.String(18), db.ForeignKey('games.id'))
    home_team_score = db.Column(db.Integer)
    away_team_score = db.Column(db.Integer)

    game = relationship('Game', foreign_keys=[game_id], back_populates='picks')
    user = relationship('User', foreign_keys=[user_id], back_populates='picks')

    __table_args__ = (db.UniqueConstraint('user_id', 'game_id', name='unique_user_game'),)

    @property
    def winner(self):
        """The winner picked"""
        return self.game.home_team if self.home_team_score > self.away_team_score \
            else self.game.away_team

    @property
    def loser(self):
        """The loser picked"""
        return self.game.home_team if self.home_team_score < self.away_team_score \
            else self.game.away_team

    @property
    def higher_score(self):
        return self.home_team_score if self.home_team_score > self.away_team_score else self.away_team_score

    @property
    def lower_score(self):
        return self.home_team_score if self.home_team_score < self.away_team_score else self.away_team_score

    @property
    def pick_str(self):
        """Return the winner and score"""
        return f"{self.winner.team_name} {self.higher_score} - {self.lower_score}"

    @property
    def points(self):
        if self.game.status != 'Final':
            return 0
        if not self.winner.id == self.game.winner.id:
            return 0
        score = 1
        if self.home_team_score == self.game.home_score:
            score += 1
        if self.away_team_score == self.game.away_score:
            score += 1
        if abs(self.game.margin - (self.higher_score - self.lower_score)) == self.game.closest_margin:
            score += 1
        return score
