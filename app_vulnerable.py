"""
app_vulnerable.py
------------------
*** EDUCATIONAL DEMO — CONTAINS AN INTENTIONAL SQL INJECTION VULNERABILITY ***

This app builds SQL queries by directly concatenating / formatting
user-supplied input into the query string. NEVER do this in real code.
It is included so you can see, in a controlled local environment,
exactly how an attacker exploits unsanitized input — and then compare
it against app_secure.py, which fixes the same code with parameterized
queries.

Run with:
    python app_vulnerable.py
Then visit http://127.0.0.1:5000/

Try logging in with:
    Username: ' OR '1'='1' --
    Password: anything
"""

import sqlite3
import os
from flask import Flask, request, render_template, g

DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")

app = Flask(__name__)
app.secret_key = "demo-only-not-for-production"


def get_db():
    """Open (or reuse) a SQLite connection for this request."""
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
    executed_query = None  # shown on the page so you can see exactly what ran

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        db = get_db()
        cur = db.cursor()

        # ------------------------------------------------------------
        # !!! VULNERABLE LINE !!!
        #
        # User input is inserted directly into the SQL string using an
        # f-string. Because the query text itself changes based on what
        # the attacker types, they can inject SQL syntax — like adding
        # `OR '1'='1'` — to change the query's logic entirely.
        # ------------------------------------------------------------
        query = (
            f"SELECT * FROM users WHERE username = '{username}' "
            f"AND password = '{password}'"
        )
        executed_query = query  # for display only, so learners can see it

        try:
            cur.execute(query)
            user = cur.fetchone()
        except sqlite3.Error as e:
            error = f"Database error: {e}"

        if user is None and error is None:
            error = "Invalid username or password."

    notes = None
    if user is not None:
        # Bonus: fetch this user's notes the same vulnerable way, so a
        # successful injection can be seen pulling back unintended rows.
        db = get_db()
        cur = db.cursor()
        notes_query = f"SELECT * FROM notes WHERE user_id = {user['id']}"
        cur.execute(notes_query)
        notes = cur.fetchall()

    return render_template(
        "login.html",
        mode="VULNERABLE",
        error=error,
        user=user,
        notes=notes,
        executed_query=executed_query,
    )


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("Database not found — run `python init_db.py` first.")
    app.run(debug=True, port=5000)
