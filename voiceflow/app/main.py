"""
Hush application orchestration.

The application layer is platform-neutral. Operating-system behavior is supplied
by ``PlatformServices`` and selected once by the platform factory.

Threading architecture:
  Main thread  → pystray tray icon (AppKit REQUIRES this)
  Thread B     → pynput keyboard listener
  Thread C     → audio capture (sounddevice callback)
  Thread D     → pipeline (VAD + ASR + LLM + inject) — one at a time

"""

import os
import time
import threading

from ..config import load_config, persist_cloud_client_id
from ..core.audio import AudioRecorder
from ..core.cloud_client import (
    CloudTranscriptionError,
    CloudTranscriptionSession,
    ensure_client_id,
)
from ..platform.factory import get_platform_services
from ..runtime import configure_runtime_environment
from ..web import api_server as _api

_platform = get_platform_services()

try:
    from pynput import keyboard as _kb
    _PYNPUT = True
except ImportError:
    _PYNPUT = False

# ── Globals ───────────────────────────────────────────────────────── #
_config: dict           = {}
_recorder: AudioRecorder | None = None
_cloud_session: CloudTranscriptionSession | None = None
_hotkey_target          = None
_hotkey_pressed         = False
_captured_context: dict = {}
_session_lock           = threading.Lock()
_listener               = None   # pynput Listener — kept alive in thread
_recording_generation   = 0      # Distinguishes consecutive watchdog threads.


# ──────────────────────────────────────────────────────────────────── #
#  Permission helper                                                     #
# ──────────────────────────────────────────────────────────────────── #

def _print_permission_guide():
    _platform.permissions.print_permission_guide()


def _initial_browser_url(dashboard_port: int, first_launch: bool) -> str:
    """Choose the page shown when the Hush app is opened."""
    path = "/onboarding" if first_launch else "/"
    return f"http://localhost:{dashboard_port}{path}"


def _open_browser_after_server_start(dashboard_port: int, first_launch: bool) -> None:
    """Open setup once, then make every Hush launch visible in the browser."""
    import webbrowser

    url = _initial_browser_url(dashboard_port, first_launch)

    def _open_browser() -> None:
        time.sleep(1.5)  # Let uvicorn begin serving before opening the page.
        webbrowser.open(url, new=2)

    threading.Thread(target=_open_browser, daemon=True).start()


def _recover_resumed_onboarding(dashboard_port: int, timeout_seconds: float = 5) -> threading.Thread:
    """Open setup only when the browser page from a TCC restart did not reconnect."""
    def _recover() -> None:
        if _api.wait_for_onboarding_reconnect(timeout_seconds):
            print("[main] Existing onboarding page reconnected.")
            return
        print("[main] Onboarding page did not reconnect; opening setup again.")
        _open_browser_after_server_start(dashboard_port, first_launch=True)

    thread = threading.Thread(target=_recover, daemon=True)
    thread.start()
    return thread


# ──────────────────────────────────────────────────────────────────── #
#  Hotkey resolution                                                    #
# ──────────────────────────────────────────────────────────────────── #

def _resolve_hotkey(key_name: str):
    if not _PYNPUT:
        return None
    special = {
        "ctrl_r":  _kb.Key.ctrl_r,  "ctrl_l":  _kb.Key.ctrl_l,
        "ctrl":    _kb.Key.ctrl,    "alt_r":   _kb.Key.alt_r,
        "alt_l":   _kb.Key.alt_l,   "alt":     _kb.Key.alt,
        "shift_r": _kb.Key.shift_r, "shift_l": _kb.Key.shift_l,
        "cmd":     _kb.Key.cmd,     "cmd_r":   _kb.Key.cmd_r,
        "cmd_l":   _kb.Key.cmd_l,
        "f1":  _kb.Key.f1,  "f2":  _kb.Key.f2,  "f3":  _kb.Key.f3,
        "f4":  _kb.Key.f4,  "f5":  _kb.Key.f5,  "f6":  _kb.Key.f6,
        "f7":  _kb.Key.f7,  "f8":  _kb.Key.f8,  "f9":  _kb.Key.f9,
        "f10": _kb.Key.f10, "f11": _kb.Key.f11, "f12": _kb.Key.f12,
    }
    k = key_name.lower().strip()
    if k in special:
        return special[k]
    if len(k) == 1:
        return k
    print(f"[main] Unknown hotkey '{key_name}' — defaulting to Left Ctrl.")
    return _kb.Key.ctrl_l


