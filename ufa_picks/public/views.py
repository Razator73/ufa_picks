# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
import datetime as dt

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, login_user, logout_user

from ufa_picks.extensions import login_manager
from ufa_picks.game.models import Game
from ufa_picks.public.forms import LoginForm
from ufa_picks.user.forms import RegisterForm
from ufa_picks.user.models import Pick, User
from ufa_picks.utils import flash_errors

blueprint = Blueprint("public", __name__, static_folder="../static")


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@blueprint.route("/", methods=["GET", "POST"])
def home():
    """Home page."""
    form = LoginForm(request.form)
    current_app.logger.info("Hello from the home page!")
    # Handle logging in
    if request.method == "POST":
        if form.validate_on_submit():
            login_user(form.user)
            flash("You are logged in.", "success")
            redirect_url = request.args.get("next") or url_for("user.members")
            return redirect(redirect_url)
        else:
            flash_errors(form)

    year = str(dt.datetime.now().year)
    first_game = (
        Game.query.filter_by(season=year).order_by(Game.start_timestamp).first()
    )
    first_game_time = (
        first_game.start_timestamp.isoformat() + "Z"
        if first_game and first_game.start_timestamp
        else None
    )

    last_game = (
        Game.query.filter_by(season=year, status="Final")
        .order_by(Game.start_timestamp.desc())
        .first()
    )
    top_scorers = []
    top_week = None
    if last_game:
        top_week = last_game.week
        picks = (
            Pick.query.join(Game)
            .filter(Game.season == year, Game.week == top_week, Game.status == "Final")
            .all()
        )
        scores = {}
        for p in picks:
            scores[p.user_id] = scores.get(p.user_id, 0) + p.points

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        for uid, sc in sorted_scores:
            u_obj = User.get_by_id(uid)
            if u_obj:
                top_scorers.append({"user": u_obj, "score": sc})

    return render_template(
        "public/home.html",
        form=form,
        first_game_time=first_game_time,
        top_scorers=top_scorers,
        top_week=top_week,
    )


@blueprint.route("/logout/")
@login_required
def logout():
    """Logout."""
    logout_user()
    flash("You are logged out.", "info")
    return redirect(url_for("public.home"))


@blueprint.route("/register/", methods=["GET", "POST"])
def register():
    """Register new user."""
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        User.create(
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=form.password.data,
            active=True,
        )
        flash("Thank you for registering. You can now log in.", "success")
        return redirect(url_for("public.home"))
    else:
        flash_errors(form)
    return render_template("public/register.html", form=form)


@blueprint.route("/about/")
def about():
    """About page."""
    form = LoginForm(request.form)
    return render_template("public/about.html", form=form)
