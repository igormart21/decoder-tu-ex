import sqlite3
from contextlib import contextmanager

DB_PATH = "decoder.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)


# ── Users ──────────────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str, first_name: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name))


# ── History ────────────────────────────────────────────────────────────────

MAX_HISTORY = 10  # mensagens por usuário (últimas N)


def add_message(user_id: int, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        # Mantém só as últimas MAX_HISTORY mensagens
        conn.execute("""
            DELETE FROM history
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
        """, (user_id, user_id, MAX_HISTORY))


def get_history(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM history WHERE user_id = ? ORDER BY id ASC",
            (user_id,)
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]


def clear_history(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