def _keys_match(key, target) -> bool:
    if target is None:
        return False
    if key == target:
        return True
    if _PYNPUT:
        try:
            modifier_groups = (
                {_kb.Key.ctrl, _kb.Key.ctrl_l, _kb.Key.ctrl_r},
                {_kb.Key.alt, _kb.Key.alt_l, _kb.Key.alt_r},
                {_kb.Key.shift, _kb.Key.shift_l, _kb.Key.shift_r},
                {_kb.Key.cmd, _kb.Key.cmd_l, _kb.Key.cmd_r},
            )
            if any(key in group and target in group for group in modifier_groups):
                return True
        except Exception:
            pass
    try:
        if hasattr(key, "char") and isinstance(target, str):
            return key.char == target
    except Exception:
        pass
    return False


def _update_hotkey(key_name: str) -> bool:
    """Apply a dashboard hotkey change to the active listener."""
    global _hotkey_target
    target = _resolve_hotkey(key_name)
    if target is None:
        return False
    _hotkey_target = target
    _config.setdefault("hotkey", {})["key"] = key_name
    return True


def _apply_runtime_settings(settings: dict[str, str]) -> None:
    """Apply dashboard settings to the config consumed by future pipeline runs."""
    if "cleanup_level" in settings:
        _config.setdefault("llm", {})["cleanup_level"] = settings["cleanup_level"]
    if "ollama_model" in settings:
        _config.setdefault("llm", {})["ollama_model"] = settings["ollama_model"]
    if "asr_engine" in settings:
        # The active ASR model is constructed at startup. Persist this value and
        # expose it in state, but require a restart before rebuilding the model.
        _config.setdefault("asr", {})["engine"] = settings["asr_engine"]


# ──────────────────────────────────────────────────────────────────── #
#  Cloud transcription                                                   #
# ──────────────────────────────────────────────────────────────────── #

def _cloud_settings() -> dict:
    """Resolve cloud settings without placing the shared token in logs."""
    cloud = _config.setdefault("cloud", {})
    existing_client_id = str(cloud.get("client_id", "")).strip()
    client_id = ensure_client_id(cloud)
    if not existing_client_id:
        persist_cloud_client_id(client_id)
    return {
        "base_url": os.getenv("HUSH_CLOUD_URL", cloud.get("base_url", "")),
        "token": os.getenv("HUSH_TEAM_TOKEN", cloud.get("token", "")),
        "client_id": client_id,
        "connect_timeout": float(cloud.get("connect_timeout_seconds", 5)),
        "final_timeout": float(cloud.get("final_timeout_seconds", 90)),
    }


def _handle_partial(text: str) -> None:
    print(f"[main] PARTIAL: {text}")
    _api.push_event({"type": "partial_transcript", "text": text})


def _create_cloud_session(app_context: dict) -> CloudTranscriptionSession:
    settings = _cloud_settings()
    return CloudTranscriptionSession(
        base_url=settings["base_url"],
        token=settings["token"],
        client_id=settings["client_id"],
        app_context=app_context,
        cleanup_level=_config.get("llm", {}).get("cleanup_level", "light"),
        connect_timeout=settings["connect_timeout"],
        final_timeout=settings["final_timeout"],
        on_partial=_handle_partial,
    )


