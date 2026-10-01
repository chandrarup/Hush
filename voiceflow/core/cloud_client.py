"""Streaming client used by the thin Hush desktop application."""

from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from collections.abc import Callable
from urllib.parse import urlsplit, urlunsplit

import numpy as np


_END_OF_AUDIO = object()


class CloudTranscriptionError(RuntimeError):
    """Raised when a cloud transcription session cannot complete."""


def ensure_client_id(config: dict) -> str:
    """Return a stable client id, generating one in the supplied config if needed."""
    value = str(config.get("client_id", "")).strip()
    if value:
        return value
    value = f"desktop-{uuid.uuid4().hex[:12]}"
    config["client_id"] = value
    return value


def websocket_url(base_url: str) -> str:
    """Build the authenticated cloud WebSocket URL from the HTTP base URL."""
    parsed = urlsplit(base_url.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CloudTranscriptionError(
            "Set cloud.base_url to the Hush VM address, including http:// or https://."
        )
    scheme = "wss" if parsed.scheme == "https" else "ws"
    path = f"{parsed.path.rstrip('/')}/ws/transcribe"
    return urlunsplit((scheme, parsed.netloc, path, "", ""))


class CloudTranscriptionSession:
    """Send microphone chunks to Hush Cloud and wait for one final result."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client_id: str,
        app_context: dict,
        cleanup_level: str = "light",
        sample_rate: int = 16_000,
        connect_timeout: float = 5,
        final_timeout: float = 90,
        on_partial: Callable[[str], None] | None = None,
    ):
        if not token.strip():
            raise CloudTranscriptionError("Set cloud.token before starting cloud dictation.")
        self._url = websocket_url(base_url)
        self._token = token
        self._client_id = client_id
        self._app_context = dict(app_context)
        self._cleanup_level = cleanup_level
        self._sample_rate = sample_rate
        self._connect_timeout = connect_timeout
        self._final_timeout = final_timeout
        self._on_partial = on_partial
        self._socket = None
        self._send_queue: queue.Queue[bytes | object] = queue.Queue(maxsize=256)
        self._complete = threading.Event()
        self._sender: threading.Thread | None = None
        self._receiver: threading.Thread | None = None
        self._result: dict | None = None
        self._error: str | None = None
        self._closed = False
        self._started_at: float | None = None
        self._first_partial_at: float | None = None
        self._finish_requested_at: float | None = None
        self._completed_at: float | None = None

    def start(self) -> "CloudTranscriptionSession":
        try:
            from websockets.sync.client import connect
        except ImportError as exc:
            raise CloudTranscriptionError(
                "The cloud streaming dependency is missing. Run uv sync."
            ) from exc

        try:
            self._socket = connect(
                self._url,
                open_timeout=self._connect_timeout,
                close_timeout=2,
                max_size=2 * 1024 * 1024,
                additional_headers={"Authorization": f"Bearer {self._token}"},
            )
            self._socket.send(json.dumps({
                "type": "start",
                "client_id": self._client_id,
                "sample_rate": self._sample_rate,
                "channels": 1,
                "encoding": "float32le",
                "cleanup_level": self._cleanup_level,
                "context": self._app_context,
            }))
        except Exception as exc:
            self._close_socket()
            raise CloudTranscriptionError(
                "Could not connect to Hush Cloud. Check the VM address, firewall, and token."
            ) from exc

        self._sender = threading.Thread(
            target=self._send_loop,
            daemon=True,
            name="cloud-audio-sender",
        )
        self._receiver = threading.Thread(
            target=self._receive_loop,
            daemon=True,
            name="cloud-transcript-receiver",
        )
        self._sender.start()
        self._receiver.start()
        self._started_at = time.monotonic()
        return self

    def send_audio(self, chunk: np.ndarray) -> None:
        """Queue one sounddevice callback block without blocking the audio thread."""
        if self._closed or self._complete.is_set():
            return
        mono = np.asarray(chunk, dtype="<f4")
        if mono.ndim > 1:
            mono = mono[:, 0]
        try:
            self._send_queue.put_nowait(np.ascontiguousarray(mono).tobytes())
        except queue.Full:
            self._fail("The cloud connection could not keep up with microphone audio.")

    def finish(self) -> dict:
        """Flush queued audio, signal completion, and return the final transcript event."""
        if self._finish_requested_at is None:
            self._finish_requested_at = time.monotonic()
        if not self._complete.is_set():
            try:
                self._send_queue.put(_END_OF_AUDIO, timeout=1)
            except queue.Full:
                self._fail("The cloud audio queue is full.")

        if not self._complete.wait(self._final_timeout):
            self._fail("Timed out waiting for the cloud transcription result.")

        self._close_socket()
        if self._error:
            raise CloudTranscriptionError(self._error)
        if not self._result:
            raise CloudTranscriptionError("The cloud session ended without a final transcript.")
        return self._result

    @property
    def latency_metrics(self) -> dict[str, float | None]:
        """Return client-observed latency values in milliseconds."""
        first_partial_ms = None
        release_to_final_ms = None
        if self._started_at is not None and self._first_partial_at is not None:
            first_partial_ms = round((self._first_partial_at - self._started_at) * 1000, 1)
        if self._finish_requested_at is not None and self._completed_at is not None:
            release_to_final_ms = round(
                (self._completed_at - self._finish_requested_at) * 1000,
                1,
            )
        return {
            "first_partial_ms": first_partial_ms,
            "release_to_final_ms": release_to_final_ms,
        }

    def abort(self) -> None:
        self._fail("Cloud transcription was cancelled.")

    def _send_loop(self) -> None:
        try:
            while not self._complete.is_set():
                item = self._send_queue.get()
                if item is _END_OF_AUDIO:
                    self._socket.send(json.dumps({"type": "end_of_audio"}))
                    return
                self._socket.send(item)
        except Exception as exc:
            self._fail(f"Audio streaming failed: {exc}")

    def _receive_loop(self) -> None:
        try:
            for message in self._socket:
                if not isinstance(message, str):
                    continue
                event = json.loads(message)
                event_type = event.get("type")
                if event_type == "partial_transcript":
                    text = str(event.get("text", "")).strip()
                    if self._first_partial_at is None:
                        self._first_partial_at = time.monotonic()
                    if text and self._on_partial is not None:
                        self._on_partial(text)
                elif event_type == "final_transcript":
                    self._result = event
                    self._completed_at = time.monotonic()
                    self._complete.set()
                    return
                elif event_type == "error":
                    self._fail(str(event.get("message") or "Cloud transcription failed."))
                    return
        except Exception as exc:
            if not self._complete.is_set():
                self._fail(f"Cloud connection closed unexpectedly: {exc}")
        finally:
            if not self._complete.is_set():
                self._fail("Cloud connection closed before a final transcript was returned.")

    def _fail(self, message: str) -> None:
        if self._complete.is_set():
            return
        self._error = message
        self._complete.set()
        self._close_socket()

    def _close_socket(self) -> None:
        self._closed = True
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
