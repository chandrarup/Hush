"""
tray.py — System tray icon with state management.

macOS CRITICAL: pystray on macOS (AppKit) MUST run on the main thread.
Architecture fix: TrayIcon.run_blocking() is called from main thread.
State changes from any background thread are safe via icon.update().

States:
  idle       — gray circle
  recording  — red circle
  processing — animated amber cycle
"""

import sys
import threading
import time

_IS_MACOS = sys.platform == "darwin"

try:
    from PIL import Image, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False
    print("[tray] WARNING: Pillow not installed — tray icon disabled.")

try:
    import pystray
    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False
    print("[tray] WARNING: pystray not installed — tray icon disabled.")

ICON_SIZE      = 64
CIRCLE_PADDING = 8
ANIM_INTERVAL  = 0.25

STATE_COLORS = {
    "idle":       "#888888",
    "recording":  "#E53935",
    "processing": ["#FF6F00", "#FFB300", "#FF8F00", "#FFA000"],
}


def _make_image(color: str) -> "Image.Image":
    img  = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    box  = [CIRCLE_PADDING, CIRCLE_PADDING,
            ICON_SIZE - CIRCLE_PADDING, ICON_SIZE - CIRCLE_PADDING]
    draw.ellipse(box, fill=color)
    return img


class TrayIcon:
    """
    System tray icon.

    Usage in main.py:
        tray = get_tray()
        tray.setup(on_quit=my_quit_fn)       # call before run_blocking
        # start all background threads here
        tray.run_blocking()                  # BLOCKS — call from main thread
    """

    def __init__(self):
        self._state      = "idle"
        self._icon       = None
        self._lock       = threading.Lock()
        self._anim_thread  = None
        self._anim_stop    = threading.Event()
        self._on_quit_cb   = None
        self._enabled      = _PIL_AVAILABLE and _PYSTRAY_AVAILABLE

    # ── Public API (thread-safe) ─────────────────────────────────── #

    def setup(self, on_quit=None, on_settings=None, dashboard_port: int = 57327):
        """Configure callbacks before calling run_blocking()."""
        self._on_quit_cb     = on_quit
        self._on_settings_cb = on_settings
        self._dashboard_port = dashboard_port

    def run_blocking(self):
        """
        Create and run the tray icon. BLOCKS until icon.stop() is called.
        Must be called from the MAIN THREAD on macOS.
        """
        if not self._enabled:
            print("[tray] Tray disabled — running headlessly.")
            # Keep main thread alive without tray
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            return

        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard",  self._dashboard_action, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings (config)", self._settings_action),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit VoiceFlow",  self._quit_action),
        )

        self._icon = pystray.Icon(
            name="VoiceFlow",
            icon=_make_image(STATE_COLORS["idle"]),
            title="VoiceFlow — Idle",
            menu=menu,
        )

        print("[tray] Starting tray icon on main thread.")
        # run() blocks here on macOS main thread — this is correct
        self._icon.run()

    def set_state(self, state: str):
        """Change tray icon state. Safe to call from any thread."""
        if not self._enabled:
            return

        with self._lock:
            if self._state == state:
                return
            self._state = state

        print(f"[tray] State → {state}")
        self._stop_animation()

        if state == "processing":
            self._start_animation()
        else:
            color = STATE_COLORS.get(state, "#888888")
            self._update_icon(_make_image(color), state)

    def stop(self):
        """Stop the tray icon (safe to call from any thread)."""
        self._stop_animation()
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass

    # ── Private ──────────────────────────────────────────────────── #

    def _update_icon(self, img, state: str):
        if self._icon is None:
            return
        titles = {
            "idle":       "VoiceFlow — Idle",
            "recording":  "VoiceFlow — Recording…",
            "processing": "VoiceFlow — Processing…",
        }
        try:
            self._icon.icon  = img
            self._icon.title = titles.get(state, "VoiceFlow")
        except Exception as e:
            # Icon may not be fully initialized yet — ignore
            pass

    def _start_animation(self):
        self._anim_stop.clear()
        self._anim_thread = threading.Thread(
            target=self._animate, daemon=True, name="tray-anim"
        )
        self._anim_thread.start()

    def _stop_animation(self):
        self._anim_stop.set()
        if self._anim_thread and self._anim_thread.is_alive():
            self._anim_thread.join(timeout=1.0)
        self._anim_thread = None

    def _animate(self):
        colors = STATE_COLORS["processing"]
        frame  = 0
        while not self._anim_stop.is_set():
            self._update_icon(_make_image(colors[frame % len(colors)]), "processing")
            frame += 1
            time.sleep(ANIM_INTERVAL)

    def _quit_action(self, icon, item):
        print("[tray] Quit.")
        self.stop()
        if self._on_quit_cb:
            self._on_quit_cb()
        import os
        os._exit(0)

    def _dashboard_action(self, icon, item):
        import webbrowser
        port = getattr(self, '_dashboard_port', 57327)
        webbrowser.open(f'http://localhost:{port}/')

    def _settings_action(self, icon, item):
        if self._on_settings_cb:
            self._on_settings_cb()
        else:
            import subprocess
            subprocess.run(["open", "-e", str(__import__("pathlib").Path.home() / ".voiceflow" / "config.toml")])


# ── Singleton ─────────────────────────────────────────────────────── #
_tray_instance: TrayIcon | None = None

def get_tray() -> TrayIcon:
    global _tray_instance
    if _tray_instance is None:
        _tray_instance = TrayIcon()
    return _tray_instance
