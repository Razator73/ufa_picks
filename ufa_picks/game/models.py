# -*- coding: utf-8 -*-
"""Game models."""
from ufa_picks.database import Column, Model, db, relationship


class CancelledGame(Model):
    """A game that was cancelled and must be excluded from views and scoring.

    This lives in its own table on purpose. Game rows are refreshed from an
    external source that overwrites the ``games`` table (including ``status``)
    on every load, so marking the game as cancelled there would not survive a
    sync. The loader never touches this table, so entries here persist. Adding a
    future cancellation is a single ``INSERT`` — no code change required.
    """

    __tablename__ = "cancelled_games"
    game_id = Column(db.String(18), primary_key=True)


def cancelled_game_ids():
    """Return the set of game ids that have been cancelled.

    Fetch this once and reuse it within scoring/view loops rather than querying
    per game or per pick.
    """
    return {c.game_id for c in CancelledGame.query.all()}


class Team(Model):
    """A store team info."""

    __tablename__ = "teams"
    id = Column(db.String(30), primary_key=True)
    team_city = Column(db.String(30), nullable=False)
    team_name = Column(db.String(30), nullable=False)

    home_games = relationship(
        "Game", back_populates="home_team", foreign_keys="Game.home_team_id"
    )
    away_games = relationship(
        "Game", back_populates="away_team", foreign_keys="Game.away_team_id"
    )

    @property
    def full_name(self):
        """Team full name."""
        return f"{self.team_city} {self.team_name}"

    @property
    def schedule_link(self):
        """Hyper link to the team's schedule"""
        return f'<a href="https://www.watchufa.com/{self.id}/schedule" target="_blank" rel="noopener">{self.full_name}</a>'

    def wins(self, season):
        """Calculate wins for a season."""
        wins = 0
        season_str = str(season)
        for game in self.home_games:
            if (
                game.season == season_str
                and game.status == "Final"
                and self.id == game.winner.id
            ):
                wins += 1
        for game in self.away_games:
            if (
                game.season == season_str
                and game.status == "Final"
                and self.id == game.winner.id
            ):
                wins += 1
        return wins

    def losses(self, season):
        """Calculate losses for a season."""
        losses = 0
        season_str = str(season)
        for game in self.home_games:
            if (
                game.season == season_str
                and game.status == "Final"
                and self.id != game.winner.id
            ):
                losses += 1
        for game in self.away_games:
            if (
                game.season == season_str
                and game.status == "Final"
                and self.id != game.winner.id
            ):
                losses += 1
        return losses

    def record(self, season):
        """Get team record string."""
        return f"{self.wins(season)} - {self.losses(season)}"


class Game(Model):
    """Store game info."""

    __tablename__ = "games"
    id = Column(db.String(18), primary_key=True)
    home_team_id = Column(db.String(30), db.ForeignKey("teams.id"))
    away_team_id = Column(db.String(30), db.ForeignKey("teams.id"))
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

    home_team = relationship(
        "Team", back_populates="home_games", foreign_keys=[home_team_id]
    )
    away_team = relationship(
        "Team", back_populates="away_games", foreign_keys=[away_team_id]
    )
    picks = relationship("Pick", back_populates="game", lazy="dynamic")

    @property
    def is_cancelled(self):
        """Whether this game has been cancelled (excluded from views and scoring)."""
        return db.session.get(CancelledGame, self.id) is not None

    @property
    def winner(self):
        """The game winner."""
        if self.status == "Final":
            return (
                self.home_team if self.home_score > self.away_score else self.away_team
            )
        return None

    @property
    def higher_score(self):
        """Get the higher score."""
        if self.home_score is not None and self.away_score is not None:
            return (
                self.home_score
                if self.home_score > self.away_score
                else self.away_score
            )
        return None

    @property
    def lower_score(self):
        """Get the lower score."""
        if self.home_score is not None and self.away_score is not None:
            return (
                self.home_score
                if self.home_score < self.away_score
                else self.away_score
            )
        return None

    @property
    def margin(self):
        """Calculate score margin."""
        return self.higher_score - self.lower_score

    @property
    def closest_margin(self):
        """Find the closest margin from user picks."""
        closest = 1000
        for p in self.picks:
            if p.winner.id == self.winner.id:
                pick_margin = p.higher_score - p.lower_score
                compare_actual = abs(self.margin - pick_margin)
                if compare_actual == 0:
                    return 0
                closest = compare_actual if compare_actual < closest else closest
        return closest
