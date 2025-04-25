# -*- coding: utf-8 -*-
"""Game forms."""
from flask_wtf import FlaskForm
from wtforms import IntegerField, HiddenField
from wtforms.validators import NumberRange

from .models import Game


class GamePick(FlaskForm):
    """Pick scores for a game"""

    game_id = HiddenField()
    away_team_score = IntegerField("Away Team", validators=[NumberRange(min=0, max=None,
                                                                        message="Must be a non-negative number")])
    home_team_score = IntegerField("Home Team", validators=[NumberRange(min=0, max=None,
                                                                        message="Must be a non-negative number")])
