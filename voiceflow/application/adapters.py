"""Small adapters connecting existing local implementations to application ports."""

from collections.abc import Sequence
from typing import Any

import numpy as np

from ..config.snippets import expand_snippets, is_exact_shortcut, load_snippets
from ..core.vad import audio_duration, trim_silence


class LocalAudioPreprocessor:
    """Use the existing local VAD implementation behind the application seam."""

    def __init__(self, minimum_seconds: float = 0.3) -> None:
        self.minimum_seconds = minimum_seconds

    def prepare(self, audio: np.ndarray) -> np.ndarray | None:
        trimmed = trim_silence(audio)
        if audio_duration(trimmed) < self.minimum_seconds:
            return None
        return trimmed


class LocalSnippetExpander:
    """Load local snippets at the start of each workflow execution."""

    def expand(self, transcript: str) -> tuple[str, bool]:
        snippets = load_snippets()
        expanded = expand_snippets(transcript, snippets)
        return expanded, expanded != transcript and is_exact_shortcut(transcript, snippets)


class LocalHistoryRepository:
    """Adapt the local history module to the history repository port."""

    def __init__(self, history_module) -> None:
        self._history = history_module

    def save_entry(
        self,
        raw: str,
        clean: str,
        level: str = "light",
        app: str | None = None,
        request_id: str | None = None,
    ) -> int:
        return self._history.save_entry(
            raw=raw,
            clean=clean,
            level=level,
            app=app,
            request_id=request_id,
        )


class CallableCleaner:
    """Adapt the existing cleaner function to the cleaner port."""

    def __init__(self, cleaner, **provider_options: Any) -> None:
        self._cleaner = cleaner
        self._provider_options = provider_options

    def clean(
        self,
        transcript: str,
        *,
        level: str,
        app_context: str | None = None,
    ) -> str:
        return self._cleaner(
            transcript,
            level=level,
            app_context=app_context,
            **self._provider_options,
        )


class NoopEventPublisher:
    """Default local publisher for callers that do not need live events."""

    def publish(self, event: dict[str, Any]) -> None:
        return None


class CallbackEventPublisher:
    """Adapt a local callback or cloud event client to the event port."""

    def __init__(self, callback) -> None:
        self._callback = callback

    def publish(self, event: dict[str, Any]) -> None:
        self._callback(event)


class SequenceTranscriber:
    """Testing adapter that returns a known transcript sequence."""

    def __init__(self, transcript: str) -> None:
        self.transcript = transcript
        self.last_vocab: Sequence[str] | None = None

    def transcribe(self, audio, vocab: Sequence[str] | None = None) -> str:
        self.last_vocab = vocab
        return self.transcript
