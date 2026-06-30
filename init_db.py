"""
init_db.py
----------
Creates and seeds a small SQLite database used by both the vulnerable
and the secure demo apps. Run this once before starting either app:

    python init_db.py

This script ALWAYS uses parameterized queries itself (there's no reason
for setup code to be unsafe) — the vulnerability we're demonstrating
lives only in app_vulnerable.py, at the point where untrusted user
input is handled.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")


def init_db():
    # Start fresh each time so the demo behaves predictably
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- Schema -----------------------------------------------------
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,   -- plaintext on purpose, see README
            is_admin INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --- Seed data ----------------------------------------------------
    # NOTE: Passwords are stored in PLAINTEXT here. That is itself bad
    # practice (real apps should hash with bcrypt/argon2/etc.), but it's
    # left this way deliberately so the SQL injection demo is easy to
    # follow without an extra hashing step muddying the picture.
    users = [
        ("alice", "alicepassword123", 0),
        ("bob", "bobspassword456", 0),
        ("admin", "super_secret_admin_pw", 1),
    ]
    cur.executemany(
        "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
        users,
    )

    notes = [
        (1, "Alice's private note: remember to water the plants."),
        (2, "Bob's private note: meeting moved to 3pm."),
        (3, "Admin note: rotate API keys this Friday."),
    ]
    cur.executemany(
        "INSERT INTO notes (user_id, content) VALUES (?, ?)",
        notes,
    )

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")
    print("Seed users: alice/alicepassword123, bob/bobspassword456, admin/super_secret_admin_pw")


if __name__ == "__main__":
    init_db()
