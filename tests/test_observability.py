import json

from fastapi.testclient import TestClient

from voiceflow.web import api_server


def _request_records(capsys):
    return [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.startswith('{"timestamp":')
    ]


def test_controlled_5xx_logs_once_without_secrets(monkeypatch, capsys):
    monkeypatch.setenv("HUSH_ENABLE_DEMO_ERROR", "1")
    monkeypatch.setenv("HUSH_RELEASE_SHA", "abc123")
    monkeypatch.setattr(api_server, "_team_token", lambda: "private-demo-token")
    with TestClient(api_server.app, base_url="http://localhost") as client:
        response = client.get(
            "/internal/demo-error",
            headers={"Authorization": "Bearer private-demo-token"},
        )
    records = _request_records(capsys)
    assert response.status_code == 503
    assert len(records) == 1
    assert records[0]["event"] == "http_request"
    assert records[0]["status_code"] == 503
    assert records[0]["severity"] == "ERROR"
    assert records[0]["route"] == "/internal/demo-error"
    assert records[0]["release_sha"] == "abc123"
    assert records[0]["request_id"] == response.headers["X-Request-ID"]
    assert "private-demo-token" not in json.dumps(records)


def test_demo_error_disabled_and_requires_token(monkeypatch, capsys):
    monkeypatch.setattr(api_server, "_team_token", lambda: "private-demo-token")
    monkeypatch.delenv("HUSH_ENABLE_DEMO_ERROR", raising=False)
    with TestClient(api_server.app, base_url="http://localhost") as client:
        assert client.get(
            "/internal/demo-error",
            headers={"Authorization": "Bearer private-demo-token"},
        ).status_code == 404
        monkeypatch.setenv("HUSH_ENABLE_DEMO_ERROR", "1")
        assert client.get("/internal/demo-error").status_code == 401
        assert client.get("/health").status_code == 200
    records = _request_records(capsys)
    assert [item["status_code"] for item in records] == [404, 401, 200]


def test_unhandled_exception_logs_500(monkeypatch, capsys):
    with TestClient(api_server.app, raise_server_exceptions=False) as client:
        monkeypatch.setattr(api_server, "managed_state_enabled", lambda: True)
        monkeypatch.setattr(api_server, "get_managed_state", lambda: None)
        response = client.get("/ready")
        monkeypatch.setattr(api_server, "managed_state_enabled", lambda: False)
    records = _request_records(capsys)
    assert response.status_code == 500
    assert len(records) == 1
    assert records[0]["status_code"] == 500
    assert records[0]["error_class"]


def test_readiness_exposes_release_sha_for_external_rollout_check(monkeypatch):
    monkeypatch.setenv("HUSH_RELEASE_SHA", "a" * 40)
    monkeypatch.setattr(api_server, "managed_state_enabled", lambda: False)
    with TestClient(api_server.app, base_url="http://localhost") as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["release_sha"] == "a" * 40