def _finish_cloud_session(session: CloudTranscriptionSession) -> None:
    """Wait for the VM result, inject it once, and never run local ASR or cleanup."""
    global _cloud_session
    tray = _platform.tray.get_tray()
    try:
        tray.set_state("processing")
        result = session.finish()
        raw_text = str(result.get("raw", "")).strip()
        clean_text = str(result.get("text", "")).strip()
        if not clean_text:
            print("[main] Cloud returned no speech to insert.")
            return

        print(f"[main] FINAL: {clean_text}")
        metrics = session.latency_metrics
        print(
            "[main] LATENCY "
            f"first_partial_ms={metrics['first_partial_ms']} "
            f"release_to_final_ms={metrics['release_to_final_ms']}"
        )
        inject_cfg = _config.get("injection", {})
        _platform.text.inject_text(
            clean_text,
            preferred_method=inject_cfg.get("method", "auto"),
        )
        ui_cfg = _config.get("ui", {})
        _platform.notifications.show_result(
            raw_text=raw_text,
            clean_text=clean_text,
            duration_seconds=ui_cfg.get("notification_duration", 3),
            enabled=ui_cfg.get("show_notification", True),
        )
    except CloudTranscriptionError as exc:
        print(f"[main] Cloud transcription error: {exc}")
        _api.push_event({"type": "session_error", "message": str(exc)})
    finally:
        with _session_lock:
            if _cloud_session is session:
                _cloud_session = None
        tray.set_state("idle")
        _api.push_event({"type": "status", "value": "idle"})


def _virtual_key_code(key) -> int | None:
    """Return pynput's native virtual-key code when the backend exposes one."""
    value = getattr(key, "value", key)
    virtual_key = getattr(value, "vk", None)
    return virtual_key if isinstance(virtual_key, int) else None


def _macos_key_is_pressed(virtual_key: int) -> bool | None:
    """Read physical key state independently of the event-tap release callback."""
    if _platform.name != "macOS":
        return None
    try:
        from Quartz import CGEventSourceKeyState, kCGEventSourceStateCombinedSessionState

        return bool(
            CGEventSourceKeyState(kCGEventSourceStateCombinedSessionState, virtual_key)
        )
    except Exception:
        return None


def _watch_for_hotkey_release(
    virtual_key: int,
    generation: int,
    poll_seconds: float = 0.1,
) -> None:
    """Recover when macOS drops a pynput key-release event.

    Two consecutive native "up" readings avoid treating a transient state read
    as a release. Normal releases still use ``_on_release`` immediately.
    """
    consecutive_up_reads = 0
    while True:
        time.sleep(poll_seconds)
        with _session_lock:
            if not _hotkey_pressed or generation != _recording_generation:
                return

        is_pressed = _macos_key_is_pressed(virtual_key)
        if is_pressed is None:
            return
        if is_pressed:
            consecutive_up_reads = 0
            continue

        consecutive_up_reads += 1
        if consecutive_up_reads >= 2:
            print("[main] Recovered a missed hotkey release from native key state.")
            _stop_recording(expected_generation=generation)
            return


def _start_release_watchdog(key, generation: int) -> None:
    """Start the macOS missed-release guard when a native key code is available."""
    virtual_key = _virtual_key_code(key)
    if virtual_key is None or _macos_key_is_pressed(virtual_key) is None:
        return
    threading.Thread(
        target=_watch_for_hotkey_release,
        args=(virtual_key, generation),
        daemon=True,
        name="hotkey-release-watchdog",
    ).start()


def _stop_recording(expected_generation: int | None = None) -> bool:
    """Atomically leave recording state and finalize or safely abort the session."""
    global _hotkey_pressed, _cloud_session

    with _session_lock:
        if not _hotkey_pressed:
            return False
        if expected_generation is not None and expected_generation != _recording_generation:
            return False
        _hotkey_pressed = False
        session = _cloud_session

    print("[main] STOPPED — waiting for the cloud result...")
    tray = _platform.tray.get_tray()
    # Move the native HUD out of Listening before any potentially slow I/O.
    tray.set_state("processing")
    _api.push_event({"type": "status", "value": "processing"})

    try:
        if not _recorder:
            raise RuntimeError("The microphone recorder is unavailable.")
        _recorder.stop()
    except Exception as exc:
        print(f"[main] Could not stop dictation cleanly: {exc}")
        if session is not None:
            try:
                session.abort()
            except Exception:
                pass
        with _session_lock:
            if _cloud_session is session:
                _cloud_session = None
        tray.set_state("idle")
        _api.push_event({"type": "session_error", "message": str(exc)})
        _api.push_event({"type": "status", "value": "idle"})
        return True

    if session is None:
        tray.set_state("idle")
        _api.push_event({"type": "status", "value": "idle"})
        return True

    threading.Thread(
        target=_finish_cloud_session,
        args=(session,),
        daemon=True,
        name="cloud-finalize",
    ).start()
    return True


