# -*- coding: utf-8 -*-
"""Game views."""
import datetime as dt

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_required

from ufa_picks.extensions import db
from ufa_picks.game.models import Game, Team
from ufa_picks.game.forms import GamePick
from ufa_picks.user.models import Pick

blueprint = Blueprint("game", __name__, url_prefix="/games", static_folder="../static")


@blueprint.route("/", defaults={"year": None})
@blueprint.route("/<string:year>/")
@login_required
def main(year):
    """List weeks."""
    weeks = Game.query\
        .filter_by(season=year if year else str(dt.datetime.now().year))\
        .with_entities(Game.week)\
        .distinct()\
        .order_by(Game.week)\
        .all()
    weeks = [w[0] for w in weeks][:13]
    return render_template("games/games.html", weeks=weeks, year=year)


def pre_lock(year, week_num):
    token_form = GamePick(prefix='token')
    week_games = Game.query.filter_by(season=year, week=week_num).order_by(Game.start_timestamp).all()
    games_with_forms = []
    for g in week_games:
        game_form = GamePick(prefix=f'game_{g.id}')
        if user_pick := Pick.query.filter_by(user_id=current_user.id, game_id=g.id).first():
            game_form.away_team_score.data = user_pick.away_team_score
            game_form.home_team_score.data = user_pick.home_team_score
        game_dict = {'game': g,
                     'form': game_form}
        games_with_forms.append(game_dict)

    if request.method == 'POST':
        updated_picks = []
        for game_data in games_with_forms:
            form = GamePick(request.form, prefix=f'game_{game_data["game"].id}')
            if form.validate():
                game_id = game_data['game'].id
                home_score = form.home_team_score.data
                away_score = form.away_team_score.data

                pick = Pick.query.filter_by(user_id=current_user.id, game_id=game_id).first()
                if pick:
                    pick.home_team_score = home_score
                    pick.away_team_score = away_score
                else:
                    pick = Pick(user_id=current_user.id, game_id=game_id,
                                home_team_score=home_score, away_team_score=away_score)
                    db.session.add(pick)
                updated_picks.append(pick)
        db.session.commit()
        flash('Your picks have been saved!', 'success')
        return redirect(url_for('.week', week_num=week_num, year=year))

    return render_template('games/pre_week.html', games=games_with_forms, week_num=week_num, year=year, form=token_form)


def post_lock(year, week_num):
    week_games = Game.query.filter_by(season=year, week=week_num).order_by(Game.start_timestamp).all()
    return render_template('games/post_week.html', games=week_games, week_num=week_num, year=year)


@blueprint.route('/week-<int:week_num>', methods=['GET', 'POST'], defaults={'year': None})
@blueprint.route('/<string:year>/week-<int:week_num>', methods=['GET', 'POST'])
@login_required
def week(week_num, year):
    if year is None:
        year = str(dt.datetime.now().year)

    if week_num > 13:
        return render_template('games/post_season.html', year=year)
    first_game = Game.query.filter_by(season=year, week=week_num).order_by(Game.start_timestamp).first()
    if not first_game:
        flash('No games found for this week.', 'warning')
        return redirect(url_for('.main', year=year))

    lock = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) > first_game.start_timestamp
    if lock:
        return post_lock(year, week_num)
    else:
        return pre_lock(year, week_num)
