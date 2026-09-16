import sqlite3

from voiceflow.config import paths
from voiceflow.config import migration


def _create_entries_db(path, rows):
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                raw TEXT NOT NULL,
                clean TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'light',
                app TEXT,
                words INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.executemany(
            "INSERT INTO entries (ts, raw, clean, level, app, words) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )


def test_application_data_paths_are_inside_repository():
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data"
    assert paths.HISTORY_DB_PATH == paths.DATA_DIR / "history.db"
    assert paths.SNIPPETS_PATH == paths.DATA_DIR / "snippets.toml"
    assert paths.HISTORY_DB_PATH.is_relative_to(paths.PROJECT_ROOT)


def test_database_migration_preserves_raw_and_cleaned_entries(tmp_path):
    legacy_path = tmp_path / "legacy.db"
    destination_path = tmp_path / "data.db"
    rows = [
        ("2026-09-15T10:00:00", "hello raw", "Hello cleaned.", "light", "Safari", 2),
        ("2026-09-15T10:01:00", "second raw", "Second cleaned.", "medium", "Notes", 2),
    ]
    _create_entries_db(legacy_path, rows)
    _create_entries_db(destination_path, [rows[0]])

    migration._merge_databases(legacy_path, destination_path)

    with sqlite3.connect(destination_path) as connection:
        saved = connection.execute(
            "SELECT raw, clean, level, app FROM entries ORDER BY id"
        ).fetchall()

    assert saved == [
        ("hello raw", "Hello cleaned.", "light", "Safari"),
        ("second raw", "Second cleaned.", "medium", "Notes"),
    ]
