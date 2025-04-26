# -*- coding: utf-8 -*-
"""User views."""
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from ufa_picks.extensions import db
from ufa_picks.user.models import Pick, User

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


@blueprint.route("/")
@login_required
def members():
    """Leader board"""
    players = User.query.all()
    sort_dict = {p: p.score for p in players}
    sorted_dict = sorted(sort_dict.items(), key=lambda item: item[1], reverse=True)
    players = [p[0] for p in sorted_dict]
    return render_template("users/members.html", players=players)
