import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx

from voiceflow.application.auth import Principal
from voiceflow.core.jobs import SQLiteJobRepository
from voiceflow.web.cloud_api import create_cloud_app


class FakeAuthenticator:
    def authenticate(self, headers):
        token = headers.get("authorization", "")
        if token.startswith("Bearer ") and token.removeprefix("Bearer "):
            return Principal(subject=token.removeprefix("Bearer "))
        return None


def test_backend_api_factory_does_not_require_desktop_services(tmp_path):
    fastapi = pytest.importorskip("fastapi")
    app = create_cloud_app(SQLiteJobRepository(tmp_path / "jobs.db"), FakeAuthenticator())
    routes = {route.path for route in app.routes if hasattr(route, "path")}

    assert "/health/live" in routes
    assert "/health/ready" in routes
    assert "/jobs" in routes
    assert "/jobs/{request_id}" in routes
    assert fastapi is not None


def test_backend_api_accepts_and_reads_a_durable_job(tmp_path):
    app = create_cloud_app(SQLiteJobRepository(tmp_path / "jobs.db"), FakeAuthenticator())

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/jobs",
                json={"request_id": "request-http", "user_id": "user-1"},
                headers={"Authorization": "Bearer owner-1"},
            )
            loaded = await client.get(
                "/jobs/request-http",
                headers={"Authorization": "Bearer owner-1"},
            )
        return created, loaded

    created, loaded = asyncio.run(exercise())

    assert created.status_code == 200
    assert created.json()["status"] == "accepted"
    assert created.json()["user_id"] == "owner-1"
    assert loaded.status_code == 200
    assert loaded.json()["request_id"] == "request-http"


def test_backend_api_requires_auth_and_scopes_jobs_to_principal(tmp_path):
    app = create_cloud_app(SQLiteJobRepository(tmp_path / "jobs.db"), FakeAuthenticator())

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unauthenticated = await client.post("/jobs", json={"request_id": "request-auth"})
            empty = await client.post(
                "/jobs",
                json={"request_id": ""},
                headers={"Authorization": "Bearer owner-1"},
            )
            created = await client.post(
                "/jobs",
                json={"request_id": "request-owner"},
                headers={"Authorization": "Bearer owner-1"},
            )
            wrong_owner = await client.get(
                "/jobs/request-owner",
                headers={"Authorization": "Bearer owner-2"},
            )
            duplicate_wrong_owner = await client.post(
                "/jobs",
                json={"request_id": "request-owner", "user_id": "owner-1"},
                headers={"Authorization": "Bearer owner-2"},
            )
        return unauthenticated, empty, created, wrong_owner, duplicate_wrong_owner

    unauthenticated, empty, created, wrong_owner, duplicate_wrong_owner = asyncio.run(exercise())

    assert unauthenticated.status_code == 401
    assert empty.status_code == 400
    assert created.status_code == 200
    assert wrong_owner.status_code == 404
    assert duplicate_wrong_owner.status_code == 404


def test_concurrent_job_submissions_with_same_request_id_do_not_cross_owners(tmp_path):
    repository = SQLiteJobRepository(tmp_path / "jobs.db")
    app = create_cloud_app(repository, FakeAuthenticator())
    start = Barrier(2)

    def submit(owner):
        async def exercise():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                start.wait(timeout=5)
                return await client.post(
                    "/jobs",
                    json={"request_id": "request-concurrent"},
                    headers={"Authorization": f"Bearer {owner}"},
                )

        return asyncio.run(exercise())

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(submit, ("owner-1", "owner-2")))

    assert sorted(response.status_code for response in responses) == [200, 404]
    accepted = next(response for response in responses if response.status_code == 200)
    hidden = next(response for response in responses if response.status_code == 404)
    assert accepted.json()["user_id"] in {"owner-1", "owner-2"}
    assert hidden.json() == {"error": "Job not found."}
    assert repository.get("request-concurrent").user_id == accepted.json()["user_id"]
