"""
history.py - SQLite transcription history store.

Saves every transcription entry with timestamp, raw ASR output,
LLM-cleaned output, cleanup level, and active app name to ``data/history.db``.
"""

import sqlite3
from datetime import datetime

from voiceflow.config.paths import HISTORY_DB_PATH


# Keep the existing module-level name for callers that inspect the database
# location, while sourcing it from the centralized application path module.
DB_PATH = HISTORY_DB_PATH


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                ts       TEXT    NOT NULL,
                raw      TEXT    NOT NULL,
                clean    TEXT    NOT NULL,
                level    TEXT    NOT NULL DEFAULT 'light',
                app      TEXT,
                words    INTEGER NOT NULL DEFAULT 0
            )
        """)
        c.commit()
    print("[history] DB ready at", DB_PATH)


def save_entry(raw: str, clean: str, level: str = "light", app: str | None = None) -> int:
    """Save a transcription entry. Returns the new row id."""
    words = len(clean.split())
    ts    = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO entries (ts, raw, clean, level, app, words) VALUES (?,?,?,?,?,?)",
            (ts, raw, clean, level, app, words),
        )
        c.commit()
        return cur.lastrowid


def get_entries(limit: int = 200, offset: int = 0) -> list[dict]:
    """Return entries newest-first."""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM entries ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def get_entry(entry_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
    return dict(row) if row else None


def delete_entry(entry_id: int):
    with _conn() as c:
        c.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        c.commit()


def clear_all():
    with _conn() as c:
        c.execute("DELETE FROM entries")
        c.commit()


def get_stats() -> dict:
    """Total words, average WPM (rough), and number of active days."""
    with _conn() as c:
        row = c.execute("""
            SELECT
                COALESCE(SUM(words), 0)  AS total_words,
                COUNT(*)                 AS total_entries,
                COUNT(DISTINCT DATE(ts)) AS active_days
            FROM entries
        """).fetchone()
    total_words  = row["total_words"]
    active_days  = row["active_days"]
    # Rough WPM: assume average ~5s per entry at ~150 wpm
    avg_wpm = 0
    if row["total_entries"] > 0:
        with _conn() as c:
            avg_row = c.execute("SELECT AVG(words) as aw FROM entries").fetchone()
            avg_wpm = int((avg_row["aw"] or 0) * 12)  # 5s entries → rough wpm
    return {
        "total_words": total_words,
        "avg_wpm":     min(avg_wpm, 300),
        "active_days": active_days,
    }
