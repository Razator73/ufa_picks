# -*- coding: utf-8 -*-
"""Game models."""
import datetime as dt

from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property

from ufa_picks.database import Column, Model, PkModel, db, reference_col, relationship
from ufa_picks.extensions import bcrypt


class PlayoffTeam(Model):
    """ A store team info"""

    __tablename__ = 'playoff_teams'
    id = Column(db.String(30), db.ForeignKey('teams.id'), primary_key=True)
    division_seed = Column(db.Integer, nullable=False)
    overall_seed = Column(db.Integer, nullable=False)

    team = relationship('Team', back_populates='playoff_info')


class PlayoffGame(Model):

    __tablename__ = 'playoff_games'

    id = Column(db.String(18), db.ForeignKey('games.id'), primary_key=True)
    game_title = Column(db.String(32), nullable=False)

    game = relationship('Game', back_populates='playoff_info')
