"""
api_server.py - Local FastAPI server for the VoiceFlow dashboard.

Runs on http://localhost:57327 (loopback only).
Serves:
  GET  /              → dashboard HTML
  GET  /history       → transcription entries (JSON)
  GET  /stats         → word count, wpm, days
  GET  /status        → app state (recording/idle, cleanup level, etc.)
  POST /settings      → update cleanup level, hotkey display name
  GET  /snippets      → saved spoken shortcuts
  POST /snippets      → create or update a spoken shortcut
  DELETE /snippets/{id} → remove a spoken shortcut
  DELETE /history     → clear all history
  DELETE /history/{id}→ delete one entry
  GET  /events        → Server-Sent Events stream for live updates
"""

import asyncio
import json
import pathlib
import threading
import uuid
from typing import Any

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
from ..core.jobs import SQLiteJobRepository
from ..config.loader import update_config_value
from ..config.snippets import (
    SNIPPETS_PATH,
    add_snippet,
    load_snippets,
    remove_snippet,
)
from ..platform.factory import get_platform_services

# ── Shared state (updated by main.py) ─────────────────────────────── #
_state: dict[str, Any] = {
    "status":        "idle",       # idle | recording | processing
    "cleanup_level": "light",      # none | light | medium | high
    "hotkey":        "cmd_r",
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
_jobs = SQLiteJobRepository()


def push_event(event: dict):
    """
    Push a live event to all connected dashboard clients.
    Thread-safe - called from the pipeline thread.
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
    app = FastAPI(title="VoiceFlow", docs_url=None, redoc_url=None)

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

    @app.post("/jobs")
    async def create_job(request: Request):
        """Accept a durable job request for local or future cloud workers."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"error": "Malformed JSON."}, status_code=400)
        if not isinstance(data, dict):
            return JSONResponse({"error": "A JSON object is required."}, status_code=400)
        raw_request_id = data.get("request_id")
        request_id = uuid.uuid4().hex if raw_request_id is None else str(raw_request_id).strip()
        if not request_id:
            return JSONResponse({"error": "request_id cannot be empty."}, status_code=400)
        job = _jobs.create(request_id, user_id=data.get("user_id"))
        return _job_payload(job)

    @app.get("/jobs/{request_id}")
    async def get_job(request_id: str):
        job = _jobs.get(request_id)
        if job is None:
            return JSONResponse({"error": "Job not found."}, status_code=404)
        return _job_payload(job)

    @app.post("/settings")
    async def post_settings(request: Request):
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"error": "Malformed JSON."}, status_code=400)
        if not isinstance(data, dict):
            return JSONResponse({"error": "A JSON object is required."}, status_code=400)
        allowed = {"cleanup_level", "hotkey", "asr_engine", "ollama_model"}
        for k, v in data.items():
            if k in allowed:
                _state[k] = v
        # Persist cleanup_level to config if changed
        if "cleanup_level" in data:
            _persist_cleanup_level(data["cleanup_level"])
        return {"ok": True, "state": dict(_state)}

    @app.get("/snippets")
    async def get_snippets():
        return {
            "path": str(SNIPPETS_PATH),
            "snippets": [
                {**snippet, "index": index}
                for index, snippet in enumerate(load_snippets())
            ],
        }

    @app.post("/snippets")
    async def post_snippet(request: Request):
        try:
            data = await request.json()
        except json.JSONDecodeError:
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

    @app.delete("/snippets/{snippet_index}")
    async def delete_snippet(snippet_index: int):
        try:
            return {"ok": True, "snippets": remove_snippet(snippet_index)}
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
    """Write cleanup_level back to ~/.voiceflow/config.toml."""
    try:
        update_config_value("llm", "cleanup_level", level)
    except Exception as e:
        print(f"[api] Could not persist cleanup_level: {e}")


def _job_payload(job) -> dict[str, Any]:
    """Serialize a job without exposing implementation-specific objects."""
    return {
        "request_id": job.request_id,
        "status": job.status.value,
        "user_id": job.user_id,
        "raw_text": job.raw_text,
        "clean_text": job.clean_text,
        "entry_id": job.entry_id,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


# ── Server launcher ────────────────────────────────────────────────── #

def start_server(host: str = "127.0.0.1", port: int = 57327):
    """Start uvicorn in a background daemon thread. Non-blocking."""
    if not _FASTAPI_OK:
        print("[api] FastAPI/uvicorn not installed - dashboard unavailable.")
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
