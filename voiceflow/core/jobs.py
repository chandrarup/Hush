"""SQLite adapter for the durable local dictation job repository."""

import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..application.jobs import DictationJob, JobClaim, JobStatus
from ..config.paths import HISTORY_DB_PATH


class SQLiteJobRepository:
    """Persist job state in SQLite behind a cloud-ready interface."""

    def __init__(
        self,
        db_path: Path = HISTORY_DB_PATH,
        *,
        processing_lease_seconds: float = 300,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if processing_lease_seconds <= 0:
            raise ValueError("processing_lease_seconds must be positive")
        self.db_path = Path(db_path)
        self.processing_lease = timedelta(seconds=processing_lease_seconds)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.init_db()

    def _conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        with self._conn() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dictation_jobs (
                    request_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    user_id TEXT,
                    raw_text TEXT,
                    clean_text TEXT,
                    entry_id INTEGER,
                    error TEXT,
                    claim_token TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(dictation_jobs)")
            }
            if "claim_token" not in columns:
                connection.execute("ALTER TABLE dictation_jobs ADD COLUMN claim_token TEXT")
            connection.commit()

    def create(self, request_id: str, user_id: str | None = None) -> DictationJob:
        now = self._now()
        with self._conn() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT OR IGNORE INTO dictation_jobs
                    (request_id, status, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (request_id, JobStatus.ACCEPTED.value, user_id, now, now),
            )
            row = connection.execute(
                "SELECT * FROM dictation_jobs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            connection.commit()
        if row is None:
            raise RuntimeError(f"Could not create dictation job: {request_id}")
        return _row_to_job(row)

    def create_for_owner(self, request_id: str, user_id: str) -> DictationJob | None:
        """Atomically create a job or load it when ``user_id`` owns it."""
        now = self._now()
        with self._conn() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT OR IGNORE INTO dictation_jobs
                    (request_id, status, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (request_id, JobStatus.ACCEPTED.value, user_id, now, now),
            )
            row = connection.execute(
                """
                SELECT * FROM dictation_jobs
                 WHERE request_id = ? AND user_id = ?
                """,
                (request_id, user_id),
            ).fetchone()
            connection.commit()
        return _row_to_job(row) if row else None

    def get(self, request_id: str) -> DictationJob | None:
        with self._conn() as connection:
            row = connection.execute(
                "SELECT * FROM dictation_jobs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return _row_to_job(row) if row else None

    def get_for_owner(self, request_id: str, user_id: str) -> DictationJob | None:
        with self._conn() as connection:
            row = connection.execute(
                """
                SELECT * FROM dictation_jobs
                 WHERE request_id = ? AND user_id = ?
                """,
                (request_id, user_id),
            ).fetchone()
        return _row_to_job(row) if row else None

    def claim_processing(self, request_id: str, claim_token: str) -> JobClaim:
        """Atomically claim a job or reclaim an expired processing lease."""
        with self._conn() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM dictation_jobs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown dictation job: {request_id}")

            status = JobStatus(row["status"])
            now = self._clock()
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            updated_at = _parse_timestamp(row["updated_at"])
            if updated_at is not None and updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            lease_expired = (
                status is JobStatus.PROCESSING
                and updated_at is not None
                and updated_at <= now - self.processing_lease
            )
            owns_lease = row["claim_token"] == claim_token
            unclaimed = not row["claim_token"]
            acquired = status is JobStatus.ACCEPTED or (
                status is JobStatus.PROCESSING
                and (owns_lease or unclaimed or lease_expired)
            )
            if acquired:
                connection.execute(
                    """
                    UPDATE dictation_jobs
                       SET status = ?, claim_token = ?, updated_at = ?
                     WHERE request_id = ?
                    """,
                    (
                        JobStatus.PROCESSING.value,
                        claim_token,
                        now.isoformat(timespec="microseconds"),
                        request_id,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM dictation_jobs WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
            connection.commit()

        if row is None:
            raise KeyError(f"Unknown dictation job: {request_id}")
        return JobClaim(job=_row_to_job(row), acquired=acquired)

    def renew_processing(self, request_id: str, claim_token: str) -> bool:
        """Extend a processing lease only for its current owner."""
        now = self._now()
        with self._conn() as connection:
            cursor = connection.execute(
                """
                UPDATE dictation_jobs
                   SET updated_at = ?
                 WHERE request_id = ?
                   AND status = ?
                   AND claim_token = ?
                """,
                (
                    now,
                    request_id,
                    JobStatus.PROCESSING.value,
                    claim_token,
                ),
            )
            connection.commit()
        return cursor.rowcount == 1

    def update(
        self,
        request_id: str,
        status: JobStatus,
        *,
        raw_text: str | None = None,
        clean_text: str | None = None,
        entry_id: int | None = None,
        error: str | None = None,
        claim_token: str | None = None,
    ) -> DictationJob:
        now = self._now()
        with self._conn() as connection:
            cursor = connection.execute(
                """
                UPDATE dictation_jobs
                   SET status = ?, raw_text = COALESCE(?, raw_text),
                       clean_text = COALESCE(?, clean_text),
                       entry_id = COALESCE(?, entry_id),
                       error = ?, claim_token = COALESCE(?, claim_token),
                       updated_at = ?
                 WHERE request_id = ?
                   AND (? IS NULL OR claim_token = ?)
                """,
                (
                    status.value,
                    raw_text,
                    clean_text,
                    entry_id,
                    error,
                    claim_token,
                    now,
                    request_id,
                    claim_token,
                    claim_token,
                ),
            )
            connection.commit()
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown dictation job: {request_id}")
        job = self.get(request_id)
        if job is None:
            raise KeyError(f"Unknown dictation job: {request_id}")
        return job

    def _now(self) -> str:
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.isoformat(timespec="microseconds")


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _row_to_job(row: sqlite3.Row) -> DictationJob:
    return DictationJob(
        request_id=row["request_id"],
        status=JobStatus(row["status"]),
        user_id=row["user_id"],
        raw_text=row["raw_text"],
        clean_text=row["clean_text"],
        entry_id=row["entry_id"],
        error=row["error"],
        claim_token=row["claim_token"],
        created_at=_parse_timestamp(row["created_at"]),
        updated_at=_parse_timestamp(row["updated_at"]),
    )
