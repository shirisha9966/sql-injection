"""
app_secure.py
-------------
Secure counterpart to app_vulnerable.py.

The ONLY meaningful difference is how user input reaches the SQL
engine: here it is passed as bound parameters (the `?` placeholders),
never concatenated into the query string. The database driver sends
the query text and the data separately, so attacker input can never
change the *structure* of the query — it can only ever be treated as
a literal value to compare against.

Run with:
    python app_secure.py
Then visit http://127.0.0.1:5001/

Try the same injection payload that worked against the vulnerable app:
    Username: ' OR '1'='1' --
    Password: anything
...and confirm it correctly fails to log in.
"""

import sqlite3
import os
from flask import Flask, request, render_template, g

DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")

app = Flask(__name__)
app.secret_key = "demo-only-not-for-production"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    user = None
    executed_query = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        db = get_db()
        cur = db.cursor()

        # ------------------------------------------------------------
        # SECURE: the `?` placeholders are bound parameters. sqlite3
        # sends the query template and the values separately to the
        # database engine, so user input is always treated as plain
        # data — it can never be interpreted as SQL syntax, no matter
        # what characters it contains.
        # ------------------------------------------------------------
        query = "SELECT * FROM users WHERE username = ? AND password = ?"
        executed_query = f"{query}   -- params: ({username!r}, {password!r})"

        try:
            cur.execute(query, (username, password))
            user = cur.fetchone()
        except sqlite3.Error as e:
            error = f"Database error: {e}"

        if user is None and error is None:
            error = "Invalid username or password."

    notes = None
    if user is not None:
        db = get_db()
        cur = db.cursor()
        # Secure here too: user["id"] comes from our own trusted query
        # result (not raw request input), but we still parameterize as
        # a matter of consistent good practice.
        cur.execute("SELECT * FROM notes WHERE user_id = ?", (user["id"],))
        notes = cur.fetchall()

    return render_template(
        "login.html",
        mode="SECURE",
        error=error,
        user=user,
        notes=notes,
        executed_query=executed_query,
    )


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("Database not found — run `python init_db.py` first.")
    app.run(debug=True, port=5001)
