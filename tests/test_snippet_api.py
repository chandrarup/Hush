import asyncio

import httpx

from voiceflow.web import api_server
from voiceflow.config import snippets as snippet_store


def test_snippet_api_round_trip(tmp_path, monkeypatch):
    snippets_path = tmp_path / "snippets.toml"
    monkeypatch.setattr(api_server, "SNIPPETS_PATH", snippets_path)
    monkeypatch.setattr(snippet_store, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(snippet_store, "SNIPPETS_PATH", snippets_path)

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/snippets",
                json={
                    "name": "Greeting",
                    "shortcut": "hello",
                    "text": "Hello from VoiceFlow.",
                },
            )
            listed = await client.get("/snippets")
            updated = await client.put(
                "/snippets/0",
                json={
                    "name": "Updated greeting",
                    "shortcut": "good morning",
                    "text": "Good morning.",
                },
            )
            listed_after_update = await client.get("/snippets")
            stale_delete = await client.delete(
                "/snippets/0",
                params={"version": listed.json()["version"]},
            )
            removed = await client.delete(
                "/snippets/0",
                params={"version": listed_after_update.json()["version"]},
            )
            malformed = await client.post("/snippets", content=b"\xff")
        return created, listed, updated, stale_delete, removed, malformed

    created, listed, updated, stale_delete, removed, malformed = asyncio.run(exercise())

    assert created.status_code == 200
    assert listed.json()["snippets"][0]["shortcut"] == "hello"
    assert updated.status_code == 200
    assert stale_delete.status_code == 409
    assert removed.status_code == 200
    assert malformed.status_code == 400
