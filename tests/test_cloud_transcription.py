import inspect
import sqlite3

import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from voiceflow.app import main as app_main
from voiceflow.core.audio import AudioRecorder
from voiceflow.core import history
from voiceflow.core.cloud_client import CloudTranscriptionError, websocket_url
from voiceflow.web import api_server


def _start_message() -> dict:
    return {
        "type": "start",
        "client_id": "desktop-test",
        "sample_rate": 16_000,
        "channels": 1,
        "encoding": "float32le",
        "cleanup_level": "light",
        "context": {"app": "TextEdit", "is_ai_chat": False},
    }


def test_cloud_websocket_streams_partial_and_saves_final_on_server(monkeypatch):
    saved = []
    monkeypatch.setenv("HUSH_TEAM_TOKEN", "test-team-token")
    monkeypatch.setattr(api_server, "_history_enabled", True)
    monkeypatch.setattr(api_server._history, "init_db", lambda: None)
    monkeypatch.setattr(
        api_server,
        "_transcribe_web_audio",
        lambda audio: "hello from the cloud" if audio.size else "",
    )
    monkeypatch.setattr(
        api_server,
        "_clean_cloud_transcript",
        lambda raw, level, app: "Hello from the cloud.",
    )
    monkeypatch.setattr(
        api_server._history,
        "save_entry",
        lambda **entry: saved.append(entry) or 23,
    )
    monkeypatch.setattr(
        api_server._history,
        "get_entry",
        lambda entry_id: {"id": entry_id, "clean": "Hello from the cloud."},
    )

    with TestClient(api_server.app) as client:
        with client.websocket_connect(
            "/ws/transcribe",
            headers={"Authorization": "Bearer test-team-token"},
        ) as websocket:
            websocket.send_json(_start_message())
            assert websocket.receive_json()["type"] == "session_started"
            websocket.send_bytes(np.ones(16_000, dtype="<f4").tobytes())
            partial = websocket.receive_json()
            assert partial == {
                "type": "partial_transcript",
                "session_id": partial["session_id"],
                "client_id": "desktop-test",
                "text": "hello from the cloud",
            }
            websocket.send_json({"type": "end_of_audio"})
            final = websocket.receive_json()

    assert final["type"] == "final_transcript"
    assert final["raw"] == "hello from the cloud"
    assert final["text"] == "Hello from the cloud."
    assert final["history_id"] == 23
    assert saved == [{
        "raw": "hello from the cloud",
        "clean": "Hello from the cloud.",
        "level": "light",
        "app": "TextEdit",
        "client_id": "desktop-test",
        "status": "final",
    }]


def test_cloud_websocket_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("HUSH_TEAM_TOKEN", "correct-token")
    monkeypatch.setattr(api_server, "_history_enabled", True)

    with TestClient(api_server.app) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                "/ws/transcribe",
                headers={"Authorization": "Bearer wrong-token"},
            ):
                pass

    assert error.value.code == 1008


def test_cloud_dashboard_mutations_require_team_token(monkeypatch):
    monkeypatch.setenv("HUSH_TEAM_TOKEN", "test-team-token")
    headers = {"Host": "test", "Origin": "http://test"}

    with TestClient(api_server.app) as client:
        missing = client.post("/settings", json={}, headers=headers)
        query_string = client.post(
            "/settings?token=test-team-token",
            json={},
            headers=headers,
        )
        accepted = client.post(
            "/settings",
            json={},
            headers={**headers, "Authorization": "Bearer test-team-token"},
        )

    assert missing.status_code == 401
    assert query_string.status_code == 401
    assert accepted.status_code == 200


def test_cloud_dashboard_reads_require_team_token_but_health_is_public(monkeypatch):
    monkeypatch.setenv("HUSH_TEAM_TOKEN", "test-team-token")
    monkeypatch.setattr(api_server, "_history_enabled", False)
    headers = {"Host": "test"}

    with TestClient(api_server.app) as client:
        health = client.get("/health", headers=headers)
        missing_history = client.get("/history", headers=headers)
        missing_status = client.get("/status", headers=headers)
        accepted_history = client.get(
            "/history",
            headers={**headers, "Authorization": "Bearer test-team-token"},
        )
        accepted_status = client.get(
            "/status",
            headers={**headers, "Authorization": "Bearer test-team-token"},
        )

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert missing_history.status_code == 401
    assert missing_status.status_code == 401
    assert accepted_history.status_code == 200
    assert accepted_status.status_code == 200


def test_cloud_mode_requires_team_token(monkeypatch):
    monkeypatch.setenv("HUSH_SERVER_MODE", "cloud")
    monkeypatch.delenv("HUSH_TEAM_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="HUSH_TEAM_TOKEN is required"):
        api_server._validate_cloud_configuration()


def test_local_dashboard_mode_does_not_initialize_or_return_history(monkeypatch):
    monkeypatch.setattr(api_server, "_history_enabled", False)
    monkeypatch.setattr(
        api_server._history,
        "init_db",
        lambda: pytest.fail("the desktop dashboard must not initialize history"),
    )

    with TestClient(api_server.app) as client:
        response = client.get("/history", headers={"Host": "test"})

    assert response.status_code == 200
    assert response.json() == []


def test_cloud_history_uses_wal_and_stores_client_status(tmp_path, monkeypatch):
    database = tmp_path / "cloud-history.db"
    monkeypatch.setattr(history, "DB_PATH", database)

    history.init_db()
    entry_id = history.save_entry(
        raw="raw words",
        clean="Clean words.",
        level="light",
        app="TextEdit",
        client_id="desktop-test",
        status="final",
    )

    entry = history.get_entry(entry_id)
    with sqlite3.connect(database) as connection:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]

    assert journal_mode == "wal"
    assert entry["client_id"] == "desktop-test"
    assert entry["status"] == "final"


def test_audio_recorder_can_stream_without_retaining_microphone_audio(monkeypatch):
    delivered = []
    recorder = AudioRecorder(sample_rate=16_000, channels=1)
    recorder._recording = True
    recorder._retain_audio = False
    recorder._on_chunk = delivered.append
    chunk = np.ones((1_024, 1), dtype=np.float32)

    recorder._callback(chunk, 1_024, None, None)

    assert len(delivered) == 1
    assert np.array_equal(delivered[0], chunk)
    assert recorder._chunks == []


def test_desktop_orchestrator_has_no_local_transcription_pipeline():
    source = inspect.getsource(app_main)

    assert "core.transcriber" not in source
    assert "clean_transcript" not in source
    assert "_history.save_entry" not in source
    assert "retain_audio=False" in source


def test_websocket_url_never_contains_the_team_token():
    assert websocket_url("http://203.0.113.10:57327") == (
        "ws://203.0.113.10:57327/ws/transcribe"
    )
    with pytest.raises(CloudTranscriptionError):
        websocket_url("203.0.113.10:57327")


def test_cloud_cleanup_uses_runtime_ollama_url(monkeypatch):
    captured = {}
    monkeypatch.setenv("HUSH_OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setattr(api_server, "load_snippets", lambda: [])
    monkeypatch.setattr(
        api_server,
        "load_config",
        lambda: {"llm": {"ollama_base_url": "http://localhost:11434"}},
    )

    def fake_clean_transcript(text, **kwargs):
        captured.update(kwargs)
        return text

    monkeypatch.setattr(api_server, "clean_transcript", fake_clean_transcript)

    assert api_server._clean_cloud_transcript("hello", "light", None) == "hello"
    assert captured["ollama_base_url"] == "http://ollama:11434"
