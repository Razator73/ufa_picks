# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
import datetime as dt
import secrets
import string

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from ufa_picks.email_utils import send_temp_password_email, send_welcome_email
from ufa_picks.extensions import login_manager
from ufa_picks.game.models import Game
from ufa_picks.public.forms import ChangePasswordForm, ForgotPasswordForm, LoginForm
from ufa_picks.user.forms import RegisterForm
from ufa_picks.user.models import User
from ufa_picks.utils import flash_errors

blueprint = Blueprint("public", __name__, static_folder="../static")

login_manager.login_view = "public.login"


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@blueprint.route("/", methods=["GET"])
def home():
    """Home page."""
    current_app.logger.info("Hello from the home page!")

    year = str(dt.datetime.now().year)
    first_game = (
        Game.query.filter_by(season=year).order_by(Game.start_timestamp).first()
    )
    first_game_time = (
        first_game.start_timestamp.isoformat() + "Z"
        if first_game and first_game.start_timestamp
        else None
    )

    # To pick current week it is the week that has a game in the future
    # from 26 hours ago. This will hold current week the same for
    # 26 hours after the last game of the week starts.
    buffer = dt.timedelta(hours=26)
    now = dt.datetime.now(dt.timezone.utc)
    current_week_game = (
        Game.query.filter(Game.season == year)
        .filter(Game.start_timestamp > (now - buffer))
        .order_by(Game.start_timestamp.asc())
        .first()
    )

    if current_week_game:
        current_week = current_week_game.week
    else:
        last_game = (
            Game.query.filter(Game.season == year)
            .order_by(Game.start_timestamp.desc())
            .first()
        )
        current_week = last_game.week if last_game else None

    return render_template(
        "public/home.html",
        first_game_time=first_game_time,
        current_week=current_week,
        year=year,
    )


@blueprint.route("/login/", methods=["GET", "POST"])
def login():
    """Dedicated login page."""
    if current_user.is_authenticated:
        return redirect(url_for("user.members"))
    form = LoginForm(request.form)
    if request.method == "POST":
        if form.validate_on_submit():
            login_user(form.user, remember=True)
            if form.user.force_password_change:
                flash("Your password is temporary. Please set a new one.", "warning")
                return redirect(url_for("public.change_password"))
            flash("You are logged in.", "success")
            redirect_url = request.args.get("next") or url_for("user.members")
            return redirect(redirect_url)
        else:
            flash_errors(form)
            return redirect(url_for("public.home", open_modal="login"))
    return render_template("public/login.html", login_form=form)


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
    register_form = RegisterForm(request.form)
    if register_form.validate_on_submit():
        user = User.create(
            username=register_form.username.data,
            first_name=register_form.first_name.data,
            last_name=register_form.last_name.data,
            email=register_form.email.data,
            password=register_form.password.data,
            active=True,
        )
        try:
            send_welcome_email(user)
        except Exception:
            current_app.logger.exception(
                "Failed to send welcome email to %s", user.email
            )
        flash("Thank you for registering. You can now log in.", "success")
        return redirect(url_for("public.home"))
    else:
        flash_errors(register_form)
        return redirect(url_for("public.home", open_modal="register"))


@blueprint.route("/forgot-password/", methods=["GET", "POST"])
def forgot_password():
    """Send a temporary password to the user's email."""
    forgot_form = ForgotPasswordForm(request.form)
    if request.method == "POST" and forgot_form.validate_on_submit():
        identifier = forgot_form.username_or_email.data.strip()
        user = User.query.filter_by(username=identifier).first()
        if not user:
            user = User.query.filter(
                func.lower(User.email) == identifier.lower()
            ).first()
        if user and user.email:
            temp_password = "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(10)
            )
            user.password = temp_password
            user.force_password_change = True
            user.save()
            try:
                send_temp_password_email(user, temp_password)
            except Exception:
                current_app.logger.exception("Failed to send temp password email")
        flash(
            "If that username/email exists, a temporary password has been sent to the associated email.",
            "info",
        )
        return redirect(url_for("public.home"))
    return redirect(url_for("public.home", open_modal="forgot"))


@blueprint.route("/change-password/", methods=["GET", "POST"])
@login_required
def change_password():
    """Force password change after temp password login."""
    if not current_user.force_password_change:
        return redirect(url_for("user.members"))
    form = ChangePasswordForm(request.form)
    if request.method == "POST" and form.validate_on_submit():
        current_user.password = form.new_password.data
        current_user.force_password_change = False
        current_user.save()
        flash("Password changed successfully.", "success")
        return redirect(url_for("user.members"))
    return render_template("public/change_password.html", form=form)


@blueprint.route("/about/")
def about():
    """About page."""
    return render_template("public/about.html")
