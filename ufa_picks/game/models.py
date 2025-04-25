# -*- coding: utf-8 -*-
"""Game models."""
import datetime as dt

from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property

from ufa_picks.database import Column, Model, PkModel, db, reference_col, relationship
from ufa_picks.extensions import bcrypt


class Team(Model):
    """ A store team info"""

    __tablename__ = 'teams'
    id = Column(db.String(30), primary_key=True)
    team_city = Column(db.String(30), nullable=False)
    team_name = Column(db.String(30), nullable=False)

    home_games = relationship('Game', foreign_keys='[Game.home_team_id]', backref='home_team_association')
    away_games = relationship('Game', foreign_keys='[Game.away_team_id]', backref='away_team_association')


class Game(Model):
    """ Store game info """

    __tablename__ = 'games'
    id = Column(db.String(18), primary_key=True)
    home_team_id = Column(db.String(30), db.ForeignKey('teams.id'))
    away_team_id = Column(db.String(30), db.ForeignKey('teams.id'))
    home_score = Column(db.Integer)
    away_score = Column(db.Integer)
    status = Column(db.String(30), nullable=False)
    week = Column(db.Integer, nullable=False)
    streaming_url = Column(db.String(256), nullable=False)
    has_roster_report = Column(db.Boolean(), nullable=False)
    start_timestamp = Column(db.DateTime)
    start_timezone = Column(db.String(8))
    start_time_tbd = Column(db.Boolean())

    home_team = relationship('Team', foreign_keys=[home_team_id], backref='games_as_home')
    away_team = relationship('Team', foreign_keys=[away_team_id], backref='games_as_away')
