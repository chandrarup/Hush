"""Windows permission and settings adapter."""

import subprocess

from ..common.permissions import DesktopPermissions


class WindowsPermissions(DesktopPermissions):
    def open_system_settings(self, permission_type: str) -> bool:
        pages = {
            "microphone": "ms-settings:privacy-microphone",
            "accessibility": "ms-settings:easeofaccess",
        }
        page = pages.get(permission_type)
        if not page:
            return False
        try:
            subprocess.run(["cmd", "/c", "start", "", page], check=True)
            return True
        except Exception as exc:
            print(f"[permission] Could not open Windows settings: {exc}")
            return False
