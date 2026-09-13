import asyncio

import httpx

from voiceflow.web import api_server


def test_hotkey_setting_updates_runtime_state_and_persists(monkeypatch):
    persisted = []
    applied = []

    monkeypatch.setitem(api_server._state, "hotkey", "ctrl_l")
    monkeypatch.setattr(api_server, "_persist_hotkey", persisted.append)
    monkeypatch.setattr(
        api_server,
        "_hotkey_updater",
        lambda key: applied.append(key) or True,
    )

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/settings", json={"hotkey": "ctrl_r"})

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert response.json()["state"]["hotkey"] == "ctrl_r"
    assert applied == ["ctrl_r"]
    assert persisted == ["ctrl_r"]


def test_hotkey_setting_rejects_empty_value(monkeypatch):
    monkeypatch.setattr(api_server, "_hotkey_updater", None)

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/settings", json={"hotkey": "   "})

    response = asyncio.run(exercise())

    assert response.status_code == 400
    assert response.json()["error"] == "A valid hotkey is required."
