"""Cross-platform pystray control with an optional activity HUD."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

try:
    from PIL import Image, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    import pystray
    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False


ICON_SIZE = 64
CIRCLE_PADDING = 8
def _make_menu_image():
    """Draw a static waveform mark instead of a distracting status dot."""
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    heights = (16, 28, 40, 24, 34)
    x = 14
    for height in heights:
        top = (ICON_SIZE - height) // 2
        draw.rounded_rectangle([x, top, x + 5, top + height], radius=2, fill="#8FA5A5")
        x += 8
    return image


class TrayIcon:
    """A pystray menu with no operating-system-specific behavior."""

    def __init__(self, open_settings: Callable[[], bool] | None = None, activity_hud=None) -> None:
        self._state = "idle"
        self._icon = None
        self._lock = threading.Lock()
        self._on_quit = None
        self._on_settings = None
        self._dashboard_port = 57327
        self._open_settings = open_settings or (lambda: False)
        self._activity_hud = activity_hud
        self._enabled = _PIL_AVAILABLE and _PYSTRAY_AVAILABLE

    def setup(self, on_quit=None, on_settings=None, dashboard_port: int = 57327):
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._dashboard_port = dashboard_port

    def run_blocking(self):
        if self._activity_hud is not None:
            self._activity_hud.prepare()
        if not self._enabled:
            print("[tray] Tray disabled — running headlessly.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                return

        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", self._dashboard_action, default=True),
            pystray.MenuItem("Run Setup Again", self._setup_action),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings (config)", self._settings_action),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Hush", self._quit_action),
        )
        self._icon = pystray.Icon(
            name="Hush",
            icon=_make_menu_image(),
            title="Hush — Idle",
            menu=menu,
        )
        print("[tray] Starting tray icon on main thread.")
        self._icon.run()

    def set_state(self, state: str):
        if not self._enabled:
            return
        with self._lock:
            if self._state == state:
                return
            self._state = state
        if self._activity_hud is not None:
            self._activity_hud.set_state(state)
        self._update_title(state)

    def stop(self):
        if self._activity_hud is not None:
            self._activity_hud.set_state("idle")
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass

    def _update_title(self, state: str):
        if self._icon is None:
            return
        titles = {
            "idle": "Hush — Idle",
            "recording": "Hush — Recording…",
            "processing": "Hush — Processing…",
        }
        try:
            self._icon.title = titles.get(state, "Hush")
        except Exception:
            pass

    def _quit_action(self, _icon, _item):
        self.stop()
        if self._on_quit:
            self._on_quit()

    def _dashboard_action(self, _icon, _item):
        import webbrowser

        webbrowser.open(f"http://localhost:{self._dashboard_port}/")

    def _setup_action(self, _icon, _item):
        import webbrowser

        webbrowser.open(f"http://localhost:{self._dashboard_port}/onboarding")

    def _settings_action(self, _icon, _item):
        if self._on_settings:
            self._on_settings()
        else:
            self._open_settings()


_tray_instance: TrayIcon | None = None


def get_tray(open_settings: Callable[[], bool] | None = None) -> TrayIcon:
    global _tray_instance
    if _tray_instance is None:
        _tray_instance = TrayIcon(open_settings=open_settings)
    return _tray_instance
