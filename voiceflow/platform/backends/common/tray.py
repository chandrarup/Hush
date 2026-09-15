"""Cross-platform pystray implementation with injected settings behavior."""

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
ANIM_INTERVAL = 0.25
STATE_COLORS = {
    "idle": "#888888",
    "recording": "#E53935",
    "processing": ["#FF6F00", "#FFB300", "#FF8F00", "#FFA000"],
}


def _make_image(color: str):
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse(
        [CIRCLE_PADDING, CIRCLE_PADDING, ICON_SIZE - CIRCLE_PADDING, ICON_SIZE - CIRCLE_PADDING],
        fill=color,
    )
    return image


class TrayIcon:
    """A pystray menu with no operating-system-specific behavior."""

    def __init__(self, open_settings: Callable[[], bool] | None = None) -> None:
        self._state = "idle"
        self._icon = None
        self._lock = threading.Lock()
        self._animation_thread = None
        self._animation_stop = threading.Event()
        self._on_quit = None
        self._on_settings = None
        self._dashboard_port = 57327
        self._open_settings = open_settings or (lambda: False)
        self._enabled = _PIL_AVAILABLE and _PYSTRAY_AVAILABLE

    def setup(self, on_quit=None, on_settings=None, dashboard_port: int = 57327):
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._dashboard_port = dashboard_port

    def run_blocking(self):
        if not self._enabled:
            print("[tray] Tray disabled — running headlessly.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                return

        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", self._dashboard_action, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings (config)", self._settings_action),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Hush", self._quit_action),
        )
        self._icon = pystray.Icon(
            name="Hush",
            icon=_make_image(STATE_COLORS["idle"]),
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
        self._stop_animation()
        if state == "processing":
            self._start_animation()
        else:
            self._update_icon(_make_image(STATE_COLORS.get(state, "#888888")), state)

    def stop(self):
        self._stop_animation()
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass

    def _update_icon(self, image, state: str):
        if self._icon is None:
            return
        titles = {
            "idle": "Hush — Idle",
            "recording": "Hush — Recording…",
            "processing": "Hush — Processing…",
        }
        try:
            self._icon.icon = image
            self._icon.title = titles.get(state, "Hush")
        except Exception:
            pass

    def _start_animation(self):
        self._animation_stop.clear()
        self._animation_thread = threading.Thread(target=self._animate, daemon=True, name="tray-animation")
        self._animation_thread.start()

    def _stop_animation(self):
        self._animation_stop.set()
        if self._animation_thread and self._animation_thread.is_alive():
            self._animation_thread.join(timeout=1.0)
        self._animation_thread = None

    def _animate(self):
        colors = STATE_COLORS["processing"]
        frame = 0
        while not self._animation_stop.is_set():
            self._update_icon(_make_image(colors[frame % len(colors)]), "processing")
            frame += 1
            time.sleep(ANIM_INTERVAL)

    def _quit_action(self, _icon, _item):
        self.stop()
        if self._on_quit:
            self._on_quit()

    def _dashboard_action(self, _icon, _item):
        import webbrowser

        webbrowser.open(f"http://localhost:{self._dashboard_port}/")

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
