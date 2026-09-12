"""Backend-only FastAPI application factory.

Unlike the local dashboard server, this module has no desktop, tray, keyboard,
microphone, or operating-system permission imports. A deployment supplies a
job repository adapter and can later add authentication and queue adapters.
"""

import uuid
from typing import Any

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
except ImportError:  # pragma: no cover - handled by deployment dependency checks
    FastAPI = None

from ..application.ports import JobRepository


def create_cloud_app(jobs: JobRepository):
    """Create a stateless backend app around an injected job repository."""
    if FastAPI is None:
        raise RuntimeError("FastAPI is required to run the backend API.")

    app = FastAPI(title="VoiceFlow Backend", docs_url=None, redoc_url=None)

    @app.get("/health/live")
    async def live_health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready_health() -> dict[str, str]:
        return {"status": "ready"}

    @app.post("/jobs")
    async def create_job(request: Request):
        data = await request.json()
        request_id = str(data.get("request_id") or uuid.uuid4().hex).strip()
        if not request_id:
            return JSONResponse({"error": "request_id cannot be empty."}, status_code=400)
        job = jobs.create(request_id, user_id=data.get("user_id"))
        return _job_payload(job)

    @app.get("/jobs/{request_id}")
    async def get_job(request_id: str):
        job = jobs.get(request_id)
        if job is None:
            return JSONResponse({"error": "Job not found."}, status_code=404)
        return _job_payload(job)

    return app


def _job_payload(job) -> dict[str, Any]:
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
