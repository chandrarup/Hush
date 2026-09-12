"""Small domain models shared by local and cloud application adapters."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class DictationStatus(str, Enum):
    """Lifecycle states visible to callers of the dictation workflow."""

    COMPLETED = "completed"
    FAILED = "failed"
    DISCARDED = "discarded"


@dataclass(frozen=True)
class DictationResult:
    """The stable result returned after one dictation has been processed."""

    request_id: str
    status: DictationStatus
    raw_text: str = ""
    clean_text: str = ""
    entry_id: int | None = None
    app_context: str | None = None
    cleanup_level: str = "light"
    error: str | None = None
    completed_at: datetime | None = None
