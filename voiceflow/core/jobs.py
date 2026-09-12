"""SQLite adapter for the durable local dictation job repository."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..application.jobs import DictationJob, JobClaim, JobStatus
from ..config.paths import HISTORY_DB_PATH


class SQLiteJobRepository:
    """Persist job state in SQLite behind a cloud-ready interface."""

    def __init__(self, db_path: Path = HISTORY_DB_PATH) -> None:
        self.db_path = Path(db_path)
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
        now = _now()
        with self._conn() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO dictation_jobs
                    (request_id, status, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (request_id, JobStatus.ACCEPTED.value, user_id, now, now),
            )
            connection.commit()
        job = self.get(request_id)
        if job is None:
            raise RuntimeError(f"Could not create dictation job: {request_id}")
        return job

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
        """Atomically claim an accepted or unclaimed processing job."""
        with self._conn() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM dictation_jobs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown dictation job: {request_id}")

            status = JobStatus(row["status"])
            token_owned_by_other = (
                status is JobStatus.PROCESSING
                and row["claim_token"]
                and row["claim_token"] != claim_token
            )
            eligible = status in {JobStatus.ACCEPTED, JobStatus.PROCESSING}
            acquired = eligible and not token_owned_by_other
            if acquired:
                connection.execute(
                    """
                    UPDATE dictation_jobs
                       SET status = ?, claim_token = ?, updated_at = ?
                     WHERE request_id = ?
                    """,
                    (JobStatus.PROCESSING.value, claim_token, _now(), request_id),
                )
            connection.commit()

        job = self.get(request_id)
        if job is None:
            raise KeyError(f"Unknown dictation job: {request_id}")
        return JobClaim(job=job, acquired=acquired)

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
        now = _now()
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
