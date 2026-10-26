"""FastAPI dashboard and cloud transcription service for Hush.

The desktop starts this app in UI-only mode on loopback. The VM runs it as the
cloud service, where it owns transcription, cleanup, snippets, and history.

Serves:
  GET  /              → dashboard HTML
  GET  /history       → transcription entries (JSON)
  GET  /stats         → word count, wpm, days
  GET  /health        → unauthenticated container health probe
  GET  /status        → authenticated app state
  POST /transcribe    → transcribe a browser-uploaded WAV file
  POST /settings      → update cleanup level, hotkey display name
  DELETE /history     → clear all history
  DELETE /history/{id}→ delete one entry
  GET  /events        → Server-Sent Events stream for live updates
  WS   /ws/transcribe → live desktop audio and transcript events
"""

import asyncio
import hmac
import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import uuid
import wave
from typing import Any, Callable
from urllib.parse import urlsplit

import numpy as np

try:
    from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    _FASTAPI_OK = True
except ImportError:
    _FASTAPI_OK = False

from ..core import history as _history
from ..core.cleaner import clean_transcript
from ..config import load_config
from ..config.snippets import (
    SNIPPETS_PATH,
    add_snippet,
    expand_snippets,
    get_snippets_snapshot,
    is_exact_shortcut,
    load_snippets,
    remove_snippet,
    SnippetConflictError,
    update_snippet,
)
from ..config.paths import CONFIG_PATH
from ..config.defaults import DEFAULT_CONFIG
from ..cloud.managed_state import (
    ManagedStateError,
    get_managed_state,
    initialize_managed_state,
    managed_state_enabled,
)
from ..platform.factory import get_platform_services


def _configured_whisper_model() -> str:
    """Return the cloud Whisper model selected at container startup."""
    return os.getenv("HUSH_WHISPER_MODEL", "base.en").strip() or "base.en"


def _configured_whisper_beam_size() -> int:
    """Return a bounded beam size; one favors latency on CPU-only VMs."""
    try:
        beam_size = int(os.getenv("HUSH_WHISPER_BEAM_SIZE", "5"))
    except ValueError:
        return 5
    return min(max(beam_size, 1), 10)


# ── Shared state (updated by main.py) ─────────────────────────────── #
_state: dict[str, Any] = {
    "status":        "idle",       # idle | recording | processing
    "status_updated_at": 0,        # Startup Idle must not override another replica's activity.
    "cleanup_level": "light",      # none | light | medium | high
    "hotkey":        "ctrl_l",
    "asr_engine":    "whisper",
    "ollama_model":  "llama3.2:3b",
    "web_model":     pathlib.Path(_configured_whisper_model()).name,
}

def update_state(**kwargs):
    """Thread-safe state update called from main.py."""
    if "status" in kwargs:
        kwargs.setdefault("status_updated_at", time.time() * 1000)
    _state.update(kwargs)


# ── SSE subscriber list ────────────────────────────────────────────── #
_subscribers: list[asyncio.Queue] = []
_sub_lock = threading.Lock()
_event_loop: asyncio.AbstractEventLoop | None = None
_hotkey_updater: Callable[[str], bool] | None = None
_runtime_config_updater: Callable[[dict[str, Any]], None] | None = None
_onboarding_reconnect_event = threading.Event()

_VALID_CLEANUP_LEVELS = {"none", "light", "medium", "high"}
_VALID_ASR_ENGINES = {"auto", "parakeet", "whisper"}
_WEB_AUDIO_SAMPLE_RATE = 16_000
_WEB_AUDIO_MAX_BYTES = 10 * 1024 * 1024
_WEB_AUDIO_MAX_SECONDS = 60
_web_transcriber: Any | None = None
_web_transcriber_init_lock = threading.Lock()
_web_transcribe_lock = threading.Lock()
_cloud_work_slots = threading.BoundedSemaphore(2)
_web_status_lock = threading.Lock()
_web_active_transcriptions = 0
_history_enabled = True
_managed_startup_error: str | None = None
_active_cloud_sessions: dict[str, dict[str, Any]] = {}
_cloud_sessions_lock = threading.Lock()
_CLOUD_PARTIAL_INTERVAL_SECONDS = 1.5
_CLOUD_MIN_PARTIAL_SECONDS = 0.75
_CLOUD_MAX_AUDIO_BYTES = _WEB_AUDIO_SAMPLE_RATE * _WEB_AUDIO_MAX_SECONDS * 4
_CLOUD_MAX_CHUNK_BYTES = 256 * 1024


class WebAudioError(ValueError):
    """Raised when a browser upload is not a supported PCM WAV file."""


