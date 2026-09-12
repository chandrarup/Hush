"""Stable interfaces used by the application workflow.

These interfaces deliberately avoid references to desktop libraries, SQLite,
HTTP clients, cloud SDKs, or model SDKs. Adapters can satisfy them locally or
in a hosted deployment.
"""

from collections.abc import Sequence
from typing import Any, Protocol

from .jobs import DictationJob, JobStatus


AudioInput = Any


class AudioPreprocessor(Protocol):
    """Prepare captured audio and decide whether it is long enough to use."""

    def prepare(self, audio: AudioInput) -> AudioInput | None: ...


class Transcriber(Protocol):
    """Convert one prepared audio recording into text."""

    def transcribe(
        self,
        audio: AudioInput,
        vocab: Sequence[str] | None = None,
    ) -> str: ...


class TranscriptCleaner(Protocol):
    """Turn a raw transcript into text ready for injection."""

    def clean(
        self,
        transcript: str,
        *,
        level: str,
        app_context: str | None = None,
    ) -> str: ...


class SnippetExpander(Protocol):
    """Expand spoken shortcuts at the final text-processing seam."""

    def expand(self, transcript: str) -> tuple[str, bool]: ...


class HistoryRepository(Protocol):
    """Persist a completed transcript and return its durable identifier."""

    def save_entry(
        self,
        raw: str,
        clean: str,
        level: str = "light",
        app: str | None = None,
    ) -> int: ...


class JobRepository(Protocol):
    """Persist job lifecycle state outside the worker process."""

    def create(self, request_id: str, user_id: str | None = None) -> DictationJob: ...

    def get(self, request_id: str) -> DictationJob | None: ...

    def update(
        self,
        request_id: str,
        status: JobStatus,
        *,
        raw_text: str | None = None,
        clean_text: str | None = None,
        entry_id: int | None = None,
        error: str | None = None,
    ) -> DictationJob: ...


class EventPublisher(Protocol):
    """Publish application events without prescribing the transport."""

    def publish(self, event: dict[str, Any]) -> None: ...
