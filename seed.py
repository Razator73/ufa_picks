"""Seed the dev database with realistic UFA data for local development."""
import datetime as dt
import random

from autoapp import app
from ufa_picks.extensions import db
from ufa_picks.game.models import Game, Team
from ufa_picks.user.models import User

SEASON = "2026"

TEAMS = [
    ("atl-hustle",    "Atlanta",      "Hustle"),
    ("aus-sol",       "Austin",       "Sol"),
    ("chi-windchill", "Chicago",      "Windchill"),
    ("dal-roughnecks","Dallas",       "Roughnecks"),
    ("dc-breeze",     "DC",           "Breeze"),
    ("den-summit",    "Denver",       "Summit"),
    ("min-wind",      "Minnesota",    "Wind Chill"),
    ("ny-empire",     "New York",     "Empire"),
    ("phi-phoenix",   "Philadelphia", "Phoenix"),
    ("pit-thunderbirds","Pittsburgh", "Thunderbirds"),
    ("rdu-phoenix",   "Raleigh",      "Phoenix"),
    ("sea-cascades",  "Seattle",      "Cascades"),
]

# (away_id, home_id, week, start_offset_days, home_score, away_score, status)
# Weeks 1-4 are Final, week 5 is In Progress, week 6 is Upcoming
GAME_TEMPLATE = [
    ("atl-hustle",     "chi-windchill", 1, -35, 19, 15, "Final"),
    ("ny-empire",      "dc-breeze",     1, -35, 22, 18, "Final"),
    ("sea-cascades",   "den-summit",    1, -35, 20, 21, "Final"),
    ("phi-phoenix",    "pit-thunderbirds",1,-35,17, 20, "Final"),
    ("aus-sol",        "dal-roughnecks",2, -28, 18, 22, "Final"),
    ("min-wind",       "rdu-phoenix",   2, -28, 21, 14, "Final"),
    ("dc-breeze",      "atl-hustle",    2, -28, 16, 19, "Final"),
    ("chi-windchill",  "ny-empire",     2, -28, 23, 20, "Final"),
    ("den-summit",     "phi-phoenix",   3, -21, 20, 17, "Final"),
    ("pit-thunderbirds","sea-cascades", 3, -21, 18, 21, "Final"),
    ("dal-roughnecks", "min-wind",      3, -21, 22, 19, "Final"),
    ("rdu-phoenix",    "aus-sol",       3, -21, 15, 18, "Final"),
    ("atl-hustle",     "ny-empire",     4, -14, 20, 22, "Final"),
    ("dc-breeze",      "chi-windchill", 4, -14, 18, 16, "Final"),
    ("sea-cascades",   "pit-thunderbirds",4,-14,21,17,  "Final"),
    ("den-summit",     "dal-roughnecks",4, -14, 19, 23, "Final"),
    ("phi-phoenix",    "rdu-phoenix",   5,   2, None, None, "In Progress"),
    ("aus-sol",        "min-wind",      5,   3, None, None, "In Progress"),
    ("ny-empire",      "atl-hustle",    6,   7, None, None, "Upcoming"),
    ("chi-windchill",  "dc-breeze",     6,   7, None, None, "Upcoming"),
]

USERS = [
    ("admin",   "admin@ufapicks.dev",   "Admin",   "User",   "password", True),
    ("alice",   "alice@ufapicks.dev",   "Alice",   "Smith",  "password", False),
    ("bob",     "bob@ufapicks.dev",     "Bob",     "Jones",  "password", False),
    ("carol",   "carol@ufapicks.dev",   "Carol",   "White",  "password", False),
    ("dave",    "dave@ufapicks.dev",    "Dave",    "Brown",  "password", False),
]


def seed():
    with app.app_context():
        print("Clearing existing seed data...")
        db.session.execute(db.text("DELETE FROM picks"))
        db.session.execute(db.text("DELETE FROM followers"))
        db.session.execute(db.text("DELETE FROM games"))
        db.session.execute(db.text("DELETE FROM teams"))
        db.session.execute(db.text("DELETE FROM users"))
        db.session.commit()

        print("Creating teams...")
        for team_id, city, name in TEAMS:
            db.session.add(Team(id=team_id, team_city=city, team_name=name))
        db.session.commit()

        print("Creating games...")
        now = dt.datetime.utcnow()
        for i, (away_id, home_id, week, offset, hscore, ascore, status) in enumerate(GAME_TEMPLATE):
            game_id = f"2026-w{week:02d}-g{i:02d}"
            start = now + dt.timedelta(days=offset)
            start = start.replace(hour=19, minute=0, second=0, microsecond=0)
            db.session.add(Game(
                id=game_id,
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=hscore,
                away_score=ascore,
                status=status,
                week=week,
                season=SEASON,
                streaming_url="https://ultiworld.com",
                has_roster_report=False,
                start_timestamp=start,
                start_timezone="ET",
                start_time_tbd=False,
            ))
        db.session.commit()

        print("Creating users...")
        users = []
        for username, email, first, last, pw, is_admin in USERS:
            u = User(
                username=username,
                email=email,
                first_name=first,
                last_name=last,
                active=True,
                is_admin=is_admin,
                get_email_reminder=False,
                force_password_change=False,
            )
            u.password = pw
            db.session.add(u)
            users.append(u)
        db.session.commit()

        print("Creating picks for completed games...")
        from ufa_picks.user.models import Pick
        final_games = Game.query.filter_by(season=SEASON, status="Final").all()
        for user in users:
            for game in final_games:
                # Randomise picks slightly around actual scores
                h_pick = max(0, game.home_score + random.randint(-3, 3))
                a_pick = max(0, game.away_score + random.randint(-3, 3))
                # Occasionally pick the exact score
                if random.random() < 0.15:
                    h_pick, a_pick = game.home_score, game.away_score
                db.session.add(Pick(
                    user_id=user.id,
                    game_id=game.id,
                    home_team_score=h_pick,
                    away_team_score=a_pick,
                ))
        db.session.commit()

        print("Creating follow relationships...")
        for i, u in enumerate(users):
            for j, other in enumerate(users):
                if i != j and random.random() < 0.6:
                    u.follow(other)
        db.session.commit()

        print("\nDone! Seeded:")
        print(f"  {len(TEAMS)} teams")
        print(f"  {len(GAME_TEMPLATE)} games (weeks 1-6)")
        print(f"  {len(users)} users  (all passwords: 'password')")
        print(f"  Picks for all completed games")
        print("\nLogin at http://localhost:5000 with any username above.")


if __name__ == "__main__":
    seed()