# ──────────────────────────────────────────────────────────────────── #
#  Hotkey callbacks                                                     #
# ──────────────────────────────────────────────────────────────────── #

def _on_press(key):
    global _hotkey_pressed, _captured_context, _cloud_session, _recording_generation
    if not _keys_match(key, _hotkey_target) or _hotkey_pressed:
        return

    with _session_lock:
        if _cloud_session is not None:
            print("[main] Previous cloud transcription is still finishing.")
            return

    _captured_context  = _platform.context.get_active_context()
    app_name = _captured_context.get("app", "unknown")
    is_ai    = _captured_context.get("is_ai_chat", False)
    session = None
    try:
        session = _create_cloud_session(_captured_context).start()
        if not _recorder:
            session.abort()
            raise CloudTranscriptionError("The microphone recorder is unavailable.")
        _recorder.start(on_chunk=session.send_audio, retain_audio=False)
    except (CloudTranscriptionError, RuntimeError) as exc:
        if session is not None:
            try:
                session.abort()
            except Exception:
                pass
        if _recorder and _recorder.is_recording:
            try:
                _recorder.stop()
            except Exception:
                pass
        print(f"[main] Cannot start cloud dictation: {exc}")
        _api.push_event({"type": "session_error", "message": str(exc)})
        _api.push_event({"type": "status", "value": "idle"})
        _platform.tray.get_tray().set_state("idle")
        return

    with _session_lock:
        _cloud_session = session
        _hotkey_pressed = True
        _recording_generation += 1
        generation = _recording_generation
    print(f"[main] RECORDING TO CLOUD  app='{app_name}'" + (" [AI chat]" if is_ai else ""))
    _platform.tray.get_tray().set_state("recording")
    _api.push_event({"type": "status", "value": "recording"})
    _start_release_watchdog(key, generation)


def _on_release(key):
    if not _keys_match(key, _hotkey_target) or not _hotkey_pressed:
        return
    _stop_recording()


# ──────────────────────────────────────────────────────────────────── #
#  Keyboard listener — runs in its own thread                           #
# ──────────────────────────────────────────────────────────────────── #

def _start_listener():
    """
    Start pynput keyboard listener.

    Some desktop keyboard backends require their listener to be created from
    the process' main thread. Start the listener before handing the main loop
    to the tray implementation so each platform adapter can own its event loop:

    We create the Listener and call lst.start() while still on the main thread
    (before tray.run_blocking), then the keepalive loop runs in a daemon thread.
    """
    global _listener

    if not _PYNPUT:
        print("[main] FATAL: pynput not installed.")
        return None

    try:
        lst = _kb.Listener(
            on_press=_on_press,
            on_release=_on_release,
            suppress=False,
        )
        lst.start()   # called from main thread — CFRunLoop exists here
        lst.wait()    # Wait until pynput's listener thread has evaluated macOS trust.
        _listener = lst
        trusted = getattr(lst, 'IS_TRUSTED', None)
        if trusted is False:
            print("\n" + "!" * 66)
            print("[main] ⚠  IS_TRUSTED = False — GLOBAL KEYBOARD ACCESS NOT GRANTED")
            print("[main]    The operating system is blocking global key events.")
            print("[main]    Enable Input Monitoring for Hush, then restart if macOS asks.")
            print("!" * 66 + "\n")
        else:
            print(f"[main] ✓ Keyboard listener started. IS_TRUSTED={trusted}")
    except Exception as e:
        print(f"[main] Keyboard listener failed to start: {e}")
        _print_permission_guide()
        return None

    # Keepalive thread — just prevents the listener from being GC'd
    def _keepalive():
        while _listener and _listener.running:
            time.sleep(0.5)
        print("[main] Keyboard listener stopped.")

    t = threading.Thread(target=_keepalive, daemon=True, name="kb-keepalive")
    t.start()
    return t


