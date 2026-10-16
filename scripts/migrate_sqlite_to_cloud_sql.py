#!/usr/bin/env python3
"""Migrate the VM's canonical SQLite state into managed Cloud SQL.

Run this on the VM with the Hush runtime service account attached. The script
never accepts or prints a password; it uses Secret Manager and ADC exactly like
the application. It is idempotent by entry ID and exits non-zero if row counts
do not match after migration.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import toml

from voiceflow.cloud.managed_state import ManagedState, ManagedStateError
from voiceflow.config.snippets import _normalise_text


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--snippets", type=Path)
    parser.add_argument("--backup-object")
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def _sqlite_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"SQLite source does not exist: {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [
            dict(row)
            for row in connection.execute("SELECT * FROM entries ORDER BY id")
        ]
    finally:
        connection.close()


def _migrate_settings(state: ManagedState, config_path: Path | None) -> int:
    if config_path is None or not config_path.is_file():
        return 0
    config = toml.load(config_path)
    values = {
        "cleanup_level": config.get("llm", {}).get("cleanup_level"),
        "ollama_model": config.get("llm", {}).get("ollama_model"),
        "asr_engine": config.get("asr", {}).get("engine"),
        "hotkey": config.get("hotkey", {}).get("key"),
    }
    count = 0
    for key, value in values.items():
        if value is not None:
            state.set_setting(key, value)
            count += 1
    return count


def _migrate_snippets(state: ManagedState, snippets_path: Path | None) -> int:
    if snippets_path is None or not snippets_path.is_file():
        return 0
    snippets = toml.load(snippets_path).get("snippets", [])
    count = 0
    for item in snippets:
        name = str(item.get("name", "")).strip()
        shortcut = str(item.get("shortcut", "")).strip()
        expanded = str(item.get("text", "")).strip()
        normalized = _normalise_text(shortcut)
        if name and normalized and expanded:
            state.upsert_snippet(name, shortcut, normalized, expanded)
            count += 1
    return count


def main() -> int:
    args = _arguments()
    source_rows = _sqlite_rows(args.sqlite)
    state = ManagedState().initialize()
    try:
        backup_object = args.backup_object or (
            "migration-backups/history-"
            f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.db"
        )
        blob = state._bucket.blob(backup_object)
        blob.upload_from_filename(
            str(args.sqlite),
            content_type="application/vnd.sqlite3",
            if_generation_match=0,
        )

        for row in source_rows:
            state.save_entry(
                raw=row.get("raw", ""),
                clean=row.get("clean", ""),
                level=row.get("level", "light"),
                app=row.get("app"),
                client_id=row.get("client_id"),
                status=row.get("status", "final"),
                timestamp=row.get("ts"),
                entry_id=int(row["id"]),
            )

        settings_count = _migrate_settings(state, args.config)
        snippets_count = _migrate_snippets(state, args.snippets)
        destination_count = state.count_entries()
        report = {
            "source": {"database": str(args.sqlite), "entries": len(source_rows)},
            "destination": {
                "instance": state.instance_connection_name,
                "database": state.database,
                "entries": destination_count,
            },
            "migrated_settings": settings_count,
            "migrated_snippets": snippets_count,
            "backup": f"gs://{state.bucket_name}/{backup_object}",
            "counts_match": destination_count == len(source_rows),
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        rendered = json.dumps(report, indent=2, sort_keys=True)
        print(rendered)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(rendered + "\n", encoding="utf-8")
        return 0 if report["counts_match"] else 2
    finally:
        state.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ManagedStateError as exc:
        raise SystemExit(str(exc)) from exc
