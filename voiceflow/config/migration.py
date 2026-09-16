"""One-time migration from the former home-directory data location."""

from __future__ import annotations

import re
import shutil
import sqlite3
from pathlib import Path

from .paths import DATA_DIR, HISTORY_DB_PATH, LEGACY_BACKUP_DIR, LEGACY_DATA_DIR


_MIGRATED_FILES = (
    "config.toml",
    "vocab.txt",
    "snippets.toml",
    ".onboarded",
    "voiceflow.log",
)

_SUPPORTED_DATABASE_TABLES = ("entries", "dictation_jobs")


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_names(connection: sqlite3.Connection, schema: str = "main") -> set[str]:
    rows = connection.execute(
        f"SELECT name FROM {_quote(schema)}.sqlite_master "
        "WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def _columns(connection: sqlite3.Connection, table: str, schema: str) -> list[str]:
    return [
        row[1]
        for row in connection.execute(
            f"PRAGMA {_quote(schema)}.table_info({_quote(table)})"
        ).fetchall()
    ]


def _create_table_from_legacy(target: sqlite3.Connection, table: str) -> None:
    row = target.execute(
        f"SELECT sql FROM {_quote('legacy')}.sqlite_master "
        "WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    statement = row[0] if row else None
    if not statement:
        raise RuntimeError(f"Could not read the schema for legacy table {table!r}.")

    match = re.match(
        r"^(?P<prefix>\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?)(?P<name>\"(?:[^\"]|\"\")*\"|`[^`]+`|\[[^\]]+\]|'[^']+'|[A-Za-z_][A-Za-z0-9_]*)(?P<rest>\s*\(.*)$",
        statement,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise RuntimeError(f"Unsupported schema for legacy table {table!r}.")

    target.execute(
        f"{match.group('prefix')}main.{_quote(table)}{match.group('rest')}"
    )


def _verify_rows_copied(target: sqlite3.Connection, table: str) -> None:
    source_columns = _columns(target, table, "legacy")
    destination_columns = _columns(target, table, "main")
    missing = [column for column in source_columns if column not in destination_columns]
    if missing:
        raise RuntimeError(
            f"Cannot safely migrate {table!r}; destination is missing columns: {missing}."
        )

    compare_columns = [column for column in source_columns if column != "id"]
    if not compare_columns:
        return

    selected = ", ".join(_quote(column) for column in compare_columns)
    predicates = " AND ".join(
        f"current.{_quote(column)} IS ?" for column in compare_columns
    )
    source_rows = target.execute(
        f"SELECT {selected} FROM legacy.{_quote(table)}"
    ).fetchall()
    for row in source_rows:
        copied = target.execute(
            f"SELECT 1 FROM main.{_quote(table)} AS current "
            f"WHERE {predicates} LIMIT 1",
            tuple(row),
        ).fetchone()
        if copied is None:
            raise RuntimeError(f"Could not confirm migration of a row from {table!r}.")


def _merge_entries(target: sqlite3.Connection, source_table: str = "entries") -> None:
    destination_columns = _columns(target, source_table, "main")
    source_columns = _columns(target, source_table, "legacy")
    missing = [column for column in source_columns if column not in destination_columns]
    if missing:
        raise RuntimeError(
            f"Cannot safely migrate {source_table!r}; destination is missing columns: {missing}."
        )
    columns = [column for column in source_columns if column in destination_columns and column != "id"]
    if not columns:
        raise RuntimeError(f"Legacy table {source_table!r} has no migratable columns.")

    quoted_columns = ", ".join(_quote(column) for column in columns)
    matches = " AND ".join(
        f"current.{_quote(column)} IS legacy.{_quote(column)}"
        for column in columns
    )
    target.execute(
        f"INSERT INTO main.{_quote(source_table)} ({quoted_columns}) "
        f"SELECT {quoted_columns} FROM legacy.{_quote(source_table)} AS legacy "
        f"WHERE NOT EXISTS (SELECT 1 FROM main.{_quote(source_table)} AS current WHERE {matches})"
    )


def _merge_jobs(target: sqlite3.Connection) -> None:
    table = "dictation_jobs"
    destination_columns = _columns(target, table, "main")
    source_columns = _columns(target, table, "legacy")
    missing = [column for column in source_columns if column not in destination_columns]
    if missing:
        raise RuntimeError(
            f"Cannot safely migrate {table!r}; destination is missing columns: {missing}."
        )
    columns = list(source_columns)
    if not columns:
        raise RuntimeError(f"Legacy table {table!r} has no migratable columns.")
    quoted_columns = ", ".join(_quote(column) for column in columns)
    target.execute(
        f"INSERT OR IGNORE INTO main.{_quote(table)} ({quoted_columns}) "
        f"SELECT {quoted_columns} FROM legacy.{_quote(table)}"
    )


def _merge_databases(legacy_path: Path, destination_path: Path) -> bool:
    """Merge legacy rows and confirm every supported table was copied."""
    with sqlite3.connect(str(destination_path)) as target:
        target.execute("ATTACH DATABASE ? AS legacy", (str(legacy_path),))
        try:
            tables = _table_names(target, "legacy")
            unsupported = tables - set(_SUPPORTED_DATABASE_TABLES) - {"sqlite_sequence"}
            if unsupported:
                raise RuntimeError(
                    f"Legacy database contains unsupported tables: {sorted(unsupported)}."
                )

            supported = [table for table in _SUPPORTED_DATABASE_TABLES if table in tables]
            destination_tables = _table_names(target, "main")
            for table in supported:
                if table not in destination_tables:
                    _create_table_from_legacy(target, table)

            if "entries" in supported:
                _merge_entries(target)
            if "dictation_jobs" in supported:
                _merge_jobs(target)
            for table in supported:
                _verify_rows_copied(target, table)
            target.commit()
            return True
        except Exception:
            target.rollback()
            raise
        finally:
            target.execute("DETACH DATABASE legacy")


def _backup_conflicting_file(source: Path) -> None:
    LEGACY_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    destination = LEGACY_BACKUP_DIR / source.name
    suffix = 1
    while destination.exists():
        destination = LEGACY_BACKUP_DIR / f"{source.stem}.{suffix}{source.suffix}"
        suffix += 1
    shutil.move(str(source), str(destination))


def _merge_vocab(source: Path, destination: Path) -> None:
    existing = destination.read_text(encoding="utf-8").splitlines() if destination.exists() else []
    known = {line.strip() for line in existing if line.strip()}
    additions = [line.strip() for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in additions:
        if line not in known:
            existing.append(line)
            known.add(line)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(existing) + ("\n" if existing else ""), encoding="utf-8")
    source.unlink()


def migrate_legacy_data() -> list[str]:
    """Move or merge known legacy data into ``data/`` and return actions taken."""
    if not LEGACY_DATA_DIR.exists() or LEGACY_DATA_DIR == DATA_DIR:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return []

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    actions: list[str] = []

    legacy_db = LEGACY_DATA_DIR / "history.db"
    if legacy_db.exists():
        if HISTORY_DB_PATH.exists():
            if _merge_databases(legacy_db, HISTORY_DB_PATH):
                legacy_db.unlink()
                actions.append(f"merged {legacy_db} into {HISTORY_DB_PATH}")
        else:
            shutil.move(str(legacy_db), str(HISTORY_DB_PATH))
            actions.append(f"moved {legacy_db} to {HISTORY_DB_PATH}")

    for name in _MIGRATED_FILES:
        source = LEGACY_DATA_DIR / name
        destination = DATA_DIR / name
        if name == "voiceflow.log":
            destination = DATA_DIR / "hush.log"
        if not source.exists():
            continue
        if name == "vocab.txt" and destination.exists():
            _merge_vocab(source, destination)
            actions.append(f"merged {source} into {destination}")
        elif destination.exists():
            _backup_conflicting_file(source)
            actions.append(f"moved conflicting {source} into {LEGACY_BACKUP_DIR}")
        else:
            shutil.move(str(source), str(destination))
            actions.append(f"moved {source} to {destination}")

    try:
        LEGACY_DATA_DIR.rmdir()
        actions.append(f"removed empty legacy directory {LEGACY_DATA_DIR}")
    except OSError:
        # Unknown files are left untouched rather than deleting user data.
        pass

    return actions
