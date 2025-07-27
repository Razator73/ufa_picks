# -*- coding: utf-8 -*-
"""Game views."""
import datetime as dt

from flask import Blueprint, render_template
from flask_login import login_required

from ufa_picks.playoff.models import PlayoffTeam
from ufa_picks.user.models import User

blueprint = Blueprint("playoff", __name__, url_prefix="/playoffs", static_folder="../static")


# @login_required
@blueprint.route("/")
@login_required
def main():
    """Playoff leaderboard"""
    players = User.query.all()
    return render_template('playoff/playoffs.html', players=players)


@blueprint.route('/bracket-<int:user_id>')
@login_required
def bracket(user_id):
    user = User.get_by_id(user_id)
    return render_template('playoff/static_bracket.html', player=user)
