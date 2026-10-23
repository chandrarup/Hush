"""Managed PostgreSQL, Cloud Storage, and Secret Manager runtime.

The cloud VM authenticates with its attached service account through Application
Default Credentials. No service-account key file or secret value is written to
the container filesystem.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path, PurePath
from typing import Any


class ManagedStateError(RuntimeError):
    """Raised when a required managed service cannot be initialized or used."""


_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _ROOT / "migrations"
_RUNTIME_LOCK = threading.RLock()
_RUNTIME: ManagedState | None = None


def managed_state_enabled() -> bool:
    """Return whether the server has been configured for Cloud SQL."""
    return bool(os.getenv("HUSH_CLOUD_SQL_INSTANCE", "").strip())


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ManagedStateError(f"{name} is required for managed cloud state.")
    return value


def _serialized_row(row: Any) -> dict[str, Any]:
    values = dict(row._mapping if hasattr(row, "_mapping") else row)
    for key, value in list(values.items()):
        if isinstance(value, (datetime, date)):
            values[key] = value.isoformat()
        elif isinstance(value, uuid.UUID):
            values[key] = str(value)
    return values


def _safe_original_filename(value: str | None) -> str:
    """Keep a display-only filename; object paths never contain user input."""
    name = PurePath(value or "recording.wav").name.strip()[:200]
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name)
    return name or "recording.wav"


class ManagedState:
    """Own the VM's pooled private database connection and GCS client."""

    def __init__(self) -> None:
        self.project_id = _required_env("GOOGLE_CLOUD_PROJECT")
        self.instance_connection_name = _required_env("HUSH_CLOUD_SQL_INSTANCE")
        self.database = os.getenv("HUSH_DB_NAME", "hush").strip() or "hush"
        self.database_user = os.getenv("HUSH_DB_USER", "hush_app").strip() or "hush_app"
        self.database_password_secret = os.getenv(
            "HUSH_DB_PASSWORD_SECRET", "hush-db-password"
        ).strip() or "hush-db-password"
        self.team_token_secret = os.getenv(
            "HUSH_TEAM_TOKEN_SECRET", "hush-team-token"
        ).strip() or "hush-team-token"
        self.bucket_name = _required_env("HUSH_UPLOAD_BUCKET")
        self._connector: Any | None = None
        self._engine: Any | None = None
        self._storage_client: Any | None = None
        self._bucket: Any | None = None
        self._team_token: str | None = None
        self._ready = False

    @property
    def team_token(self) -> str:
        if not self._team_token:
            raise ManagedStateError("The team token has not been loaded.")
        return self._team_token

    def _access_secret(self, secret_name: str) -> str:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        resource = (
            f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
        )
        try:
            response = client.access_secret_version(request={"name": resource})
        except Exception as exc:
            raise ManagedStateError(
                f"Could not access required secret '{secret_name}'."
            ) from exc
        value = response.payload.data.decode("utf-8").strip()
        if not value:
            raise ManagedStateError(f"Required secret '{secret_name}' is empty.")
        return value

    def initialize(self) -> "ManagedState":
        """Initialize clients, verify access, and apply committed migrations."""
        if self._ready:
            return self

        from google.cloud import storage
        from google.cloud.sql.connector import Connector, IPTypes
        from sqlalchemy import create_engine, text

        database_password = self._access_secret(self.database_password_secret)
        self._team_token = self._access_secret(self.team_token_secret)
        self._connector = Connector(refresh_strategy="LAZY", timeout=5)

        def connect() -> Any:
            return self._connector.connect(
                self.instance_connection_name,
                "pg8000",
                user=self.database_user,
                password=database_password,
                db=self.database,
                ip_type=IPTypes.PRIVATE,
                timeout=2,
            )

        self._engine = create_engine(
            "postgresql+pg8000://",
            creator=connect,
            pool_size=int(os.getenv("HUSH_DB_POOL_SIZE", "2")),
            max_overflow=int(os.getenv("HUSH_DB_MAX_OVERFLOW", "0")),
            pool_timeout=1,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        self._storage_client = storage.Client(project=self.project_id)
        self._bucket = self._storage_client.bucket(self.bucket_name)

        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            next(
                iter(self._storage_client.list_blobs(self.bucket_name, max_results=1)),
                None,
            )
            self.apply_migrations()
        except Exception as exc:
            self.close()
            raise ManagedStateError(
                "Managed state initialization failed; check private networking and IAM."
            ) from exc

        self._ready = True
        return self

    def close(self) -> None:
        self._ready = False
        if self._engine is not None:
            self._engine.dispose()
        if self._connector is not None:
            self._connector.close()
        self._engine = None
        self._connector = None

    def _require_engine(self) -> Any:
        if self._engine is None:
            raise ManagedStateError("Managed state has not been initialized.")
        return self._engine

    def apply_migrations(self) -> None:
        """Apply every committed SQL migration exactly once."""
        from sqlalchemy import text

        engine = self._require_engine()
        migration_files = sorted(_MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
        if not migration_files:
            raise ManagedStateError("No database migration files were found.")

        with engine.begin() as connection:
            # Lock before inspecting the ledger: two replicas can start together.
            connection.execute(text("SELECT pg_advisory_xact_lock(57327001)"))
            connection.execute(text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version TEXT PRIMARY KEY, "
                "applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            ))
            applied = {
                row[0]
                for row in connection.execute(
                    text("SELECT version FROM schema_migrations")
                ).fetchall()
            }
            for path in migration_files:
                if path.name in applied:
                    continue
                sql = path.read_text(encoding="utf-8")
                for statement in (piece.strip() for piece in sql.split(";")):
                    if statement:
                        connection.exec_driver_sql(statement)
                connection.execute(
                    text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                    {"version": path.name},
                )

    def check_ready(self) -> dict[str, bool]:
        from sqlalchemy import text

        checks = {"database": False, "storage": False, "secrets": bool(self._team_token)}
        if self._engine is None or self._bucket is None:
            return checks
        try:
            with self._engine.connect() as connection:
                checks["database"] = connection.execute(text("SELECT 1")).scalar_one() == 1
        except Exception:
            pass
        try:
            next(
                iter(self._storage_client.list_blobs(
                    self.bucket_name, max_results=1, timeout=2, retry=None
                )),
                None,
            )
            checks["storage"] = True
        except Exception:
            pass
        return checks

    # History ---------------------------------------------------------
    def save_entry(
        self,
        *,
        raw: str,
        clean: str,
        level: str,
        app: str | None,
        client_id: str | None,
        status: str,
        timestamp: str | None = None,
        entry_id: int | None = None,
    ) -> int:
        from sqlalchemy import text

        words = len(clean.split())
        values = {
            "ts": timestamp or datetime.now(timezone.utc).isoformat(),
            "raw": raw,
            "clean": clean,
            "level": level,
            "app": app,
            "client_id": client_id,
            "status": status,
            "words": words,
            "id": entry_id,
        }
        if entry_id is None:
            sql = text(
                "INSERT INTO entries (ts, raw, clean, level, app, client_id, status, words) "
                "VALUES (:ts, :raw, :clean, :level, :app, :client_id, :status, :words) "
                "RETURNING id"
            )
        else:
            sql = text(
                "INSERT INTO entries (id, ts, raw, clean, level, app, client_id, status, words) "
                "VALUES (:id, :ts, :raw, :clean, :level, :app, :client_id, :status, :words) "
                "ON CONFLICT (id) DO NOTHING RETURNING id"
            )
        with self._require_engine().begin() as connection:
            saved_id = connection.execute(sql, values).scalar_one_or_none()
            if entry_id is not None:
                connection.execute(text(
                    "SELECT setval(pg_get_serial_sequence('entries', 'id'), "
                    "GREATEST((SELECT COALESCE(MAX(id), 1) FROM entries), 1), true)"
                ))
        return int(saved_id if saved_id is not None else entry_id)

    def get_entries(self, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
        from sqlalchemy import text

        bounded_limit = min(max(int(limit), 1), 500)
        bounded_offset = max(int(offset), 0)
        with self._require_engine().connect() as connection:
            rows = connection.execute(
                text("SELECT * FROM entries ORDER BY id DESC LIMIT :limit OFFSET :offset"),
                {"limit": bounded_limit, "offset": bounded_offset},
            ).fetchall()
        return [_serialized_row(row) for row in rows]

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        from sqlalchemy import text

        with self._require_engine().connect() as connection:
            row = connection.execute(
                text("SELECT * FROM entries WHERE id = :id"), {"id": entry_id}
            ).fetchone()
        return _serialized_row(row) if row else None

    def delete_entry(self, entry_id: int) -> None:
        from sqlalchemy import text

        with self._require_engine().begin() as connection:
            connection.execute(text("DELETE FROM entries WHERE id = :id"), {"id": entry_id})

    def clear_entries(self) -> None:
        from sqlalchemy import text

        with self._require_engine().begin() as connection:
            connection.execute(text("DELETE FROM entries"))

    def get_stats(self) -> dict[str, int]:
        from sqlalchemy import text

        with self._require_engine().connect() as connection:
            row = connection.execute(text(
                "SELECT COALESCE(SUM(words), 0) AS total_words, "
                "COUNT(*) AS total_entries, COUNT(DISTINCT DATE(ts)) AS active_days, "
                "COALESCE(AVG(words), 0) AS avg_words FROM entries"
            )).one()
        values = row._mapping
        avg_wpm = int(float(values["avg_words"]) * 12) if values["total_entries"] else 0
        return {
            "total_words": int(values["total_words"]),
            "avg_wpm": min(avg_wpm, 300),
            "active_days": int(values["active_days"]),
        }

    def count_entries(self) -> int:
        from sqlalchemy import text

        with self._require_engine().connect() as connection:
            return int(connection.execute(text("SELECT COUNT(*) FROM entries")).scalar_one())

    # Snippets and settings ------------------------------------------
    def list_snippets(self) -> list[dict[str, str]]:
        from sqlalchemy import text

        with self._require_engine().connect() as connection:
            rows = connection.execute(text(
                "SELECT name, shortcut, expanded_text AS text FROM snippets ORDER BY id"
            )).fetchall()
        return [dict(row._mapping) for row in rows]

    def upsert_snippet(self, name: str, shortcut: str, normalized: str, expanded: str) -> None:
        from sqlalchemy import text

        with self._require_engine().begin() as connection:
            connection.execute(text(
                "INSERT INTO snippets (name, shortcut, normalized_shortcut, expanded_text) "
                "VALUES (:name, :shortcut, :normalized, :expanded) "
                "ON CONFLICT (normalized_shortcut) DO UPDATE SET "
                "name = EXCLUDED.name, shortcut = EXCLUDED.shortcut, "
                "expanded_text = EXCLUDED.expanded_text, updated_at = CURRENT_TIMESTAMP"
            ), {"name": name, "shortcut": shortcut, "normalized": normalized, "expanded": expanded})

    def update_snippet(self, index: int, name: str, shortcut: str, normalized: str, expanded: str) -> None:
        from sqlalchemy import text

        with self._require_engine().begin() as connection:
            snippet_id = connection.execute(text(
                "SELECT id FROM snippets ORDER BY id LIMIT 1 OFFSET :offset"
            ), {"offset": index}).scalar_one_or_none()
            if snippet_id is None:
                raise IndexError("Snippet does not exist.")
            connection.execute(text(
                "UPDATE snippets SET name=:name, shortcut=:shortcut, "
                "normalized_shortcut=:normalized, expanded_text=:expanded, "
                "updated_at=CURRENT_TIMESTAMP WHERE id=:id"
            ), {"id": snippet_id, "name": name, "shortcut": shortcut, "normalized": normalized, "expanded": expanded})

    def delete_snippet(self, index: int) -> None:
        from sqlalchemy import text

        with self._require_engine().begin() as connection:
            snippet_id = connection.execute(text(
                "SELECT id FROM snippets ORDER BY id LIMIT 1 OFFSET :offset"
            ), {"offset": index}).scalar_one_or_none()
            if snippet_id is None:
                raise IndexError("Snippet does not exist.")
            connection.execute(text("DELETE FROM snippets WHERE id=:id"), {"id": snippet_id})

    def get_settings(self) -> dict[str, Any]:
        from sqlalchemy import text

        with self._require_engine().connect() as connection:
            rows = connection.execute(text("SELECT key, value FROM app_settings")).fetchall()
        return {row.key: row.value for row in rows}

    def set_setting(self, key: str, value: Any) -> None:
        from sqlalchemy import text

        with self._require_engine().begin() as connection:
            connection.execute(text(
                "INSERT INTO app_settings (key, value) VALUES (:key, CAST(:value AS JSONB)) "
                "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, "
                "updated_at=CURRENT_TIMESTAMP"
            ), {"key": key, "value": json.dumps(value)})

    # Uploads ---------------------------------------------------------
    def store_upload(self, payload: bytes, original_filename: str | None) -> dict[str, Any]:
        from sqlalchemy import text

        if self._bucket is None:
            raise ManagedStateError("Cloud Storage has not been initialized.")
        upload_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        object_name = f"uploads/{now:%Y/%m/%d}/{upload_id}.wav"
        safe_name = _safe_original_filename(original_filename)
        values = {
            "id": upload_id,
            "bucket": self.bucket_name,
            "object_name": object_name,
            "original_filename": safe_name,
            "size_bytes": len(payload),
        }
        with self._require_engine().begin() as connection:
            connection.execute(text(
                "INSERT INTO uploads (id, bucket, object_name, original_filename, "
                "content_type, size_bytes, status) VALUES (:id, :bucket, :object_name, "
                ":original_filename, 'audio/wav', :size_bytes, 'pending')"
            ), values)
        try:
            blob = self._bucket.blob(object_name)
            blob.metadata = {"original-filename": safe_name}
            blob.upload_from_string(
                payload,
                content_type="audio/wav",
                if_generation_match=0,
                timeout=60,
            )
            with self._require_engine().begin() as connection:
                connection.execute(text(
                    "UPDATE uploads SET status='stored' WHERE id=:id"
                ), {"id": upload_id})
        except Exception as exc:
            with self._require_engine().begin() as connection:
                connection.execute(text(
                    "UPDATE uploads SET status='failed', error_message=:error WHERE id=:id"
                ), {"id": upload_id, "error": type(exc).__name__})
            raise ManagedStateError("Could not store the uploaded file.") from exc
        return {
            "id": str(upload_id),
            "bucket": self.bucket_name,
            "object_name": object_name,
            "original_filename": safe_name,
            "size_bytes": len(payload),
            "status": "stored",
        }

    def complete_upload(self, upload_id: str, history_id: int | None) -> None:
        from sqlalchemy import text

        with self._require_engine().begin() as connection:
            connection.execute(text(
                "UPDATE uploads SET status='completed', history_id=:history_id, "
                "completed_at=CURRENT_TIMESTAMP WHERE id=:id"
            ), {"id": uuid.UUID(upload_id), "history_id": history_id})

    def fail_upload(self, upload_id: str, reason: str) -> None:
        from sqlalchemy import text

        with self._require_engine().begin() as connection:
            connection.execute(text(
                "UPDATE uploads SET status='failed', error_message=:reason, "
                "completed_at=CURRENT_TIMESTAMP WHERE id=:id"
            ), {"id": uuid.UUID(upload_id), "reason": reason[:500]})


def initialize_managed_state() -> ManagedState:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = ManagedState()
        return _RUNTIME.initialize()


def get_managed_state() -> ManagedState:
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            raise ManagedStateError("Managed state has not been initialized.")
        return _RUNTIME


def reset_managed_state_for_tests() -> None:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is not None:
            _RUNTIME.close()
        _RUNTIME = None
