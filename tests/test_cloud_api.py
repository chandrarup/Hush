import pytest
import asyncio
import httpx

from voiceflow.core.jobs import SQLiteJobRepository
from voiceflow.web.cloud_api import create_cloud_app


def test_backend_api_factory_does_not_require_desktop_services(tmp_path):
    fastapi = pytest.importorskip("fastapi")
    app = create_cloud_app(SQLiteJobRepository(tmp_path / "jobs.db"))
    routes = {route.path for route in app.routes if hasattr(route, "path")}

    assert "/health/live" in routes
    assert "/health/ready" in routes
    assert "/jobs" in routes
    assert "/jobs/{request_id}" in routes
    assert fastapi is not None


def test_backend_api_accepts_and_reads_a_durable_job(tmp_path):
    app = create_cloud_app(SQLiteJobRepository(tmp_path / "jobs.db"))

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/jobs",
                json={"request_id": "request-http", "user_id": "user-1"},
            )
            loaded = await client.get("/jobs/request-http")
        return created, loaded

    created, loaded = asyncio.run(exercise())

    assert created.status_code == 200
    assert created.json()["status"] == "accepted"
    assert loaded.status_code == 200
    assert loaded.json()["request_id"] == "request-http"
