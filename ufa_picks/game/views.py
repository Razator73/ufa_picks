# -*- coding: utf-8 -*-
"""Game views."""
import datetime as dt

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ufa_picks.extensions import db
from ufa_picks.game.forms import GamePick
from ufa_picks.game.models import Game
from ufa_picks.user.models import Pick, User
from ufa_picks.user.views import get_leaderboard_cache


class ManualPagination:
    """A helper class that mimics Flask-SQLAlchemy's Pagination for a simple list."""

    def __init__(self, items, page, per_page, total):
        """Create instance."""
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1
        self.next_num = page + 1

    def iter_pages(self):
        """Simple implementation of iter_pages."""
        return range(1, self.pages + 1)


blueprint = Blueprint("game", __name__, url_prefix="/games", static_folder="../static")


@blueprint.route("/", defaults={"year": None})
@blueprint.route("/<string:year>/")
@login_required
def main(year):
    """List weeks."""
    weeks = (
        Game.query.filter_by(season=year if year else str(dt.datetime.now().year))
        .with_entities(Game.week)
        .distinct()
        .order_by(Game.week)
        .all()
    )
    weeks = [w[0] for w in weeks][:13]
    return render_template("games/games.html", weeks=weeks, year=year)


def pre_lock(year, week_num):
    """Handle games and picks before the week's first game starts."""
    token_form = GamePick(prefix="token")
    week_games = (
        Game.query.filter_by(season=year, week=week_num)
        .order_by(Game.start_timestamp)
        .all()
    )
    games_with_forms = []
    for g in week_games:
        game_form = GamePick(prefix=f"game_{g.id}")
        if user_pick := Pick.query.filter_by(
            user_id=current_user.id, game_id=g.id
        ).first():
            game_form.away_team_score.data = user_pick.away_team_score
            game_form.home_team_score.data = user_pick.home_team_score
        game_dict = {"game": g, "form": game_form}
        games_with_forms.append(game_dict)

    if request.method == "POST":
        updated_picks = []
        for game_data in games_with_forms:
            form = GamePick(request.form, prefix=f'game_{game_data["game"].id}')
            if form.validate():
                game_id = game_data["game"].id
                home_score = form.home_team_score.data
                away_score = form.away_team_score.data

                pick = Pick.query.filter_by(
                    user_id=current_user.id, game_id=game_id
                ).first()
                if pick:
                    pick.home_team_score = home_score
                    pick.away_team_score = away_score
                else:
                    pick = Pick(
                        user_id=current_user.id,
                        game_id=game_id,
                        home_team_score=home_score,
                        away_team_score=away_score,
                    )
                    db.session.add(pick)
                updated_picks.append(pick)
        db.session.commit()
        flash("Your picks have been saved!", "success")
        return redirect(url_for(".week", week_num=week_num, year=year))

    # Get Top 7 for the season and Friends standings
    lb = get_leaderboard_cache(year)
    season_ranked = lb[:7]
    followed_ids = {f.id for f in current_user.followed} | {current_user.id}
    followed_season_ranked = [entry for entry in lb if entry["user"].id in followed_ids]

    return render_template(
        "games/pre_week.html",
        games=games_with_forms,
        week_num=week_num,
        year=year,
        form=token_form,
        season_ranked=season_ranked,
        followed_season_ranked=followed_season_ranked,
    )


@blueprint.route("/update_pick/<string:game_id>", methods=["POST"])
@login_required
def update_pick(game_id):
    """Update a user's pick for a specific game via JSON API."""
    game = db.get_or_404(Game, game_id)

    if dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) > game.start_timestamp:
        return jsonify({"status": "error", "message": "Game has already started."}), 400

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid data."}), 400

    try:
        home_score = data.get("home_team_score")
        away_score = data.get("away_team_score")

        home_score = int(home_score) if home_score not in [None, ""] else None
        away_score = int(away_score) if away_score not in [None, ""] else None

        if (home_score is not None and home_score < 0) or (
            away_score is not None and away_score < 0
        ):
            return (
                jsonify({"status": "error", "message": "Scores must be non-negative."}),
                400,
            )
    except ValueError:
        return jsonify({"status": "error", "message": "Scores must be integers."}), 400

    pick = Pick.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if pick:
        pick.home_team_score = home_score
        pick.away_team_score = away_score
    else:
        pick = Pick(
            user_id=current_user.id,
            game_id=game_id,
            home_team_score=home_score,
            away_team_score=away_score,
        )
        db.session.add(pick)

    db.session.commit()
    return jsonify({"status": "success", "message": "Pick saved."})


