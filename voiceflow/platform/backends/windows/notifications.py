"""Windows desktop notification adapter."""

from ..common.notifications import print_notification, show_transcript_result


class WindowsNotifications:
    def show_result(self, raw_text, clean_text, duration_seconds=3, enabled=True):
        show_transcript_result(raw_text, clean_text, duration_seconds, enabled, self._dispatch)

    @staticmethod
    def _dispatch(title: str, message: str, duration_seconds: int) -> None:
        try:
            from plyer import notification

            notification.notify(title=title, message=message, app_name=title, timeout=duration_seconds)
        except Exception as exc:
            print(f"[notification] Windows notification failed: {exc}")
            print_notification(title, message)
