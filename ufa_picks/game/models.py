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
    division = Column(db.String(8))

    home_games = relationship('Game', back_populates='home_team', foreign_keys='Game.home_team_id')
    away_games = relationship('Game', back_populates='away_team', foreign_keys='Game.away_team_id')
    playoff_info = relationship('PlayoffTeam', back_populates='team', uselist=False)

    @property
    def full_name(self):
        return f'{self.team_city} {self.team_name}'

    @property
    def wins(self):
        wins = 0
        for game in self.home_games:
            if game.status == 'Final' and self.id == game.winner.id:
                wins += 1
        for game in self.away_games:
            if game.status == 'Final' and self.id == game.winner.id:
                wins += 1
        return wins

    @property
    def losses(self):
        losses = 0
        for game in self.home_games:
            if game.status == 'Final' and self.id != game.winner.id:
                losses += 1
        for game in self.away_games:
            if game.status == 'Final' and self.id != game.winner.id:
                losses += 1
        return losses

    @property
    def record(self):
        return f'{self.wins} - {self.losses}'


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
    season = Column(db.String(4), nullable=True)

    home_team = relationship('Team', back_populates='home_games', foreign_keys=[home_team_id])
    away_team = relationship('Team', back_populates='away_games', foreign_keys=[away_team_id])
    picks = relationship('Pick', back_populates='game', lazy='dynamic')
    playoff_info = relationship('PlayoffGame', back_populates='game', uselist=False)

    @property
    def winner(self):
        """The game winner"""
        if self.status == 'Final':
            return self.home_team if self.home_score > self.away_score else self.away_team
        return None

    @property
    def higher_score(self):
        if self.home_score and self.away_score:
            return self.home_score if self.home_score > self.away_score else self.away_score
        return None

    @property
    def lower_score(self):
        if self.home_score and self.away_score:
            return self.home_score if self.home_score < self.away_score else self.away_score
        return None

    @property
    def margin(self):
        return self.higher_score - self.lower_score

    @property
    def closest_margin(self):
        closest = 1000
        for p in self.picks:
            if p.winner.id == self.winner.id:
                pick_margin = p.higher_score - p.lower_score
                compare_actual = abs(self.margin - pick_margin)
                if compare_actual == 0:
                    return 0
                closest = compare_actual if compare_actual < closest else closest
        return closest
