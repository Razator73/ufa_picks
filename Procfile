release: flask db upgrade
web: gunicorn ufa_picks.app:create_app\(\) -b 0.0.0.0:$PORT -w 3