def post_lock(year, week_num):
    """Display games and picks after the week's first game has started (read-only)."""
    week_games = (
        Game.query.filter_by(season=year, week=week_num)
        .order_by(Game.start_timestamp)
        .all()
    )
    # Get Top 7 for the week and Friends standings
    lb = get_leaderboard_cache(year, week=week_num)
    week_ranked = lb[:7]
    followed_ids = {f.id for f in current_user.followed} | {current_user.id}
    followed_week_ranked = [entry for entry in lb if entry["user"].id in followed_ids]

    # Get current user's picks for this week
    user_picks = {
        p.game_id: p
        for p in Pick.query.filter_by(user_id=current_user.id).all()
        if p.game.season == year and p.game.week == week_num
    }

    return render_template(
        "games/post_week.html",
        games=week_games,
        week_num=week_num,
        year=year,
        week_ranked=week_ranked,
        followed_week_ranked=followed_week_ranked,
        user_picks=user_picks,
    )


@blueprint.route("/<string:year>/game/<string:game_id>", methods=["GET", "POST"])
@login_required
def game_details(year, game_id):
    """Display details and all picks for a single game."""
    game = db.get_or_404(Game, game_id)
    # Determine if the week is locked based on the first game of that week
    first_game = (
        Game.query.filter_by(season=year, week=game.week)
        .order_by(Game.start_timestamp)
        .first()
    )
    lock = (
        dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        > first_game.start_timestamp
    )

    user_pick = Pick.query.filter_by(user_id=current_user.id, game_id=game_id).first()

    if not lock:
        form = GamePick(request.form, prefix=f"game_{game.id}")
        if request.method == "POST" and form.validate():
            if not user_pick:
                user_pick = Pick(user_id=current_user.id, game_id=game_id)
                db.session.add(user_pick)
            user_pick.home_team_score = form.home_team_score.data
            user_pick.away_team_score = form.away_team_score.data
            db.session.commit()
            flash("Pick updated!", "success")
            return redirect(url_for(".game_details", year=year, game_id=game_id))

        if user_pick and request.method == "GET":
            form.home_team_score.data = user_pick.home_team_score
            form.away_team_score.data = user_pick.away_team_score

        return render_template(
            "games/game_details.html", game=game, form=form, lock=lock, year=year
        )

    # Post-lock: show all picks
    followed_picks = []
    if current_user.followed.count() > 0:
        followed_ids = [u.id for u in current_user.followed.all()]
        followed_ids.append(current_user.id)
        followed_picks = (
            Pick.query.filter(Pick.game_id == game_id, Pick.user_id.in_(followed_ids))
            .join(User)
            .all()
        )
        followed_picks.sort(key=lambda p: (-p.points, p.user.last_name))

    page = request.args.get("page", 1, type=int)
    per_page = 10

    # Fetch all picks to sort by points (non-SQL property)
    all_p = Pick.query.filter_by(game_id=game_id).join(User).all()
    all_p.sort(key=lambda p: (-p.points, p.user.last_name))

    total = len(all_p)
    items = all_p[(page - 1) * per_page : page * per_page]
    picks_pagination = ManualPagination(items, page, per_page, total)

    return render_template(
        "games/game_details.html",
        game=game,
        picks_pagination=picks_pagination,
        followed_picks=followed_picks,
        user_pick=user_pick,
        lock=lock,
        year=year,
    )


@blueprint.route(
    "/week-<int:week_num>", methods=["GET", "POST"], defaults={"year": None}
)
@blueprint.route("/<string:year>/week-<int:week_num>", methods=["GET", "POST"])
@login_required
def week(week_num, year):
    """View and submit picks for a specific week."""
    if year is None:
        year = str(dt.datetime.now().year)

    if week_num > 13:
        return render_template("games/post_season.html", year=year)
    first_game = (
        Game.query.filter_by(season=year, week=week_num)
        .order_by(Game.start_timestamp)
        .first()
    )
    if not first_game:
        flash("No games found for this week.", "warning")
        return redirect(url_for(".main", year=year))

    lock = (
        dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        > first_game.start_timestamp
    )
    if lock:
        return post_lock(year, week_num)
    else:
        return pre_lock(year, week_num)
