# -*- coding: utf-8 -*-
"""User views."""
import datetime as dt

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ufa_picks.extensions import cache, db
from ufa_picks.user.forms import EditProfileForm
from ufa_picks.user.models import User

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


@cache.memoize(timeout=60)
def get_leaderboard_cache(year, week=None):
    """Calculate and return the ranked leaderboard for a given year and optional week."""
    players = User.query.filter_by(active=True).all()
    if week is not None:
        sort_dict = {
            p.id: {"user": p, "score": p.get_weekly_score(year, week)} for p in players
        }
    else:
        sort_dict = {p.id: {"user": p, "score": p.get_score(year)} for p in players}
    sorted_items = sorted(
        sort_dict.values(), key=lambda item: item["score"], reverse=True
    )

    ranked = []
    rank = 1
    for item in sorted_items:
        ranked.append({"user": item["user"], "score": item["score"], "rank": rank})
        rank += 1
    return ranked


@blueprint.app_context_processor
def inject_user_stats():
    """Inject navigation bar stats for the current user into template context."""
    if current_user and current_user.is_authenticated:
        year = str(dt.datetime.now().year)
        lb = get_leaderboard_cache(year)
        for entry in lb:
            if entry["user"].id == current_user.id:
                return {"nav_score": entry["score"], "nav_rank": entry["rank"]}
    return {}


@blueprint.route("/", defaults={"year": None})
@blueprint.route("/<string:year>/")
@login_required
def members(year):
    """Display the leaderboard and members list."""
    if year is None:
        year = str(dt.datetime.now().year)

    tab = request.args.get("tab", "top")
    query = request.args.get("q", "").lower()
    page = request.args.get("page", 1, type=int)
    week_filter = request.args.get("week", type=int)
    per_page = 10

    ranked_players = get_leaderboard_cache(year, week_filter)
    display_players = []

    if tab == "friends":
        friends_ids = [f.id for f in current_user.followed]
        friends_ids.append(current_user.id)
        display_players = [p for p in ranked_players if p["user"].id in friends_ids]
    elif tab == "all":
        if query:
            display_players = [
                p
                for p in ranked_players
                if query in p["user"].first_name.lower()
                or query in p["user"].last_name.lower()
            ]
        else:
            display_players = ranked_players
    else:  # top
        tab = "top"
        display_players = ranked_players[:7]
        # Append current user if they aren't in the top 7
        if not any(p["user"].id == current_user.id for p in display_players):
            for p in ranked_players:
                if p["user"].id == current_user.id:
                    display_players.append(p)
                    break

    total_pages = 1
    if tab == "all":
        total_pages = max(1, (len(display_players) + per_page - 1) // per_page)
        start_idx = (page - 1) * per_page
        display_players = display_players[start_idx : start_idx + per_page]

    return render_template(
        "users/members.html",
        sorted_players=display_players,
        year=year,
        tab=tab,
        query=query,
        page=page,
        total_pages=total_pages,
        week=week_filter,
    )


@blueprint.route("/profile/<int:user_id>", defaults={"year": None})
@blueprint.route("/profile/<int:user_id>/<string:year>")
@login_required
def profile(user_id, year):
    """Display a user's profile and performance history."""
    if year is None:
        year = str(dt.datetime.now().year)
    user = db.get_or_404(User, user_id)

    ranked_players = get_leaderboard_cache(year)
    user_rank = None
    user_score = user.get_score(year)
    for entry in ranked_players:
        if entry["user"].id == user.id:
            user_rank = entry["rank"]
            user_score = entry["score"]
            break

    weekly_breakdown = user.get_weekly_breakdown(year)

    return render_template(
        "users/profile.html",
        profile_user=user,
        user_rank=user_rank,
        user_score=user_score,
        weekly_breakdown=weekly_breakdown,
        year=year,
    )


@blueprint.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow(user_id):
    """Follow a user and redirect back to their profile."""
    user = db.get_or_404(User, user_id)
    if user == current_user:
        flash("You cannot follow yourself!", "warning")
        return redirect(url_for("user.profile", user_id=user_id))
    current_user.follow(user)
    db.session.commit()
    flash(f"You are now following {user.username}!", "success")
    return redirect(url_for("user.profile", user_id=user_id))


@blueprint.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Allow the current user to edit their email, password, and notification preferences."""
    form = EditProfileForm(user=current_user)
    if request.method == "GET":
        form.email.data = current_user.email
        form.get_email_reminder.data = current_user.get_email_reminder
    if form.validate_on_submit():
        current_user.email = form.email.data
        current_user.get_email_reminder = form.get_email_reminder.data
        if form.new_password.data:
            current_user.password = form.new_password.data
        current_user.save()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("user.profile", user_id=current_user.id))
    return render_template("users/edit_profile.html", form=form)


@blueprint.route("/unfollow/<int:user_id>", methods=["POST"])
@login_required
def unfollow(user_id):
    """Unfollow a user and redirect back to their profile."""
    user = db.get_or_404(User, user_id)
    if user == current_user:
        flash("You cannot unfollow yourself!", "warning")
        return redirect(url_for("user.profile", user_id=user_id))
    current_user.unfollow(user)
    db.session.commit()
    flash(f"You are no longer following {user.username}.", "info")
    return redirect(url_for("user.profile", user_id=user_id))
