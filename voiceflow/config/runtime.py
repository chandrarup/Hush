"""Environment-backed runtime settings for local and hosted execution."""

import os
from dataclasses import dataclass

from .paths import HISTORY_DB_PATH


@dataclass(frozen=True)
class RuntimeSettings:
    """Settings that vary by deployment environment, not user preference."""

    mode: str = "local"
    transcription_provider: str = "local"
    cleanup_provider: str = "local"
    database_url: str = f"sqlite:///{HISTORY_DB_PATH}"
    queue_backend: str = "in_process"
    audio_bucket: str | None = None
    auth_required: bool = False

    @classmethod
    def from_environment(cls) -> "RuntimeSettings":
        return cls(
            mode=os.getenv("VOICEFLOW_RUNTIME_MODE", "local"),
            transcription_provider=os.getenv("VOICEFLOW_TRANSCRIPTION_PROVIDER", "local"),
            cleanup_provider=os.getenv("VOICEFLOW_CLEANUP_PROVIDER", "local"),
            database_url=os.getenv("VOICEFLOW_DATABASE_URL", f"sqlite:///{HISTORY_DB_PATH}"),
            queue_backend=os.getenv("VOICEFLOW_QUEUE_BACKEND", "in_process"),
            audio_bucket=os.getenv("VOICEFLOW_AUDIO_BUCKET") or None,
            auth_required=_as_bool(os.getenv("VOICEFLOW_AUTH_REQUIRED", "false")),
        )


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
