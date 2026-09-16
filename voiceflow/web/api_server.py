"""
api_server.py — Local FastAPI server for the Hush dashboard.

Runs on http://localhost:57327 (loopback only).
Serves:
  GET  /              → dashboard HTML
  GET  /history       → transcription entries (JSON)
  GET  /stats         → word count, wpm, days
  GET  /status        → app state (recording/idle, cleanup level, etc.)
  POST /settings      → update cleanup level, hotkey display name
  DELETE /history     → clear all history
  DELETE /history/{id}→ delete one entry
  GET  /events        → Server-Sent Events stream for live updates
"""

import asyncio
import json
import os
import pathlib
import tempfile
import threading
from typing import Any, Callable

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    _FASTAPI_OK = True
except ImportError:
    _FASTAPI_OK = False

from ..core import history as _history
from ..config.snippets import (
    SNIPPETS_PATH,
    add_snippet,
    get_snippets_snapshot,
    remove_snippet,
    SnippetConflictError,
    update_snippet,
)
from ..config.paths import CONFIG_PATH
from ..platform.factory import get_platform_services

# ── Shared state (updated by main.py) ─────────────────────────────── #
_state: dict[str, Any] = {
    "status":        "idle",       # idle | recording | processing
    "cleanup_level": "light",      # none | light | medium | high
    "hotkey":        "ctrl_l",
    "asr_engine":    "auto",
    "ollama_model":  "llama3.2:3b",
}

def update_state(**kwargs):
    """Thread-safe state update called from main.py."""
    _state.update(kwargs)


# ── SSE subscriber list ────────────────────────────────────────────── #
_subscribers: list[asyncio.Queue] = []
_sub_lock = threading.Lock()
_event_loop: asyncio.AbstractEventLoop | None = None
_hotkey_updater: Callable[[str], bool] | None = None
_runtime_config_updater: Callable[[dict[str, Any]], None] | None = None

_VALID_CLEANUP_LEVELS = {"none", "light", "medium", "high"}
_VALID_ASR_ENGINES = {"auto", "parakeet", "whisper"}


def register_hotkey_updater(updater: Callable[[str], bool]) -> None:
    """Register the application callback used to apply a new hotkey immediately."""
    global _hotkey_updater
    _hotkey_updater = updater


def register_runtime_config_updater(updater: Callable[[dict[str, Any]], None]) -> None:
    """Register the application callback for settings changed at runtime."""
    global _runtime_config_updater
    _runtime_config_updater = updater


def push_event(event: dict):
    """
    Push a live event to all connected dashboard clients.
    Thread-safe — called from the pipeline thread.
    """
    global _event_loop
    if _event_loop is None:
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve dashboard static files
    _UI_DIR = pathlib.Path(__file__).parent / "ui"

    @app.on_event("startup")
    async def _startup():
        global _event_loop
        _event_loop = asyncio.get_running_loop()
        _history.init_db()
        print("[api] Server ready at http://localhost:57327")

    # ── Dashboard HTML ──────────────────────────────────────────── #

    @app.get("/")
    async def index():
        html_path = _UI_DIR / "index.html"
        if html_path.exists():
            return FileResponse(str(html_path))
        return JSONResponse({"error": "Dashboard UI not found"}, status_code=404)

    @app.get("/ui/{path:path}")
    async def static_files(path: str):
        file_path = _UI_DIR / path
        if file_path.exists():
            return FileResponse(str(file_path))
        return JSONResponse({"error": "Not found"}, status_code=404)

    # ── REST endpoints ──────────────────────────────────────────── #

    @app.get("/history")
    async def get_history(limit: int = 200, offset: int = 0):
        return _history.get_entries(limit=limit, offset=offset)

    @app.get("/stats")
    async def get_stats():
        return _history.get_stats()

    @app.get("/status")
    async def get_status():
        return dict(_state)

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
        snippets, version = get_snippets_snapshot()
        return {
            "path": str(SNIPPETS_PATH),
            "snippets": [
                {**snippet, "index": index, "version": version}
                for index, snippet in enumerate(snippets)
            ],
            "version": version,
        }

    @app.post("/snippets")
    async def post_snippet(request: Request):
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
        _history.clear_all()
        return {"ok": True}

    @app.delete("/history/{entry_id}")
    async def delete_entry(entry_id: int):
        _history.delete_entry(entry_id)
        return {"ok": True}

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

    @app.get("/permissions")
    async def get_permissions():
        return get_platform_services().permissions.get_all_permissions()

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

def start_server(host: str = "127.0.0.1", port: int = 57327):
    """Start uvicorn in a background daemon thread. Non-blocking."""
    if not _FASTAPI_OK:
        print("[api] FastAPI/uvicorn not installed — dashboard unavailable.")
        return

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
