"""macOS privacy permission adapter."""

from __future__ import annotations

import subprocess

from ..common.permissions import DesktopPermissions
from .text_injection import check_accessibility_permission
from .tcc import (
    is_microphone_authorized,
    request_accessibility,
    request_microphone,
)


class MacOSPermissions(DesktopPermissions):
    def __init__(self) -> None:
        super().__init__(
            """
macOS permissions:
  Hush requests permissions during onboarding.
  Accessibility: System Settings -> Privacy & Security -> Accessibility
""".strip()
        )
    def check_accessibility_permission(self) -> bool:
        return check_accessibility_permission()

    def get_all_permissions(self) -> dict:
        return {
            "microphone": is_microphone_authorized(),
            "accessibility": self.check_accessibility_permission(),
        }

    def request_permission(self, permission_type: str) -> bool:
        if permission_type == "microphone":
            return request_microphone()
        if permission_type == "accessibility":
            return request_accessibility()
        return False

    def open_system_settings(self, permission_type: str) -> bool:
        urls = {
            "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
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
