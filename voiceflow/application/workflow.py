"""The platform-neutral dictation workflow.

The workflow is intentionally deep: callers provide a small set of adapters,
then receive one stable result. Desktop startup, FastAPI, and future cloud
workers can all use the same interface.
"""

from datetime import datetime
from uuid import uuid4

from .models import DictationResult, DictationStatus
from .ports import (
    AudioInput,
    AudioPreprocessor,
    EventPublisher,
    HistoryRepository,
    SnippetExpander,
    TranscriptCleaner,
    Transcriber,
)


class DictationWorkflow:
    """Process one recording using injected adapters."""

    def __init__(
        self,
        *,
        preprocessor: AudioPreprocessor,
        transcriber: Transcriber,
        cleaner: TranscriptCleaner,
        history: HistoryRepository,
        snippets: SnippetExpander,
        events: EventPublisher | None = None,
    ) -> None:
        self._preprocessor = preprocessor
        self._transcriber = transcriber
        self._cleaner = cleaner
        self._history = history
        self._snippets = snippets
        self._events = events

    def process(
        self,
        audio: AudioInput,
        *,
        vocab: list[str] | None = None,
        cleanup_level: str = "light",
        app_context: str | None = None,
        request_id: str | None = None,
    ) -> DictationResult:
        """Process one recording and return a durable application result.

        The method is synchronous by design. The caller decides whether this
        work runs in a desktop thread, a worker process, or a cloud job.
        """

        request_id = request_id or uuid4().hex
        prepared = self._preprocessor.prepare(audio)
        if prepared is None:
            return self._result(request_id, DictationStatus.DISCARDED)

        try:
            raw_text = self._transcriber.transcribe(prepared, vocab=vocab).strip()
            if not raw_text:
                return self._result(request_id, DictationStatus.DISCARDED)

            expanded_text, was_exact_snippet = self._snippets.expand(raw_text)
            if was_exact_snippet:
                clean_text = expanded_text
            else:
                clean_text = self._cleaner.clean(
                    expanded_text,
                    level=cleanup_level,
                    app_context=app_context,
                ).strip()

            entry_id = self._history.save_entry(
                raw=raw_text,
                clean=clean_text,
                level=cleanup_level,
                app=app_context,
            )
            result = self._result(
                request_id,
                DictationStatus.COMPLETED,
                raw_text=raw_text,
                clean_text=clean_text,
                entry_id=entry_id,
                app_context=app_context,
                cleanup_level=cleanup_level,
            )
            self._publish_result(result)
            return result
        except Exception as exc:
            result = self._result(
                request_id,
                DictationStatus.FAILED,
                app_context=app_context,
                cleanup_level=cleanup_level,
                error=str(exc),
            )
            self._publish_result(result)
            return result

    def _result(self, request_id: str, status: DictationStatus, **kwargs) -> DictationResult:
        return DictationResult(
            request_id=request_id,
            status=status,
            completed_at=datetime.now(),
            **kwargs,
        )

    def _publish_result(self, result: DictationResult) -> None:
        if self._events is None:
            return
        self._events.publish(
            {
                "type": "dictation_completed",
                "request_id": result.request_id,
                "status": result.status.value,
                "entry_id": result.entry_id,
                "raw": result.raw_text,
                "clean": result.clean_text,
                "level": result.cleanup_level,
                "app": result.app_context,
                "words": len(result.clean_text.split()),
            }
        )
