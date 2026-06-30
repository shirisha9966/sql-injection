# SQL Injection Demo (Educational)

A small, self-contained project for learning how SQL injection works
and how to prevent it. It contains **two Flask apps that are otherwise
identical** except for one thing: how they build their SQL query from
user input.

| App | Port | Behavior |
|---|---|---|
| `app_vulnerable.py` | 5000 | Builds SQL by string concatenation — **injectable** |
| `app_secure.py` | 5001 | Builds SQL with parameterized queries — **not injectable** |

Run them side by side and try the same login payload against both to
see the difference directly.

---

## Project structure

```
sqli-demo/
├── app_vulnerable.py    # Intentionally vulnerable login app
├── app_secure.py        # Fixed version using parameterized queries
├── init_db.py           # Creates demo.db and seeds sample users/notes
├── requirements.txt
├── templates/
│   └── login.html       # Shared template for both apps
└── demo.db              # Created after running init_db.py
```

---

## Setup

```bash
cd sqli-demo
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python init_db.py               # creates demo.db with seed users
```

Seed accounts (plaintext passwords — see "Notes on realism" below):

| username | password | admin? |
|---|---|---|
| alice | alicepassword123 | no |
| bob | bobspassword456 | no |
| admin | super_secret_admin_pw | yes |

Run each app in its own terminal:

```bash
python app_vulnerable.py   # http://127.0.0.1:5000
python app_secure.py       # http://127.0.0.1:5001
```

---

## The vulnerability

In `app_vulnerable.py`, the login query is built like this:

```python
query = (
    f"SELECT * FROM users WHERE username = '{username}' "
    f"AND password = '{password}'"
)
cur.execute(query)
```

Because `username` and `password` are dropped straight into the SQL
*text*, anything the user types that contains SQL syntax becomes part
of the query the database actually runs — not just a literal value
being compared.

### Example exploit: authentication bypass

In the username field, enter:

```
' OR '1'='1' --
```

with any password. The query becomes:

```sql
SELECT * FROM users WHERE username = '' OR '1'='1' --' AND password = '...'
```

The trailing `--` starts a SQL comment, so everything after it
(including the password check) is ignored. `'1'='1'` is always true,
so the `WHERE` clause matches the first row in the table regardless of
credentials — logging you in as whoever that is (here, `alice`),
without knowing her password.

(Note: a bare `' OR '1'='1` *without* the comment won't bypass this
particular query, because `AND` binds tighter than `OR` — the password
check would still apply. The `--` is what actually neutralizes it,
which is itself a useful lesson in how fragile "intuitive" injection
payloads can be in practice.)

### Example exploit: data exfiltration

Entering a username like:

```
nonexistent' UNION SELECT id, username, password, is_admin FROM users--
```

(with the trailing `--` commenting out the rest of the original
query) can be used to pull back arbitrary rows from the `users` table,
including every stored password — even though the form only ever
intended to check one username/password pair.

### Why this happens

The fundamental problem is that **query structure and user data are
mixed into the same string**. The database can't tell the difference
between "SQL the developer wrote" and "SQL an attacker snuck in
through a text field" — to the database engine, it's all just SQL.

---

## The fix: parameterized queries

`app_secure.py` runs the same logic with one change:

```python
query = "SELECT * FROM users WHERE username = ? AND password = ?"
cur.execute(query, (username, password))
```

The `?` placeholders are **bound parameters**. The driver sends the
query template and the values as two separate things to the database
engine. The engine compiles the query structure first, and only then
substitutes the values in as literal data — so no matter what
characters `username` or `password` contain, they can never be
interpreted as SQL syntax. Try `' OR '1'='1` against the secure app
and it's correctly treated as a literal (and nonexistent) username.

This same pattern — keep the query template fixed, bind variables
separately — is how every major language/database driver supports
safe parameterization:

| Language / Library | Syntax |
|---|---|
| Python `sqlite3` / `psycopg2` | `cur.execute("... WHERE x = ?", (val,))` (sqlite3) or `%s` (psycopg2) |
| Node.js (`pg`, `mysql2`) | `query("... WHERE x = $1", [val])` |
| Java (JDBC) | `PreparedStatement` with `?` placeholders |
| PHP (PDO) | `$pdo->prepare("... WHERE x = :val")` |
| Ruby (ActiveRecord) | `User.where("x = ?", val)` |

---

## Side-by-side comparison

| | Vulnerable | Secure |
|---|---|---|
| Query construction | f-string concatenation | `?` placeholders + bound params |
| `' OR '1'='1` as username | Logs in as first user | Login correctly rejected |
| `UNION`-based data extraction | Possible | Not possible (input is never parsed as SQL) |
| Code change required | — | One line: pass tuple of params to `execute()` instead of formatting the string |
| Performance | N/A for demo size; in real systems, prepared statements can also be *faster* on repeated queries since query plans can be cached | Same |

---

## Defense in depth (beyond parameterized queries)

Parameterized queries fix this specific class of bug, but a real
production system should layer on more protections:

1. **Least privilege database accounts** — the app's DB user should
   only have the permissions it actually needs (e.g., no `DROP TABLE`
   rights for a login service).
2. **Input validation** — reject obviously malformed input early
   (e.g., usernames with unexpected characters), as a secondary layer,
   not a replacement for parameterization.
3. **ORM usage** — tools like SQLAlchemy or Django ORM parameterize
   queries by default, reducing the chance of accidentally writing
   raw, unsafe SQL.
4. **Password hashing** — this demo stores plaintext passwords for
   clarity; real applications must hash passwords (e.g., with
   `bcrypt` or `argon2`) and compare hashes, never store or compare
   plaintext.
5. **Error handling** — don't leak raw database error messages to
   users in production; they can reveal schema details useful to an
   attacker. (This demo intentionally shows them for learning
   purposes.)
6. **Web Application Firewall (WAF)** — can catch some injection
   attempts as an additional layer, though it should never be the
   *only* defense.

---

## Notes on realism

A few things are simplified on purpose so the demo stays focused on
SQL injection specifically:

- Passwords are stored in plaintext (a real app must hash them).
- There's no CSRF protection, rate limiting, or session management
  beyond what's needed to show a logged-in result.
- Both apps print the literal query/parameters sent to the database
  on the page, purely so you can see what's happening under the hood —
  a real app would never display this.

**Run this only locally, for learning.** Don't deploy `app_vulnerable.py`
anywhere reachable from the internet.
