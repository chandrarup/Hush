"""macOS privacy permission adapter."""

from __future__ import annotations

import subprocess

from ..common.permissions import DesktopPermissions
from .text_injection import check_accessibility_permission


class MacOSPermissions(DesktopPermissions):
    def __init__(self) -> None:
        super().__init__(
            """
macOS permissions:
  Input Monitoring: System Settings -> Privacy & Security -> Input Monitoring
  Accessibility:    System Settings -> Privacy & Security -> Accessibility
  Microphone:       System Settings -> Privacy & Security -> Microphone
Add the launcher that starts VoiceFlow, then restart it.
""".strip()
        )

    def check_accessibility_permission(self) -> bool:
        return check_accessibility_permission()

    def get_all_permissions(self) -> dict:
        permissions = super().get_all_permissions()
        permissions["accessibility"] = self.check_accessibility_permission()
        return permissions

    def open_system_settings(self, permission_type: str) -> bool:
        urls = {
            "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
            "input_monitoring": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
            "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        }
        url = urls.get(permission_type)
        if not url:
            return False
        try:
            subprocess.run(["open", url], check=True)
            return True
        except Exception as exc:
            print(f"[permission] Could not open System Settings: {exc}")
            return False
