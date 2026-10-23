from fastapi.testclient import TestClient
import threading
from voiceflow.web import api_server


def test_ip_host_probes_do_not_open_application_host_boundary(monkeypatch):
    monkeypatch.setattr(api_server, "managed_state_enabled", lambda: False)
    with TestClient(api_server.app) as client:
        assert client.get('/health', headers={'Host': '10.30.1.5'}).status_code == 200
        assert client.get('/ready', headers={'Host': '10.30.1.5'}).status_code == 200
        assert client.get('/history', headers={'Host': '10.30.1.5'}).status_code == 403
        assert client.post('/health', headers={'Host': '10.30.1.5'}).status_code == 403


def test_database_failure_withdraws_readiness_without_killing_liveness(monkeypatch):
    class Store:
        team_token = 'test-only'
        database = True

        def get_settings(self):
            return {}

        def check_ready(self):
            return {'database': self.database, 'storage': True, 'secrets': True}

        def close(self):
            pass

    store = Store()
    monkeypatch.setattr(api_server, 'managed_state_enabled', lambda: True)
    monkeypatch.setattr(api_server, 'get_managed_state', lambda: store)
    monkeypatch.setattr(api_server, 'initialize_managed_state', lambda: store)
    monkeypatch.setattr(api_server._history, 'init_db', lambda: None)
    with TestClient(api_server.app) as client:
        assert client.get('/ready').status_code == 200
        store.database = False
        assert client.get('/health').status_code == 200
        assert client.get('/ready').status_code == 503
        store.database = True
        assert client.get('/ready').status_code == 200


def test_model_and_draining_are_readiness_conditions(monkeypatch, tmp_path):
    marker = tmp_path / 'hush-draining'
    original_path = api_server.pathlib.Path
    monkeypatch.setattr(api_server.pathlib, 'Path', lambda value: marker if value == '/tmp/hush-draining' else original_path(value))
    with TestClient(api_server.app) as client:
        marker.touch()
        assert client.get('/ready').status_code == 503
        assert client.get('/health').status_code == 200


def test_overload_rejects_without_waiting_for_inference(monkeypatch):
    monkeypatch.setattr(api_server, '_cloud_work_slots', threading.BoundedSemaphore(0))
    with TestClient(api_server.app, base_url='http://test') as client:
        response = client.post('/transcribe', headers={'Origin': 'http://test'})
    assert response.status_code == 429
    assert response.headers['retry-after'] == '2'


def test_failed_upload_returns_its_work_slot(monkeypatch):
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(api_server, '_cloud_work_slots', slots)
    with TestClient(api_server.app, base_url='http://test') as client:
        response = client.post('/transcribe', content=b'invalid', headers={'Origin': 'http://test'})
    assert response.status_code == 400
    assert slots.acquire(blocking=False)


def test_whisper_thread_count_matches_cloud_cpu(monkeypatch):
    from voiceflow.core import transcriber

    calls = []
    monkeypatch.setattr(transcriber, '_FASTER_WHISPER_AVAILABLE', True)
    monkeypatch.setattr(transcriber, '_best_ctranslate_device', lambda: ('cpu', 'int8'))
    monkeypatch.setattr(transcriber, 'WhisperModel', lambda *args, **kwargs: calls.append(kwargs))
    monkeypatch.setenv('HUSH_WHISPER_CPU_THREADS', '1')
    transcriber.WhisperTranscriber('tiny.en')
    assert calls[0]['cpu_threads'] == 1
