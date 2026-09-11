"""Portable console notification adapter."""

from ..common.notifications import print_notification, show_transcript_result


class GenericNotifications:
    def show_result(self, raw_text, clean_text, duration_seconds=3, enabled=True):
        show_transcript_result(raw_text, clean_text, duration_seconds, enabled, self._dispatch)

    @staticmethod
    def _dispatch(title: str, message: str, _duration_seconds: int) -> None:
        print_notification(title, message)
