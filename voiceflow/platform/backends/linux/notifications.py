"""Linux desktop notification adapter."""

import shutil
import subprocess

from ..common.notifications import print_notification, show_transcript_result


class LinuxNotifications:
    def show_result(self, raw_text, clean_text, duration_seconds=3, enabled=True):
        show_transcript_result(raw_text, clean_text, duration_seconds, enabled, self._dispatch)

    @staticmethod
    def _dispatch(title: str, message: str, duration_seconds: int) -> None:
        if shutil.which("notify-send") is None:
            print_notification(title, message)
            return
        try:
            result = subprocess.run(
                ["notify-send", "-t", str(duration_seconds * 1000), title, message],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                print_notification(title, message)
        except Exception as exc:
            print(f"[notification] Linux notification failed: {exc}")
            print_notification(title, message)
