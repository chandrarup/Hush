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

import sys
import os
import time
import threading
import numpy as np

from ..config import load_config, load_snippets, load_vocab
from ..config.snippets import expand_snippets, is_exact_shortcut
from ..core.audio import AudioRecorder
from ..core.vad import trim_silence, audio_duration
from ..core.cleaner import clean_transcript, set_docker_llm_available
from ..core import history as _history
from ..platform.factory import get_platform_services
from ..runtime import configure_runtime_environment
from ..web import api_server as _api

_platform = get_platform_services()

try:
    from pynput import keyboard as _kb
    _PYNPUT = True
except ImportError:
    _PYNPUT = False

MIN_AUDIO_SECONDS = 0.3

# ── Globals ───────────────────────────────────────────────────────── #
_config: dict           = {}
_vocab:  list[str]      = []
_transcriber            = None
_recorder: AudioRecorder | None = None
_hotkey_target          = None
_hotkey_pressed         = False
_captured_context: dict = {}
_pipeline_lock          = threading.Lock()
_listener               = None   # pynput Listener — kept alive in thread


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
#  Pipeline                                                             #
# ──────────────────────────────────────────────────────────────────── #

def _run_pipeline(audio: np.ndarray, app_context: dict):
    if not _pipeline_lock.acquire(blocking=False):
        print("[main] Pipeline busy — skipping this recording.")
        return

    tray = _platform.tray.get_tray()
    try:
        tray.set_state("processing")

        # 1. VAD trim
        audio = trim_silence(audio)
        if audio_duration(audio) < MIN_AUDIO_SECONDS:
            print("[main] Audio too short — discarding.")
            return

        # 2. Transcribe
        if _transcriber is None:
            print("[main] Transcriber not ready.")
            return
        raw_text = _transcriber.transcribe(audio, vocab=_vocab)
        if not raw_text or not raw_text.strip():
            print("[main] Empty transcript — discarding.")
            return

        print(f"\n{'─'*55}")
        print(f"  RAW  : {raw_text}")

        # 3. LLM cleanup (context-aware)
        llm_cfg    = _config.get("llm", {})
        inject_cfg = _config.get("injection", {})
        active_app = app_context.get("app")
        level      = llm_cfg.get("cleanup_level", "light")

        snippets = load_snippets()
        if is_exact_shortcut(raw_text, snippets):
            clean_text = expand_snippets(raw_text, snippets)
            print("  SNIPPET: expanded spoken shortcut")
        else:
            clean_text = clean_transcript(
                raw_text,
                level            = level,
                docker_llm_url   = llm_cfg.get("docker_llm_url",   "http://localhost:12434/engines/llama.cpp/v1"),
                docker_llm_model = llm_cfg.get("docker_llm_model", ""),
                ollama_model     = llm_cfg.get("ollama_model",     "llama3.2:3b"),
                ollama_base_url  = llm_cfg.get("ollama_base_url",  "http://localhost:11434"),
                temperature      = llm_cfg.get("temperature", 0.1),
                max_tokens       = llm_cfg.get("max_tokens", 500),
                app_context      = active_app,
            )

        print(f"  CLEAN: {clean_text}")
        print(f"{'─'*55}\n")

        # 3b. Save to history + push live event
        entry_id = _history.save_entry(
            raw=raw_text, clean=clean_text,
            level=level, app=active_app,
        )
        _api.push_event({
            "type": "new_entry",
            "entry": {
                "id":    entry_id,
                "ts":    __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                "raw":   raw_text,
                "clean": clean_text,
                "level": level,
                "app":   active_app,
                "words": len(clean_text.split()),
            },
        })

        # 4. Inject text
        _platform.text.inject_text(
            clean_text,
            preferred_method=inject_cfg.get("method", "auto"),
        )

        # 5. Notification
        ui_cfg = _config.get("ui", {})
        _platform.notifications.show_result(
            raw_text=raw_text,
            clean_text=clean_text,
            duration_seconds=ui_cfg.get("notification_duration", 3),
            enabled=ui_cfg.get("show_notification", True),
        )

    except Exception as e:
        print(f"[main] Pipeline error: {e}")
        import traceback; traceback.print_exc()
    finally:
        _pipeline_lock.release()
        tray.set_state("idle")


# ──────────────────────────────────────────────────────────────────── #
#  Hotkey callbacks                                                     #
# ──────────────────────────────────────────────────────────────────── #

def _on_press(key):
    global _hotkey_pressed, _captured_context
    if not _keys_match(key, _hotkey_target) or _hotkey_pressed:
        return

    _hotkey_pressed    = True
    _captured_context  = _platform.context.get_active_context()
    app_name = _captured_context.get("app", "unknown")
    is_ai    = _captured_context.get("is_ai_chat", False)
    print(f"[main] ● RECORDING  app='{app_name}'" + (" [AI chat]" if is_ai else ""))

    _platform.tray.get_tray().set_state("recording")
    _api.push_event({"type": "status", "value": "recording"})
    if _recorder:
        try:
            _recorder.start()
        except RuntimeError as e:
            # No audio device available (e.g. headphones disconnected mid-session)
            print(f"[main] ⚠ Audio device error: {e} — try plugging in a mic and pressing again.")
            _api.push_event({"type": "status", "value": "idle"})
            _platform.tray.get_tray().set_state("idle")
            _hotkey_pressed = False  # let next press retry


