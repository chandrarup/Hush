"""macOS notification adapter."""

import subprocess

from ..common.notifications import print_notification, show_transcript_result


class MacOSNotifications:
    def show_result(self, raw_text, clean_text, duration_seconds=3, enabled=True):
        show_transcript_result(raw_text, clean_text, duration_seconds, enabled, self._dispatch)

    @staticmethod
    def _dispatch(title: str, message: str, _duration_seconds: int) -> None:
        escaped_title = title.replace('"', '\\"')
        escaped_message = message.replace('"', '\\"')
        script = f'display notification "{escaped_message}" with title "{escaped_title}"'
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            if result.returncode != 0:
                print_notification(title, message)
        except Exception as exc:
            print(f"[notification] macOS notification failed: {exc}")
            print_notification(title, message)
