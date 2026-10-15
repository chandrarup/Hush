from types import SimpleNamespace

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
    assert events == [{"type": "status", "value": "processing"}]
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
    assert events[-1] == {"type": "status", "value": "idle"}
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
