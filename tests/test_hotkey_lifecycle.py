from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import sys

from voiceflow.app import main as app_main


class _DeferredThread:
    def __init__(self, *, target, args=(), **_kwargs):
        self.target = target
        self.args = args
        self.started = False

    def start(self):
        self.started = True


def _install_state_spies(monkeypatch):
    tray_states = []
    events = []
    tray = SimpleNamespace(set_state=tray_states.append)
    monkeypatch.setattr(
        app_main,
        "_platform",
        SimpleNamespace(name="macOS", tray=SimpleNamespace(get_tray=lambda: tray)),
    )
    monkeypatch.setattr(app_main._api, "push_event", events.append)
    return tray_states, events


def test_release_immediately_moves_native_hud_to_processing(monkeypatch):
    tray_states, events = _install_state_spies(monkeypatch)
    recorder = SimpleNamespace(stop=lambda: None)
    session = object()
    threads = []

    def make_thread(**kwargs):
        thread = _DeferredThread(**kwargs)
        threads.append(thread)
        return thread

    monkeypatch.setattr(app_main, "_hotkey_pressed", True)
    monkeypatch.setattr(app_main, "_cloud_session", session)
    monkeypatch.setattr(app_main, "_recorder", recorder)
    monkeypatch.setattr(app_main.threading, "Thread", make_thread)

    assert app_main._stop_recording() is True

    assert app_main._hotkey_pressed is False
    assert tray_states == ["processing"]
    assert [(e['type'], e['value']) for e in events] == [('status', 'processing')]
    assert len(threads) == 1
    assert threads[0].target is app_main._finish_cloud_session
    assert threads[0].args == (session,)
    assert threads[0].started is True


def test_stop_failure_aborts_session_and_clears_stuck_hud(monkeypatch):
    tray_states, events = _install_state_spies(monkeypatch)
    aborted = []

    def fail_to_stop():
        raise RuntimeError("input stream would not close")

    recorder = SimpleNamespace(stop=fail_to_stop)
    session = SimpleNamespace(abort=lambda: aborted.append(True))
    monkeypatch.setattr(app_main, "_hotkey_pressed", True)
    monkeypatch.setattr(app_main, "_cloud_session", session)
    monkeypatch.setattr(app_main, "_recorder", recorder)

    assert app_main._stop_recording() is True

    assert aborted == [True]
    assert app_main._cloud_session is None
    assert tray_states == ["processing", "idle"]
    assert events[-1]['type'] == 'status' and events[-1]['value'] == 'idle'
    assert events[-2]["type"] == "session_error"


