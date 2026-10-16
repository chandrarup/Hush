"""Transcription history backed by SQLite locally and Cloud SQL on the VM."""

import sqlite3
from datetime import datetime

from ..config.paths import HISTORY_DB_PATH


DB_PATH = HISTORY_DB_PATH


def _managed_store():
    """Return the initialized Cloud SQL store only for the managed VM runtime."""
    from ..cloud.managed_state import get_managed_state, managed_state_enabled

    return get_managed_state() if managed_state_enabled() else None


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c


def init_db():
    managed = _managed_store()
    if managed is not None:
        managed.apply_migrations()
        print("[history] Cloud SQL schema ready")
        return
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                ts       TEXT    NOT NULL,
                raw      TEXT    NOT NULL,
                clean    TEXT    NOT NULL,
                level    TEXT    NOT NULL DEFAULT 'light',
                app      TEXT,
                client_id TEXT,
                status   TEXT    NOT NULL DEFAULT 'final',
                words    INTEGER NOT NULL DEFAULT 0
            )
        """)
        columns = {row[1] for row in c.execute("PRAGMA table_info(entries)")}
        if "client_id" not in columns:
            c.execute("ALTER TABLE entries ADD COLUMN client_id TEXT")
        if "status" not in columns:
            c.execute(
                "ALTER TABLE entries ADD COLUMN status TEXT NOT NULL DEFAULT 'final'"
            )
        c.commit()
    print("[history] DB ready at", DB_PATH)


def save_entry(
    raw: str,
    clean: str,
    level: str = "light",
    app: str | None = None,
    client_id: str | None = None,
    status: str = "final",
) -> int:
    """Save a transcription entry. Returns the new row id."""
    managed = _managed_store()
    if managed is not None:
        return managed.save_entry(
            raw=raw,
            clean=clean,
            level=level,
            app=app,
            client_id=client_id,
            status=status,
        )
    words = len(clean.split())
    ts    = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO entries "
            "(ts, raw, clean, level, app, client_id, status, words) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ts, raw, clean, level, app, client_id, status, words),
        )
        c.commit()
        return cur.lastrowid


def get_entries(limit: int = 200, offset: int = 0) -> list[dict]:
    """Return entries newest-first."""
    managed = _managed_store()
    if managed is not None:
        return managed.get_entries(limit=limit, offset=offset)
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM entries ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def get_entry(entry_id: int) -> dict | None:
    managed = _managed_store()
    if managed is not None:
        return managed.get_entry(entry_id)
    with _conn() as c:
        row = c.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
    return dict(row) if row else None


def delete_entry(entry_id: int):
    managed = _managed_store()
    if managed is not None:
        managed.delete_entry(entry_id)
        return
    with _conn() as c:
        c.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        c.commit()


def clear_all():
    managed = _managed_store()
    if managed is not None:
        managed.clear_entries()
        return
    with _conn() as c:
        c.execute("DELETE FROM entries")
        c.commit()


def get_stats() -> dict:
    """Total words, average WPM (rough), and number of active days."""
    managed = _managed_store()
    if managed is not None:
        return managed.get_stats()
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
