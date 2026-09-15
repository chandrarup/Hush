"""Notification primitives shared by platform adapters."""

from __future__ import annotations

import threading
from collections.abc import Callable


def truncate(text: str, max_chars: int = 60) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def print_notification(title: str, message: str) -> None:
    border = "─" * 50
    print(f"\n┌{border}┐")
    print(f"│ {title:<48} │")
    print(f"├{border}┤")
    for line in message.splitlines():
        print(f"│ {line:<48} │")
    print(f"└{border}┘\n")


def show_transcript_result(
    raw_text: str,
    clean_text: str,
    duration_seconds: int,
    enabled: bool,
    dispatch: Callable[[str, str, int], None],
) -> None:
    if not enabled:
        return

    raw_short = truncate(raw_text)
    clean_short = truncate(clean_text)
    message = f"Raw: {raw_short}\nClean: {clean_short}"
    print(f"[notification] Raw:   {raw_short}")
    print(f"[notification] Clean: {clean_short}")
    threading.Thread(
        target=dispatch,
        args=("Hush", message, duration_seconds),
        daemon=True,
        name="notification",
    ).start()
