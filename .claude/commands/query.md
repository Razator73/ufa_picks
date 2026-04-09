Run a SELECT query against the UFA Picks database and display the results.

Steps:
1. The user will provide a SQL SELECT statement as `$ARGUMENTS`. If no arguments are given, ask the user for the query before proceeding.
2. Security check: only proceed if the query starts with SELECT (case-insensitive, ignoring leading whitespace). Refuse any other statement type.
3. Run the query via the Docker container using the Bash tool with this command (substitute the actual query for QUERY):

```
docker compose exec flask-dev python3 -c "
import os, psycopg2, csv, sys
url = os.environ['DATABASE_URL'].replace('+psycopg2', '')
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute('''QUERY''')
rows = cur.fetchall()
cols = [d[0] for d in cur.description]
w = csv.writer(sys.stdout)
w.writerow(cols)
w.writerows(rows)
"
```

4. Parse the CSV output and display results as a markdown table. If there are no rows, say so. If there is an error, show it clearly.
