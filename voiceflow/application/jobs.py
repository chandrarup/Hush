"""Durable dictation job types shared by local and hosted execution."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    ACCEPTED = "accepted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DISCARDED = "discarded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class DictationJob:
    request_id: str
    status: JobStatus
    user_id: str | None = None
    raw_text: str | None = None
    clean_text: str | None = None
    entry_id: int | None = None
    error: str | None = None
    claim_token: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class JobClaim:
    """Result of an atomic attempt to acquire a job for processing."""

    job: DictationJob
    acquired: bool
