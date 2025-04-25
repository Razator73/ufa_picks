# -*- coding: utf-8 -*-
"""User views."""
from flask import Blueprint, render_template
from flask_login import login_required

from ufa_picks.game.models import Game, Team

blueprint = Blueprint("game", __name__, url_prefix="/games", static_folder="../static")


# @login_required
@blueprint.route("/")
def members():
    """List members."""
    return render_template("games/games.html")
