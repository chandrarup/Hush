"""Portable permission implementation and shared onboarding state."""

from __future__ import annotations

from pathlib import Path
import sys

from ....config.paths import DATA_DIR, ONBOARDED_PATH
from voiceflow.runtime import is_packaged_macos_app


def _packaged_app_install_marker() -> str | None:
    """Identify a copied Hush.app bundle without treating source runs as installs."""
    if not is_packaged_macos_app():
        return None

    executable = Path(sys.executable).resolve()
    app_bundle = next((path for path in (executable, *executable.parents) if path.suffix == ".app"), None)
    if app_bundle is None:
        return None

    try:
        stat = app_bundle.stat()
    except OSError:
        return None

    # Finder gives a copied application bundle a new creation timestamp. Use
    # mtime as a fallback for filesystems that do not expose birth time.
    created_at = getattr(stat, "st_birthtime", stat.st_mtime)
    return f"{app_bundle}:{created_at}"


class DesktopPermissions:
    """Best-effort permission checks for platforms without special privacy APIs."""

    def __init__(self, permission_guide: str = "") -> None:
        self._data_dir = DATA_DIR
        self._onboarded_flag = ONBOARDED_PATH
        self._onboarding_in_progress_flag = self._data_dir / ".onboarding_in_progress"
        self._install_marker_flag = self._data_dir / ".installed_bundle"
        self._permission_guide = permission_guide

    def is_first_launch(self) -> bool:
        if not self._onboarded_flag.exists():
            return True

        install_marker = _packaged_app_install_marker()
        if install_marker is None:
            return False

        try:
            return self._install_marker_flag.read_text(encoding="utf-8") != install_marker
        except OSError:
            return True

    def mark_onboarded(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._onboarded_flag.touch()
        self._onboarding_in_progress_flag.unlink(missing_ok=True)
        install_marker = _packaged_app_install_marker()
        if install_marker is not None:
            self._install_marker_flag.write_text(install_marker, encoding="utf-8")

    def begin_onboarding(self) -> None:
        """Remember an unfinished setup so a TCC-requested restart resumes it."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._onboarding_in_progress_flag.touch()

    def is_onboarding_in_progress(self) -> bool:
        return self._onboarding_in_progress_flag.exists()

    def check_accessibility_permission(self) -> bool:
        return True

    def get_all_permissions(self) -> dict:
        return {
            "microphone": self._check_microphone(),
            "input_monitoring": self._check_input_monitoring(),
            "accessibility": True,
        }

    def request_permission(self, permission_type: str) -> bool:
        return self.open_system_settings(permission_type)

    def open_system_settings(self, permission_type: str) -> bool:
        return False

    def print_permission_guide(self) -> None:
        if self._permission_guide:
            print(self._permission_guide)

    @staticmethod
    def _check_microphone() -> bool:
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            if isinstance(devices, dict):
                return devices.get("max_input_channels", 0) > 0
            return any(device.get("max_input_channels", 0) > 0 for device in devices)
        except Exception:
            return False

    @staticmethod
    def _check_input_monitoring() -> bool:
        try:
            from pynput import keyboard

            listener = keyboard.Listener(on_press=lambda _: None, on_release=lambda _: None)
            listener.start()
            trusted = getattr(listener, "IS_TRUSTED", None)
            listener.stop()
            return trusted is not False
        except Exception:
            return True