# ──────────────────────────────────────────────────────────────────── #
#  Entry point                                                          #
# ──────────────────────────────────────────────────────────────────── #

def main():
    global _config, _recorder, _hotkey_target

    configure_runtime_environment()

    print("=" * 60)
    print("  Hush — Cloud Push-to-Talk Dictation")
    print("=" * 60)

    # ── Config ───────────────────────────────────────────────────────
    _config = load_config()
    cloud_settings = _cloud_settings()

    # ── Local dashboard and onboarding ───────────────────────────────
    # Start the local permissions/settings UI before registering the hotkey.
    ui_cfg = _config.get("ui", {})
    dashboard_port = ui_cfg.get("dashboard_port", 57327)
    first_launch = _platform.permissions.is_first_launch()
    resuming_onboarding = first_launch and _platform.permissions.is_onboarding_in_progress()
    if resuming_onboarding:
        _api.begin_onboarding_reconnect_window()
    if first_launch:
        _platform.permissions.begin_onboarding()

    _api.start_server(port=dashboard_port, history_enabled=False)
    _api.update_state(
        cleanup_level=_config.get("llm", {}).get("cleanup_level", "light"),
        hotkey=_config.get("hotkey", {}).get("key", "ctrl_l"),
        asr_engine="whisper",
        ollama_model=_config.get("llm", {}).get("ollama_model", "llama3.2:3b"),
        cloud_url=cloud_settings["base_url"],
        client_id=cloud_settings["client_id"],
    )

    if resuming_onboarding:
        _recover_resumed_onboarding(dashboard_port)
    else:
        _open_browser_after_server_start(dashboard_port, first_launch)
    if first_launch:
        if resuming_onboarding:
            print("[main] Resuming the existing onboarding page after a macOS restart.")
        else:
            print("[main] First launch — opening onboarding wizard in browser.")
    else:
        print("[main] Opening dashboard in browser.")

    # ── Permission check ─────────────────────────────────────────────
    _platform.permissions.check_accessibility_permission()

    # ── Audio recorder ────────────────────────────────────────────────
    try:
        _recorder = AudioRecorder(sample_rate=16000, channels=1)
    except Exception as e:
        print(f"[main] FATAL: Audio recorder error: {e}")
        raise SystemExit(1) from e

    # ── Hotkey ────────────────────────────────────────────────────────
    hk_cfg         = _config.get("hotkey", {})
    key_name       = hk_cfg.get("key", "ctrl_l")
    _hotkey_target = _resolve_hotkey(key_name)
    print(f"[main] Hotkey target resolved to: {repr(_hotkey_target)}")
    _api.register_hotkey_updater(_update_hotkey)
    _api.register_runtime_config_updater(_apply_runtime_settings)

    # ── Start keyboard listener in background thread ───────────────────
    kb_thread = _start_listener()

    print(f"\n[main] Hotkey : {key_name}")
    print(f"[main] Cloud  : {cloud_settings['base_url'] or 'not configured'}")
    print("[main] ASR, cleanup, snippets, and history run on the cloud server.")
    print("\n[main] Ready — hold hotkey to stream, release to insert the final text.")
    print("[main] Right-click the menu bar icon to Quit.")
    print("[main] (If hotkey does nothing, check keyboard/input permission for the launcher)\n")

    # ── Tray owns the main thread where required by the desktop backend ──
    tray = _platform.tray.get_tray()
    tray.setup(on_quit=lambda: os._exit(0), dashboard_port=dashboard_port)

    print(f"\n[main] Dashboard : http://localhost:{dashboard_port}")
    print("[main] Ready — hold hotkey to stream, release to insert the final text.")
    print("[main] Right-click the menu bar icon to open Dashboard or Quit.\n")

    # This BLOCKS until the user clicks Quit in the tray menu
    tray.run_blocking()


if __name__ == "__main__":
    main()
