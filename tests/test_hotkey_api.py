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


def test_cleanup_setting_updates_live_runtime_and_persists(monkeypatch):
    applied = []
    persisted = []
    monkeypatch.setitem(api_server._state, "cleanup_level", "light")
    monkeypatch.setattr(api_server, "_runtime_config_updater", applied.append)
    monkeypatch.setattr(api_server, "_persist_cleanup_level", persisted.append)

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/settings", json={"cleanup_level": "high"})

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert response.json()["state"]["cleanup_level"] == "high"
    assert applied == [{"cleanup_level": "high"}]
    assert persisted == ["high"]


def test_model_and_asr_settings_are_persisted(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[asr]\nengine = 'auto'\n[llm]\nollama_model = 'llama3.2:3b'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api_server, "CONFIG_PATH", config_path)

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/settings",
                json={"asr_engine": "whisper", "ollama_model": "phi3:mini"},
            )

    response = asyncio.run(exercise())

    assert response.status_code == 200
    saved = config_path.read_text(encoding="utf-8")
    assert "engine = \"whisper\"" in saved
    assert "ollama_model = \"phi3:mini\"" in saved