def _decode_web_wav(payload: bytes) -> np.ndarray:
    """Decode a mono, 16 kHz, 16-bit PCM WAV upload into float32 audio."""
    if not payload:
        raise WebAudioError("Choose a non-empty audio file.")
    if len(payload) > _WEB_AUDIO_MAX_BYTES:
        raise WebAudioError("Audio file exceeds the 10 MB limit.")

    try:
        with wave.open(io.BytesIO(payload), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            compression = wav_file.getcomptype()
            if compression != "NONE":
                raise WebAudioError("Audio must use uncompressed PCM WAV encoding.")
            if channels != 1 or sample_width != 2 or sample_rate != _WEB_AUDIO_SAMPLE_RATE:
                raise WebAudioError("Audio must be mono 16-bit PCM WAV at 16 kHz.")
            if frame_count > _WEB_AUDIO_SAMPLE_RATE * _WEB_AUDIO_MAX_SECONDS:
                raise WebAudioError("Audio must be 60 seconds or shorter.")
            pcm_bytes = wav_file.readframes(frame_count)
    except (EOFError, wave.Error) as exc:
        raise WebAudioError("Audio could not be read as a WAV file.") from exc

    audio = np.frombuffer(pcm_bytes, dtype="<i2").astype(np.float32) / 32768.0
    if audio.size == 0:
        raise WebAudioError("Choose a non-empty audio file.")
    return audio


async def _read_web_audio(request: Any) -> bytes:
    """Read an upload incrementally and stop as soon as it exceeds the limit."""
    chunks: list[bytes] = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > _WEB_AUDIO_MAX_BYTES:
            raise WebAudioError("Audio file exceeds the 10 MB limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def _get_web_transcriber():
    """Load the configured English Whisper model once, on the first request."""
    global _web_transcriber
    if _web_transcriber is None:
        with _web_transcriber_init_lock:
            if _web_transcriber is None:
                from ..core.transcriber import create_transcriber

                _web_transcriber = create_transcriber(
                    engine="whisper",
                    model=_configured_whisper_model(),
                    language="en",
                    compute_type_cpu="int8",
                    beam_size=_configured_whisper_beam_size(),
                )
    return _web_transcriber


def _transcribe_web_audio(audio: np.ndarray) -> str:
    """Trim silence and serialize model access for predictable CPU usage."""
    from ..core.vad import trim_silence

    trimmed = trim_silence(audio, sample_rate=_WEB_AUDIO_SAMPLE_RATE)
    with _web_transcribe_lock:
        return _get_web_transcriber().transcribe(trimmed).strip()


def _allowed_web_hosts() -> set[str]:
    """Return hostnames permitted to serve the browser dashboard and API."""
    configured = {
        host.strip().lower()
        for host in os.getenv("HUSH_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    }
    return {"127.0.0.1", "localhost", "::1", *configured}


def _team_token() -> str:
    """Return the shared token from Secret Manager in the managed VM runtime."""
    if managed_state_enabled():
        try:
            return get_managed_state().team_token
        except ManagedStateError:
            return ""
    return os.getenv("HUSH_TEAM_TOKEN", "").strip()


def _cloud_mode_enabled() -> bool:
    """Return whether this process is the remotely exposed cloud service."""
    return os.getenv("HUSH_SERVER_MODE", "").strip().lower() == "cloud"


def _validate_cloud_configuration() -> None:
    """Fail closed when a remotely exposed service has no authentication token."""
    if _cloud_mode_enabled() and not _team_token():
        raise RuntimeError("HUSH_TEAM_TOKEN is required when HUSH_SERVER_MODE=cloud.")


def _token_matches(provided: str | None) -> bool:
    expected = _team_token()
    return bool(expected and provided and hmac.compare_digest(provided, expected))


def _request_token(request: Any) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _request_token_is_valid(request: Any) -> bool:
    """Require the configured token when present; loopback development stays token-free."""
    return not _team_token() or _token_matches(_request_token(request))


def _is_public_http_path(path: str) -> bool:
    """Keep only the dashboard shell, static assets, and health probe public."""
    return path in {"/", "/health", "/ready"} or path.startswith("/ui/")


def _request_origin_is_trusted(request: Any) -> bool:
    """Require an allowed host and a matching same-origin browser request."""
    request_host = urlsplit(f"//{request.headers.get('host', '')}").hostname
    if not request_host or request_host.lower() not in _allowed_web_hosts():
        return False

    origin = request.headers.get("origin")
    if not origin:
        return False
    parsed_origin = urlsplit(origin)
    return (
        parsed_origin.scheme in {"http", "https"}
        and parsed_origin.netloc.lower() == request.headers.get("host", "").lower()
        and (parsed_origin.hostname or "").lower() in _allowed_web_hosts()
    )


def _change_web_transcription_count(delta: int) -> None:
    """Keep shared status accurate while browser transcriptions overlap."""
    global _web_active_transcriptions
    with _web_status_lock:
        _web_active_transcriptions = max(0, _web_active_transcriptions + delta)
        status = "processing" if _web_active_transcriptions else "idle"
    update_state(status=status)
    push_event({"type": "status", "value": status})


def _cloud_sessions_snapshot() -> list[dict[str, Any]]:
    with _cloud_sessions_lock:
        return [dict(session) for session in _active_cloud_sessions.values()]


def _set_cloud_session(session_id: str, **values: Any) -> None:
    with _cloud_sessions_lock:
        session = _active_cloud_sessions.setdefault(session_id, {"session_id": session_id})
        session.update(values)
        event = dict(session)
    push_event({"type": "live_session", "session": event})


def _remove_cloud_session(session_id: str) -> None:
    with _cloud_sessions_lock:
        _active_cloud_sessions.pop(session_id, None)


def _clean_cloud_transcript(raw_text: str, cleanup_level: str, app_name: str | None) -> str:
    """Run snippet expansion and cleanup using configuration stored on the VM."""
    snippets = load_snippets()
    if is_exact_shortcut(raw_text, snippets):
        return expand_snippets(raw_text, snippets)

    if managed_state_enabled():
        try:
            saved_settings = get_managed_state().get_settings()
        except ManagedStateError:
            saved_settings = _state
        config = {
            "llm": {
                **DEFAULT_CONFIG.get("llm", {}),
                "cleanup_level": saved_settings.get("cleanup_level", "light"),
                "ollama_model": saved_settings.get("ollama_model", "llama3.2:3b"),
            }
        }
    else:
        config = load_config()
    llm_cfg = config.get("llm", {})
    level = cleanup_level if cleanup_level in _VALID_CLEANUP_LEVELS else llm_cfg.get(
        "cleanup_level", "light"
    )
    return clean_transcript(
        raw_text,
        level=level,
        docker_llm_url=llm_cfg.get(
            "docker_llm_url", "http://localhost:12434/engines/llama.cpp/v1"
        ),
        docker_llm_model=llm_cfg.get("docker_llm_model", ""),
        ollama_model=llm_cfg.get("ollama_model", "llama3.2:3b"),
        ollama_base_url=os.getenv(
            "HUSH_OLLAMA_BASE_URL",
            llm_cfg.get("ollama_base_url", "http://localhost:11434"),
        ),
        temperature=llm_cfg.get("temperature", 0.1),
        max_tokens=llm_cfg.get("max_tokens", 500),
        app_context=app_name,
    ).strip()


def register_hotkey_updater(updater: Callable[[str], bool]) -> None:
    """Register the application callback used to apply a new hotkey immediately."""
    global _hotkey_updater
    _hotkey_updater = updater


def register_runtime_config_updater(updater: Callable[[dict[str, Any]], None]) -> None:
    """Register the application callback for settings changed at runtime."""
    global _runtime_config_updater
    _runtime_config_updater = updater


def begin_onboarding_reconnect_window() -> None:
    """Clear the reconnect signal before Hush resumes an unfinished setup."""
    _onboarding_reconnect_event.clear()


def wait_for_onboarding_reconnect(timeout_seconds: float) -> bool:
    """Wait briefly for the existing onboarding page to resume permission polling."""
    return _onboarding_reconnect_event.wait(timeout_seconds)


def push_event(event: dict):
    """
    Push a live event to all connected dashboard clients.
    Thread-safe — called from the pipeline thread.
    """
    global _event_loop
    if event.get("type") == "status" and "updated_at" not in event:
        event = {**event, "updated_at": _state.get("status_updated_at", 0)}
    if _event_loop is None or _event_loop.is_closed():
        return

    def _do_push():
        with _sub_lock:
            for q in list(_subscribers):
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    _event_loop.call_soon_threadsafe(_do_push)


# ── App ───────────────────────────────────────────────────────────── #

if _FASTAPI_OK:
    app = FastAPI(title="Hush", docs_url=None, redoc_url=None)

    _source_ui_dir = pathlib.Path(__file__).parent / "ui"
    _bundle_ui_dir = pathlib.Path(sys.executable).parent.parent / "Resources" / "ui"
    _UI_DIR = _source_ui_dir if _source_ui_dir.exists() else _bundle_ui_dir

    @app.middleware("http")
    async def _require_authenticated_api(request: Request, call_next):
        """Reject untrusted hosts, unauthenticated APIs, and cross-origin writes."""
        # Infrastructure probes use Pod IP Host headers. Only these read-only
        # probe handlers bypass the application's canonical-host boundary.
        if request.method == "GET" and request.url.path in {"/health", "/ready"}:
            return await call_next(request)
        request_host = urlsplit(f"//{request.headers.get('host', '')}").hostname
        if not request_host or request_host.lower() not in _allowed_web_hosts():
            return JSONResponse({"error": "Untrusted host."}, status_code=403)
        if not _is_public_http_path(request.url.path) and not _request_token_is_valid(request):
            return JSONResponse({"error": "Invalid or missing team token."}, status_code=401)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if not _request_origin_is_trusted(request):
                return JSONResponse({"error": "Cross-origin request rejected."}, status_code=403)
        return await call_next(request)

    @app.on_event("startup")
    async def _startup():
        global _event_loop, _managed_startup_error
        _managed_startup_error = None
        if managed_state_enabled():
            try:
                managed = await asyncio.to_thread(initialize_managed_state)
                saved_settings = await asyncio.to_thread(managed.get_settings)
                for key in ("cleanup_level", "hotkey", "asr_engine", "ollama_model"):
                    if key in saved_settings:
                        _state[key] = saved_settings[key]
            except Exception as exc:
                _managed_startup_error = str(exc)
                raise RuntimeError(
                    "Hush could not initialize its managed state dependencies."
                ) from exc
        _validate_cloud_configuration()
        if os.getenv("HUSH_WARM_MODEL") == "1":
            await asyncio.to_thread(_get_web_transcriber)
        _event_loop = asyncio.get_running_loop()
        if _history_enabled:
            _history.init_db()
        print("[api] Server ready at http://localhost:57327")

    @app.on_event("shutdown")
    async def _shutdown():
        if managed_state_enabled():
            await asyncio.to_thread(get_managed_state().close)

    # ── Dashboard HTML ──────────────────────────────────────────── #

    @app.get("/")
    async def index():
        html_path = _UI_DIR / "index.html"
        if html_path.exists():
            return FileResponse(str(html_path))
        return JSONResponse({"error": "Dashboard UI not found"}, status_code=404)

    @app.get("/ui/{path:path}")
    async def static_files(path: str):
        ui_root = _UI_DIR.resolve()
        file_path = (ui_root / path).resolve()
        try:
            file_path.relative_to(ui_root)
        except ValueError:
            return JSONResponse({"error": "Not found"}, status_code=404)
        if file_path.is_file():
            return FileResponse(str(file_path))
        return JSONResponse({"error": "Not found"}, status_code=404)

    # ── REST endpoints ──────────────────────────────────────────── #

    @app.get("/health")
    async def get_health():
        return {"status": "ok"}

    @app.get("/ready")
    async def get_readiness():
        """Report whether every required managed dependency is usable."""
        if pathlib.Path("/tmp/hush-draining").exists():
            return JSONResponse({"status": "not-ready", "reason": "draining"}, status_code=503)
        if _managed_startup_error:
            return JSONResponse(
                {"status": "not-ready", "error": "managed state initialization failed"},
                status_code=503,
            )
        if not managed_state_enabled():
            return {"status": "ready", "mode": "local"}
        checks = await asyncio.to_thread(get_managed_state().check_ready)
        checks["model"] = os.getenv("HUSH_WARM_MODEL") != "1" or _web_transcriber is not None
        if not all(checks.values()):
            return JSONResponse(
                {"status": "not-ready", "checks": checks}, status_code=503
            )
        return {"status": "ready", "mode": "managed", "checks": checks}

    @app.get("/history")
    async def get_history(limit: int = 200, offset: int = 0):
        if not _history_enabled:
            return []
        return _history.get_entries(limit=limit, offset=offset)

    @app.get("/stats")
    async def get_stats():
        if not _history_enabled:
            return {"total_words": 0, "avg_wpm": 0, "active_days": 0}
        return _history.get_stats()

    @app.get("/status")
    async def get_status():
        saved = {}
        if managed_state_enabled():
            try:
                saved = await asyncio.to_thread(lambda: get_managed_state().get_settings())
            except ManagedStateError:
                pass
        return {**_state, **saved, "live_sessions": _cloud_sessions_snapshot()}

    @app.post("/transcribe")
    async def post_transcribe(request: Request):
        if not _cloud_work_slots.acquire(blocking=False):
            return JSONResponse(
                {"error": "This replica is busy. Please retry shortly."},
                status_code=429, headers={"Retry-After": "2"},
            )
        try:
            return await _post_transcribe(request)
        finally:
            _cloud_work_slots.release()

    async def _post_transcribe(request: Request):
        if not _history_enabled:
            return JSONResponse(
                {"error": "Diagnostic upload is available on the cloud dashboard only."},
                status_code=409,
            )
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > _WEB_AUDIO_MAX_BYTES:
                    return JSONResponse(
                        {"error": "Audio file exceeds the 10 MB limit."},
                        status_code=413,
                    )
            except ValueError:
                return JSONResponse({"error": "Invalid Content-Length header."}, status_code=400)

        try:
            payload = await _read_web_audio(request)
            audio = _decode_web_wav(payload)
        except WebAudioError as exc:
            status_code = 413 if "10 MB limit" in str(exc) else 400
            return JSONResponse({"error": str(exc)}, status_code=status_code)

        upload: dict[str, Any] | None = None
        if managed_state_enabled():
            try:
                upload = await asyncio.to_thread(
                    get_managed_state().store_upload,
                    payload,
                    request.headers.get("x-hush-filename"),
                )
            except ManagedStateError as exc:
                print(f"[api] Cloud Storage upload failed: {exc}")
                return JSONResponse(
                    {"error": "The recording could not be stored."}, status_code=503
                )

        _change_web_transcription_count(1)
        try:
            text = await asyncio.to_thread(_transcribe_web_audio, audio)
            history_id = None
            if text:
                history_id = _history.save_entry(
                    raw=text,
                    clean=text,
                    level="none",
                    app="Web upload",
                    client_id="web-upload",
                    status="final",
                )
                entry = _history.get_entry(history_id)
                if entry:
                    push_event({"type": "new_entry", "entry": entry})
            if upload is not None:
                await asyncio.to_thread(
                    get_managed_state().complete_upload,
                    upload["id"],
                    history_id,
                )
                upload["status"] = "completed"
            response: dict[str, Any] = {"text": text, "history_id": history_id}
            if upload is not None:
                response["upload"] = upload
            return response
        except RuntimeError as exc:
            print(f"[api] Web transcriber unavailable: {exc}")
            if upload is not None:
                await asyncio.to_thread(
                    get_managed_state().fail_upload,
                    upload["id"],
                    "transcription model unavailable",
                )
            return JSONResponse(
                {"error": "The transcription model could not be loaded."},
                status_code=503,
            )
        except Exception as exc:
            print(f"[api] Browser transcription failed: {exc}")
            if upload is not None:
                try:
                    await asyncio.to_thread(
                        get_managed_state().fail_upload,
                        upload["id"],
                        "transcription failed",
                    )
                except Exception:
                    pass
            return JSONResponse({"error": "Transcription failed."}, status_code=500)
        finally:
            _change_web_transcription_count(-1)

    @app.post("/settings")
    async def post_settings(request: Request):
        data = await request.json()
        allowed = {"cleanup_level", "hotkey", "asr_engine", "ollama_model"}
        if "cleanup_level" in data and data["cleanup_level"] not in _VALID_CLEANUP_LEVELS:
            return JSONResponse({"error": "Invalid cleanup level."}, status_code=400)
        if "asr_engine" in data and data["asr_engine"] not in _VALID_ASR_ENGINES:
            return JSONResponse({"error": "Invalid speech recognition engine."}, status_code=400)
        if "ollama_model" in data and (
            not isinstance(data["ollama_model"], str) or not data["ollama_model"].strip()
        ):
            return JSONResponse({"error": "A valid language model is required."}, status_code=400)
        if "hotkey" in data:
            if not isinstance(data["hotkey"], str) or not data["hotkey"].strip():
                return JSONResponse({"error": "A valid hotkey is required."}, status_code=400)
            if _hotkey_updater is not None and not _hotkey_updater(data["hotkey"]):
                return JSONResponse({"error": "Could not apply the selected hotkey."}, status_code=400)
        for k, v in data.items():
            if k in allowed:
                _state[k] = v
        runtime_updates = {
            key: data[key]
            for key in ("cleanup_level", "asr_engine", "ollama_model")
            if key in data
        }
        if runtime_updates and _runtime_config_updater is not None:
            _runtime_config_updater(runtime_updates)
        # Persist cleanup_level to config if changed
        if "cleanup_level" in data:
            _persist_cleanup_level(data["cleanup_level"])
        if "asr_engine" in data or "ollama_model" in data:
            _persist_runtime_settings(runtime_updates)
        if "hotkey" in data:
            _persist_hotkey(data["hotkey"])
        return {
            "ok": True,
            "state": dict(_state),
            "restart_required": ["asr_engine"] if "asr_engine" in data else [],
        }

    @app.get("/snippets")
    async def get_snippets():
        if not _history_enabled:
            return {"path": "cloud", "snippets": [], "version": ""}
        snippets, version = get_snippets_snapshot()
        return {
            "path": "cloud-sql" if managed_state_enabled() else str(SNIPPETS_PATH),
            "snippets": [
                {**snippet, "index": index, "version": version}
                for index, snippet in enumerate(snippets)
            ],
            "version": version,
        }

    @app.post("/snippets")
    async def post_snippet(request: Request):
        if not _history_enabled:
            return JSONResponse(
                {"error": "Manage snippets from the cloud dashboard."}, status_code=409
            )
        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JSONResponse({"error": "Malformed JSON."}, status_code=400)
        if not isinstance(data, dict):
            return JSONResponse({"error": "A snippet object is required."}, status_code=400)
        try:
            snippets = add_snippet(
                data.get("name", ""),
                data.get("shortcut", ""),
                data.get("text", ""),
            )
            return {"ok": True, "snippets": snippets}
        except (AttributeError, TypeError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.put("/snippets/{snippet_index}")
    async def put_snippet(snippet_index: int, request: Request):
        if not _history_enabled:
            return JSONResponse(
                {"error": "Manage snippets from the cloud dashboard."}, status_code=409
            )
        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JSONResponse({"error": "Malformed JSON."}, status_code=400)
        if not isinstance(data, dict):
            return JSONResponse({"error": "A snippet object is required."}, status_code=400)
        try:
            snippets = update_snippet(
                snippet_index,
                data.get("name", ""),
                data.get("shortcut", ""),
                data.get("text", ""),
            )
            return {"ok": True, "snippets": snippets}
        except IndexError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        except (AttributeError, TypeError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.delete("/snippets/{snippet_index}")
    async def delete_snippet(snippet_index: int, version: str | None = None):
        if not _history_enabled:
            return JSONResponse(
                {"error": "Manage snippets from the cloud dashboard."}, status_code=409
            )
        if not version:
            return JSONResponse(
                {"error": "A snippet list version is required."},
                status_code=428,
            )
        try:
            return {"ok": True, "snippets": remove_snippet(snippet_index, version)}
        except SnippetConflictError as exc:
            return JSONResponse({"error": str(exc)}, status_code=409)
        except IndexError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @app.delete("/history")
    async def clear_history():
        if not _history_enabled:
            return JSONResponse({"error": "History is stored in Hush Cloud."}, status_code=409)
        _history.clear_all()
        return {"ok": True}

    @app.delete("/history/{entry_id}")
    async def delete_entry(entry_id: int):
        if not _history_enabled:
            return JSONResponse({"error": "History is stored in Hush Cloud."}, status_code=409)
        _history.delete_entry(entry_id)
        return {"ok": True}

    # ── Live cloud transcription ─────────────────────────────────── #

    @app.websocket("/ws/transcribe")
    async def websocket_transcribe(websocket: WebSocket):
        if not _history_enabled:
            await websocket.close(code=1008, reason="Cloud transcription is disabled locally.")
            return
        configured_token = _team_token()
        provided_token = _request_token(websocket)
        if not configured_token:
            await websocket.close(code=1011, reason="Cloud token is not configured.")
            return
        if not _token_matches(provided_token):
            await websocket.close(code=1008, reason="Invalid or missing team token.")
            return

        await websocket.accept()
        if not _cloud_work_slots.acquire(blocking=False):
            await websocket.send_json({"type": "error", "message": "This replica is busy. Please retry shortly."})
            await websocket.close(code=1013)
            return
        session_id = uuid.uuid4().hex[:16]
        client_id = "unknown"
        app_name: str | None = None
        cleanup_level = "light"
        audio_chunks: list[np.ndarray] = []
        total_bytes = 0
        last_partial_at = 0.0
        last_partial_text = ""
        session_registered = False

        try:
            try:
                start_message = json.loads(await websocket.receive_text())
            except (json.JSONDecodeError, TypeError, ValueError):
                await websocket.send_json({
                    "type": "error",
                    "message": "The cloud session start message is invalid.",
                })
                return

            context = start_message.get("context", {})
            client_id = str(start_message.get("client_id", "")).strip()[:128]
            app_name = str(context.get("app", "")).strip()[:200] if isinstance(context, dict) else ""
            cleanup_level = str(start_message.get("cleanup_level", "light")).strip()
            valid_start = (
                start_message.get("type") == "start"
                and client_id
                and start_message.get("sample_rate") == _WEB_AUDIO_SAMPLE_RATE
                and start_message.get("channels") == 1
                and start_message.get("encoding") == "float32le"
                and cleanup_level in _VALID_CLEANUP_LEVELS
            )
            if not valid_start:
                await websocket.send_json({
                    "type": "error",
                    "message": "The cloud session settings are invalid.",
                })
                return

            session_registered = True
            _set_cloud_session(
                session_id,
                client_id=client_id,
                app=app_name or None,
                status="recording",
                partial="",
                seconds=0.0,
            )
            update_state(status="recording")
            push_event({"type": "status", "value": "recording"})
            await websocket.send_json({"type": "session_started", "session_id": session_id})

            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    raise WebSocketDisconnect(message.get("code", 1000))

                payload = message.get("bytes")
                if payload is not None:
                    if not payload or len(payload) % 4:
                        raise WebAudioError("Audio chunks must contain float32 samples.")
                    if len(payload) > _CLOUD_MAX_CHUNK_BYTES:
                        raise WebAudioError("An audio chunk exceeded the 256 KB limit.")
                    total_bytes += len(payload)
                    if total_bytes > _CLOUD_MAX_AUDIO_BYTES:
                        raise WebAudioError("Live audio must be 60 seconds or shorter.")
                    chunk = np.frombuffer(payload, dtype="<f4").copy()
                    if not np.isfinite(chunk).all():
                        raise WebAudioError("Audio chunks must contain finite samples.")
                    audio_chunks.append(np.clip(chunk, -1.0, 1.0))
                    seconds = total_bytes / 4 / _WEB_AUDIO_SAMPLE_RATE
                    _set_cloud_session(session_id, seconds=round(seconds, 1))

                    now = time.monotonic()
                    should_emit_partial = (
                        seconds >= _CLOUD_MIN_PARTIAL_SECONDS
                        and now - last_partial_at >= _CLOUD_PARTIAL_INTERVAL_SECONDS
                    )
                    if should_emit_partial:
                        last_partial_at = now
                        partial_audio = np.concatenate(audio_chunks)
                        partial_text = await asyncio.to_thread(
                            _transcribe_web_audio, partial_audio
                        )
                        if partial_text and partial_text != last_partial_text:
                            last_partial_text = partial_text
                            _set_cloud_session(session_id, partial=partial_text)
                            event = {
                                "type": "partial_transcript",
                                "session_id": session_id,
                                "client_id": client_id,
                                "text": partial_text,
                            }
                            await websocket.send_json(event)
                            push_event(event)
                    continue

                text_payload = message.get("text")
                if text_payload is None:
                    continue
                try:
                    control = json.loads(text_payload)
                except json.JSONDecodeError as exc:
                    raise WebAudioError("Cloud control message is invalid JSON.") from exc
                if control.get("type") != "end_of_audio":
                    raise WebAudioError("Unsupported cloud control message.")
                break

            if not audio_chunks:
                raise WebAudioError("No microphone audio was received.")

            update_state(status="processing")
            _set_cloud_session(session_id, status="processing")
            push_event({"type": "status", "value": "processing"})
            audio = np.concatenate(audio_chunks)
            raw_text = await asyncio.to_thread(_transcribe_web_audio, audio)
            clean_text = ""
            history_id = None
            if raw_text:
                clean_text = await asyncio.to_thread(
                    _clean_cloud_transcript,
                    raw_text,
                    cleanup_level,
                    app_name or None,
                )
                history_id = _history.save_entry(
                    raw=raw_text,
                    clean=clean_text,
                    level=cleanup_level,
                    app=app_name or None,
                    client_id=client_id,
                    status="final",
                )
                entry = _history.get_entry(history_id)
                if entry:
                    push_event({"type": "new_entry", "entry": entry})

            final_event = {
                "type": "final_transcript",
                "session_id": session_id,
                "raw": raw_text,
                "text": clean_text,
                "history_id": history_id,
                "words": len(clean_text.split()),
            }
            await websocket.send_json(final_event)
            push_event(final_event)
        except WebSocketDisconnect:
            print(f"[api] Cloud client disconnected: session={session_id}")
        except WebAudioError as exc:
            await websocket.send_json({"type": "error", "message": str(exc)})
            push_event({
                "type": "session_error",
                "session_id": session_id,
                "message": str(exc),
            })
        except Exception as exc:
            print(f"[api] Cloud transcription failed for session {session_id}: {exc}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": "Cloud transcription failed.",
                })
            except Exception:
                pass
            push_event({
                "type": "session_error",
                "session_id": session_id,
                "message": "Cloud transcription failed.",
            })
        finally:
            _cloud_work_slots.release()
            if session_registered:
                _remove_cloud_session(session_id)
                remaining = _cloud_sessions_snapshot()
                status = "recording" if remaining else "idle"
                update_state(status=status)
                push_event({
                    "type": "live_session",
                    "session": {"session_id": session_id, "status": "closed"},
                })
                push_event({"type": "status", "value": status})

    # ── SSE live events ─────────────────────────────────────────── #

    @app.get("/events")
    async def sse_events(request: Request):
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        with _sub_lock:
            _subscribers.append(q)

        async def generate():
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(q.get(), timeout=25)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
            finally:
                with _sub_lock:
                    if q in _subscribers:
                        _subscribers.remove(q)

        return StreamingResponse(generate(), media_type="text/event-stream")

    # ── Onboarding ──────────────────────────────────────────────── #

    @app.get("/onboarding")
    async def onboarding_page():
        html_path = _UI_DIR / "onboarding.html"
        if html_path.exists():
            return FileResponse(str(html_path))
        return JSONResponse({"error": "Onboarding UI not found"}, status_code=404)

    @app.post("/onboarding/complete")
    async def onboarding_complete():
        get_platform_services().permissions.mark_onboarded()
        return {"ok": True}

    @app.post("/onboarding/start")
    async def onboarding_start():
        get_platform_services().permissions.begin_onboarding()
        return {"ok": True}

    @app.post("/onboarding/reconnect")
    async def onboarding_reconnect():
        _onboarding_reconnect_event.set()
        return {"ok": True}

    @app.get("/permissions")
    async def get_permissions():
        return JSONResponse(
            get_platform_services().permissions.get_all_permissions(),
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/permissions/request/{perm_type}")
    async def request_permission(perm_type: str):
        permissions = get_platform_services().permissions
        ok = permissions.request_permission(perm_type)
        response = {"ok": ok}
        if getattr(permissions, "last_permission_request_opened_settings", False):
            response["opened_settings"] = True
        return response

    @app.post("/permissions/open/{perm_type}")
    async def open_permission(perm_type: str):
        ok = get_platform_services().permissions.open_system_settings(perm_type)
        return {"ok": ok}


def _persist_cleanup_level(level: str):
    """Write cleanup_level back to the project-local config.toml."""
    _persist_config_updates({"cleanup_level": level})


def _persist_runtime_settings(settings: dict[str, Any]) -> None:
    """Persist settings whose values can change from the dashboard."""
    _persist_config_updates(settings)


def _persist_config_updates(settings: dict[str, Any]) -> None:
    """Update config.toml atomically without discarding unrelated settings."""
    if managed_state_enabled():
        try:
            managed = get_managed_state()
            for key, value in settings.items():
                managed.set_setting(key, value)
        except Exception as exc:
            print(f"[api] Could not persist managed settings: {exc}")
        return
    temporary_path: str | None = None
    try:
        import toml
        cfg = toml.load(str(CONFIG_PATH)) if CONFIG_PATH.exists() else {}
        if "cleanup_level" in settings:
            cfg.setdefault("llm", {})["cleanup_level"] = settings["cleanup_level"]
        if "asr_engine" in settings:
            cfg.setdefault("asr", {})["engine"] = settings["asr_engine"]
        if "ollama_model" in settings:
            cfg.setdefault("llm", {})["ollama_model"] = settings["ollama_model"]
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=CONFIG_PATH.parent,
            prefix=f".{CONFIG_PATH.name}.", suffix=".tmp", delete=False,
        ) as temporary:
            toml.dump(cfg, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = temporary.name
        os.replace(temporary_path, CONFIG_PATH)
    except Exception as e:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
        print(f"[api] Could not persist settings: {e}")


def _persist_hotkey(key: str):
    """Write the selected hotkey back to the project-local config.toml."""
    if managed_state_enabled():
        try:
            get_managed_state().set_setting("hotkey", key)
        except Exception as exc:
            print(f"[api] Could not persist managed hotkey: {exc}")
        return
    try:
        import toml
        cfg = toml.load(str(CONFIG_PATH)) if CONFIG_PATH.exists() else {}
        cfg.setdefault("hotkey", {})["key"] = key
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            toml.dump(cfg, f)
    except Exception as e:
        print(f"[api] Could not persist hotkey: {e}")


# ── Server launcher ────────────────────────────────────────────────── #

def start_server(
    host: str = "127.0.0.1",
    port: int = 57327,
    *,
    history_enabled: bool = True,
):
    """Start uvicorn in a background daemon thread. Non-blocking."""
    global _history_enabled
    if not _FASTAPI_OK:
        print("[api] FastAPI/uvicorn not installed — dashboard unavailable.")
        return
    _history_enabled = history_enabled

    def _run():
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False,
        )

    t = threading.Thread(target=_run, daemon=True, name="api-server")
    t.start()
    print(f"[api] Dashboard starting at http://{host}:{port}")
    return t