def test_native_watchdog_recovers_a_missed_release(monkeypatch):
    recovered = []
    readings = iter((False, False))
    monkeypatch.setattr(app_main, "_hotkey_pressed", True)
    monkeypatch.setattr(app_main, "_recording_generation", 12)
    monkeypatch.setattr(app_main.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(app_main, "_macos_key_is_pressed", lambda _vk: next(readings))

    def stop_recording(*, expected_generation):
        recovered.append(expected_generation)
        app_main._hotkey_pressed = False

    monkeypatch.setattr(app_main, "_stop_recording", stop_recording)

    app_main._watch_for_hotkey_release(59, generation=12)

    assert recovered == [12]


def _install_press_spies(monkeypatch):
    if not app_main._PYNPUT:
        pytest.skip('Requires an available pynput keyboard backend')
    states, events = _install_state_spies(monkeypatch)
    app_main._platform.context = SimpleNamespace(get_active_context=lambda: {})
    session = Mock()
    session.start.return_value = session
    recorder = Mock(is_recording=False)
    monkeypatch.setattr(app_main, '_hotkey_pressed', False)
    monkeypatch.setattr(app_main, '_recording_starting', False)
    monkeypatch.setattr(app_main, '_cloud_session', None)
    monkeypatch.setattr(app_main, '_hotkey_target', app_main._kb.Key.ctrl_l)
    monkeypatch.setattr(app_main, '_recorder', recorder)
    monkeypatch.setattr(app_main, '_create_cloud_session', Mock(return_value=session))
    monkeypatch.setattr(app_main, '_macos_key_is_pressed', lambda _: True)
    monkeypatch.setattr(app_main, '_start_release_watchdog', lambda *_: None)
    return session, recorder, states, events


def test_sidebar_snapshot_and_live_events_match_native_hud(monkeypatch):
    states, events = _install_state_spies(monkeypatch)
    monkeypatch.setitem(app_main._api._state, 'status', 'idle')
    for state in ('recording', 'processing', 'idle'):
        app_main._set_activity_state(state)
        assert app_main._api._state['status'] == state
        assert states[-1] == state
        assert events[-1]['type'] == 'status' and events[-1]['value'] == state
        assert events[-1]['updated_at'] == app_main._api._state['status_updated_at']


def test_right_control_does_not_activate_left_control(monkeypatch):
    session, recorder, states, _ = _install_press_spies(monkeypatch)
    app_main._on_press(app_main._kb.Key.ctrl_r)
    session.start.assert_not_called()
    recorder.start.assert_not_called()
    assert states == []


def test_generated_press_and_unheld_press_never_open_microphone(monkeypatch):
    session, recorder, states, _ = _install_press_spies(monkeypatch)
    app_main._on_press(app_main._kb.Key.ctrl_l, injected=True)
    monkeypatch.setattr(app_main, '_macos_key_is_pressed', lambda _: False)
    app_main._on_press(app_main._kb.Key.ctrl_l)
    session.start.assert_not_called()
    recorder.start.assert_not_called()
    assert states == []


def test_release_during_connection_does_not_start_late_recording(monkeypatch):
    session, recorder, states, _ = _install_press_spies(monkeypatch)
    readings = iter((True, False))
    monkeypatch.setattr(app_main, '_macos_key_is_pressed', lambda _: next(readings))
    app_main._on_press(app_main._kb.Key.ctrl_l)
    recorder.start.assert_not_called()
    session.abort.assert_called_once()
    assert app_main._recording_starting is False
    assert app_main._cloud_session is None
    assert states == []


def test_autorepeat_starts_only_one_session_and_injected_release_is_ignored(monkeypatch):
    session, recorder, states, _ = _install_press_spies(monkeypatch)
    session.start.side_effect = lambda: (app_main._on_press(app_main._kb.Key.ctrl_l) or session)
    app_main._on_press(app_main._kb.Key.ctrl_l)
    app_main._on_press(app_main._kb.Key.ctrl_l)
    app_main._on_release(app_main._kb.Key.ctrl_l, injected=True)
    session.start.assert_called_once()
    recorder.start.assert_called_once()
    assert states == ['recording']
    assert app_main._hotkey_pressed is True


def test_audio_forwarding_stops_at_physical_release(monkeypatch):
    session, _, _, _ = _install_press_spies(monkeypatch)
    monkeypatch.setattr(app_main, '_cloud_session', session)
    monkeypatch.setattr(app_main, '_hotkey_pressed', True)
    app_main._forward_recording_audio(b'held audio', session, 59)
    monkeypatch.setattr(app_main, '_macos_key_is_pressed', lambda _: False)
    app_main._forward_recording_audio(b'after release', session, 59)
    session.send_audio.assert_called_once_with(b'held audio')


def test_release_while_microphone_opens_aborts_without_recording(monkeypatch):
    session, recorder, states, _ = _install_press_spies(monkeypatch)
    readings = iter((True, True, False))
    monkeypatch.setattr(app_main, '_macos_key_is_pressed', lambda _: next(readings))
    app_main._on_press(app_main._kb.Key.ctrl_l)
    recorder.stop.assert_called_once()
    session.abort.assert_called_once()
    assert app_main._hotkey_pressed is False
    assert app_main._cloud_session is None
    assert states == []


def test_release_event_cannot_stop_a_physically_held_key(monkeypatch):
    _, recorder, _, _ = _install_press_spies(monkeypatch)
    monkeypatch.setattr(app_main, '_hotkey_pressed', True)
    app_main._on_release(app_main._kb.Key.ctrl_l)
    recorder.stop.assert_not_called()
    assert app_main._hotkey_pressed is True


def test_macos_physical_key_check_fails_closed_when_quartz_unavailable(monkeypatch):
    _install_state_spies(monkeypatch)
    monkeypatch.setitem(sys.modules, 'Quartz', None)
    assert app_main._macos_key_is_pressed(59) is False
