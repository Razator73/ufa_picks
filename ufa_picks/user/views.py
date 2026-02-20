# -*- coding: utf-8 -*-
"""User views."""
import datetime as dt

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from ufa_picks.extensions import db
from ufa_picks.user.models import Pick, User

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


@blueprint.route("/", defaults={"year": None})
@blueprint.route("/<string:year>/")
@login_required
def members(year):
    if year is None:
        year = str(dt.datetime.now().year)
    """Leader board"""
    players = User.query.all()
    sort_dict = {p: p.get_score(year) for p in players}
    sorted_dict = sorted(sort_dict.items(), key=lambda item: item[1], reverse=True)
    return render_template("users/members.html", sorted_players=sorted_dict, year=year)
