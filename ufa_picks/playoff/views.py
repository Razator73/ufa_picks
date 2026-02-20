# -*- coding: utf-8 -*-
"""Game views."""
import datetime as dt

from flask import Blueprint, render_template
from flask_login import login_required

from ufa_picks.playoff.models import PlayoffTeam

blueprint = Blueprint("playoff", __name__, url_prefix="/playoffs", static_folder="../static")


# @login_required
@blueprint.route("/")
@login_required
def main():
    """List weeks."""
    return render_template('playoff/playoffs.html')
