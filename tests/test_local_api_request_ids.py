import asyncio

import httpx
import pytest

from voiceflow.core.jobs import SQLiteJobRepository
from voiceflow.web import api_server


def test_local_api_preserves_explicit_empty_request_id_for_validation(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    monkeypatch.setattr(api_server, "_jobs", SQLiteJobRepository(tmp_path / "jobs.db"))

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            empty = await client.post("/jobs", json={"request_id": ""})
            generated = await client.post("/jobs", json={})
            malformed = await client.post(
                "/snippets",
                content=b"{",
                headers={"content-type": "application/json"},
            )
        return empty, generated, malformed

    empty, generated, malformed = asyncio.run(exercise())

    assert empty.status_code == 400
    assert generated.status_code == 200
    assert generated.json()["request_id"]
    assert malformed.status_code == 400
