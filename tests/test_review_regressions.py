"""Regression coverage for the Milestone 5 review failure paths."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from voiceflow.cloud import managed_state
from voiceflow.web import api_server
from voiceflow.app import main as desktop


def test_connector_socket_bounds_tcp_and_tls(monkeypatch):
    connect = Mock(return_value=object())
    monkeypatch.setattr(managed_state.socket, 'create_connection', connect)
    managed_state._BoundedConnectorSocket().create_connection(('10.0.0.1', 3307))
    connect.assert_called_once_with(('10.0.0.1', 3307), timeout=2)


def test_early_audio_is_forwarded_only_while_key_held(monkeypatch):
    session = Mock()
    monkeypatch.setattr(desktop, '_recording_starting', True)
    monkeypatch.setattr(desktop, '_hotkey_pressed', False)
    monkeypatch.setattr(desktop, '_cloud_session', None)
    monkeypatch.setattr(desktop, '_macos_key_is_pressed', lambda _: True)
    desktop._forward_recording_audio(b'first', session, 59)
    session.send_audio.assert_called_once_with(b'first')
    monkeypatch.setattr(desktop, '_macos_key_is_pressed', lambda _: False)
    desktop._forward_recording_audio(b'late', session, 59)
    assert session.send_audio.call_count == 1
    monkeypatch.setattr(desktop, '_cloud_session', Mock())
    monkeypatch.setattr(desktop, '_macos_key_is_pressed', lambda _: True)
    desktop._forward_recording_audio(b'other', session, 59)
    assert session.send_audio.call_count == 1


def test_cleanup_preserves_transcript_when_settings_fail(monkeypatch):
    monkeypatch.setattr(api_server, 'managed_state_enabled', lambda: True)
    monkeypatch.setattr(api_server, 'load_snippets', lambda: [])
    monkeypatch.setattr(api_server, 'is_exact_shortcut', lambda *_: False)
    monkeypatch.setattr(api_server, 'get_managed_state', Mock(side_effect=managed_state.ManagedStateError('offline')))
    monkeypatch.setattr(api_server, 'clean_transcript', lambda text, **kwargs: text)
    assert api_server._clean_cloud_transcript('saved speech', 'none', None) == 'saved speech'


def test_settings_cache_expires_and_invalidates(monkeypatch):
    for key, value in {'GOOGLE_CLOUD_PROJECT':'test', 'HUSH_CLOUD_SQL_INSTANCE':'test:r:db', 'HUSH_UPLOAD_BUCKET':'test'}.items():
        monkeypatch.setenv(key, value)
    state = managed_state.ManagedState()
    engine = Mock()
    state._engine = engine
    engine.connect.return_value.__enter__ = Mock(return_value=Mock(execute=Mock(return_value=Mock(fetchall=Mock(return_value=[SimpleNamespace(key='hotkey', value='ctrl')])))))
    engine.connect.return_value.__exit__ = Mock(return_value=False)
    engine.begin.return_value.__enter__ = Mock(return_value=Mock())
    engine.begin.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(managed_state.time, 'monotonic', lambda: 10)
    assert state.get_settings() == {'hotkey':'ctrl'}
    assert state.get_settings() == {'hotkey':'ctrl'}
    assert engine.connect.call_count == 1
    state.set_setting('hotkey', 'alt')
    state.get_settings()
    assert engine.connect.call_count == 2
    monkeypatch.setattr(managed_state.time, 'monotonic', lambda: 13)
    state.get_settings()
    assert engine.connect.call_count == 3


@pytest.mark.parametrize('counts', [
    {'200': 1, 'transport_error': 1}, {'200': 1, '500': 1},
    {'200': 1, '503': 1}, {'429': 4},
])
def test_load_rejects_degraded_or_unsuccessful_runs(counts):
    from scripts.milestone5_load import validate_results
    with pytest.raises(SystemExit):
        validate_results(counts)


def test_load_accepts_success_with_expected_busy_responses():
    from scripts.milestone5_load import validate_results
    validate_results({'200': 3, '429': 4})


def test_verifier_rejects_untrusted_host_before_loading_credentials(monkeypatch):
    from scripts import milestone5_verify
    credentials = Mock(side_effect=AssertionError('must not fetch credentials'))
    monkeypatch.setattr(milestone5_verify.subprocess, 'check_output', credentials)
    monkeypatch.setattr('sys.argv', ['verify', '--host', 'attacker.example', '--sample', 'unused.wav'])
    with pytest.raises(SystemExit) as error:
        milestone5_verify.main()
    assert error.value.code == 2
    credentials.assert_not_called()
