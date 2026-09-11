"""Portable permission implementation and shared onboarding state."""

from __future__ import annotations

from pathlib import Path


class DesktopPermissions:
    """Best-effort permission checks for platforms without special privacy APIs."""

    def __init__(self, permission_guide: str = "") -> None:
        self._voiceflow_dir = Path.home() / ".voiceflow"
        self._onboarded_flag = self._voiceflow_dir / ".onboarded"
        self._permission_guide = permission_guide

    def is_first_launch(self) -> bool:
        return not self._onboarded_flag.exists()

    def mark_onboarded(self) -> None:
        self._voiceflow_dir.mkdir(parents=True, exist_ok=True)
        self._onboarded_flag.touch()

    def check_accessibility_permission(self) -> bool:
        return True

    def get_all_permissions(self) -> dict:
        return {
            "microphone": self._check_microphone(),
            "input_monitoring": self._check_input_monitoring(),
            "accessibility": True,
        }

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