def _on_release(key):
    global _hotkey_pressed
    if not _keys_match(key, _hotkey_target) or not _hotkey_pressed:
        return

    _hotkey_pressed = False
    print("[main] ■ STOPPED — running pipeline…")
    _api.push_event({"type": "status", "value": "processing"})

    if not _recorder:
        return

    audio   = _recorder.stop()
    context = dict(_captured_context)

    threading.Thread(
        target=_run_pipeline, args=(audio, context),
        daemon=True, name="pipeline"
    ).start()


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
        _listener = lst
        trusted = getattr(lst, 'IS_TRUSTED', None)
        if trusted is False:
            print("\n" + "!" * 66)
            print("[main] ⚠  IS_TRUSTED = False — GLOBAL KEYBOARD ACCESS NOT GRANTED")
            print("[main]    The operating system is blocking global key events.")
            print("[main]    Enable Accessibility for Hush, then restart if macOS asks.")
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
#  Docker LLM check                                                     #
# ──────────────────────────────────────────────────────────────────── #

def _check_docker_llm(url: str):
    import requests
    try:
        r = requests.get(url.rstrip("/") + "/models", timeout=3)
        if r.ok:
            names = [m.get("id","?") for m in r.json().get("data", [])[:3]]
            print(f"[main] ✓ Docker LLM at {url}  models={names}")
            set_docker_llm_available(True)
        else:
            print(f"[main] ✗ Docker LLM status {r.status_code} — will use Ollama.")
            set_docker_llm_available(False)
    except Exception as e:
        print(f"[main] ✗ Docker LLM unreachable ({e}) — will use Ollama.")
        set_docker_llm_available(False)


# ──────────────────────────────────────────────────────────────────── #
#  Entry point                                                          #
# ──────────────────────────────────────────────────────────────────── #

def main():
    global _config, _vocab, _transcriber, _recorder, _hotkey_target

    configure_runtime_environment()
    # Import model providers after their packaged cache location is configured.
    from ..core.transcriber import create_transcriber

    print("=" * 60)
    print("  Hush — Local Push-to-Talk Dictation")
    print("=" * 60)

    # ── Config ───────────────────────────────────────────────────────
    _config = load_config()
    _vocab  = load_vocab()

    # ── Local dashboard and onboarding ───────────────────────────────
    # Start this before model initialization so first-run permissions do not
    # wait for a potentially large model download.
    ui_cfg = _config.get("ui", {})
    dashboard_port = ui_cfg.get("dashboard_port", 57327)
    asr_cfg = _config.get("asr", {})
    first_launch = _platform.permissions.is_first_launch()
    resuming_onboarding = first_launch and _platform.permissions.is_onboarding_in_progress()
    if resuming_onboarding:
        _api.begin_onboarding_reconnect_window()
    if first_launch:
        _platform.permissions.begin_onboarding()

    _api.start_server(port=dashboard_port)
    _api.update_state(
        cleanup_level=_config.get("llm", {}).get("cleanup_level", "light"),
        hotkey=_config.get("hotkey", {}).get("key", "ctrl_l"),
        asr_engine=asr_cfg.get("engine", "auto"),
        ollama_model=_config.get("llm", {}).get("ollama_model", "llama3.2:3b"),
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

    # ── Docker LLM check (background, non-blocking) ───────────────────
    llm_cfg    = _config.get("llm", {})
    docker_url = llm_cfg.get("docker_llm_url", "http://localhost:12434/engines/llama.cpp/v1")
    threading.Thread(target=_check_docker_llm, args=(docker_url,), daemon=True).start()

    # ── ASR model (load once) ─────────────────────────────────────────
    engine  = asr_cfg.get("engine", "auto")
    model   = asr_cfg.get("model",  "")
    print(f"\n[main] Loading ASR  engine={engine}  model={model or 'default'}")
    print("[main] First run downloads the model (~1-2 GB), cached after that.\n")

    try:
        _transcriber = create_transcriber(
            engine=engine,
            model=model,
            language=asr_cfg.get("language", "en"),
            compute_type_gpu=asr_cfg.get("compute_type_gpu", "float16"),
            compute_type_cpu=asr_cfg.get("compute_type_cpu", "int8"),
        )
    except Exception as e:
        print(f"[main] FATAL: Cannot load ASR model: {e}")
        sys.exit(1)

    # ── Audio recorder ────────────────────────────────────────────────
    try:
        _recorder = AudioRecorder(sample_rate=16000, channels=1)
    except Exception as e:
        print(f"[main] FATAL: Audio recorder error: {e}")
        sys.exit(1)

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
    print(f"[main] Engine : {type(_transcriber).__name__}")
    print(f"[main] LLM    : {docker_url}")
    print("\n[main] ✓ Ready — hold hotkey to record, release to transcribe.")
    print("[main] Right-click the menu bar icon to Quit.")
    print("[main] (If hotkey does nothing, check keyboard/input permission for the launcher)\n")

    # ── Tray owns the main thread where required by the desktop backend ──
    tray = _platform.tray.get_tray()
    tray.setup(on_quit=lambda: os._exit(0), dashboard_port=dashboard_port)

    print(f"\n[main] Dashboard : http://localhost:{dashboard_port}")
    print("[main] ✓ Ready — hold hotkey to record, release to transcribe.")
    print("[main] Right-click the menu bar icon to open Dashboard or Quit.\n")

    # This BLOCKS until the user clicks Quit in the tray menu
    tray.run_blocking()


if __name__ == "__main__":
    main()
