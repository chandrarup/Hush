"""
notifier.py — Desktop notification showing raw vs cleaned transcript.

Uses plyer for cross-platform desktop notifications.
Falls back to a simple print statement if plyer is not available.
"""

import sys
import threading

_IS_MACOS = sys.platform == "darwin"

try:
    if _IS_MACOS:
        # Skip plyer on macOS — it requires pyobjus (Kivy dep) which is
        # not installed. Use the native osascript backend instead.
        _PLYER_AVAILABLE = False
    else:
        from plyer import notification as _plyer_notify
        _PLYER_AVAILABLE = True
except ImportError:
    _PLYER_AVAILABLE = False

# Fallback: try macOS osascript notification


def _truncate(text: str, max_chars: int = 60) -> str:
    """Truncate text to max_chars with ellipsis."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


def _send_plyer(title: str, message: str, timeout: int):
    """Send a desktop notification via plyer."""
    try:
        _plyer_notify.notify(
            title=title,
            message=message,
            app_name="VoiceFlow",
            timeout=timeout,
        )
    except Exception as e:
        print(f"[notifier] plyer notification failed: {e}")
        # Fall through to print fallback below
        _print_notification(title, message)


def _send_macos_osascript(title: str, message: str):
    """Send a macOS notification via osascript (no extra deps)."""
    import subprocess
    # Escape double quotes
    title_esc = title.replace('"', '\\"')
    msg_esc = message.replace('"', '\\"')
    script = f'display notification "{msg_esc}" with title "{title_esc}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            timeout=5,
            capture_output=True,
        )
    except Exception as e:
        print(f"[notifier] osascript notification failed: {e}")
        _print_notification(title, message)


def _send_linux_notify(title: str, message: str, timeout_ms: int):
    """Send a Linux notification via notify-send."""
    import subprocess
    import shutil
    if shutil.which("notify-send") is None:
        _print_notification(title, message)
        return
    try:
        subprocess.run(
            ["notify-send", "-t", str(timeout_ms), title, message],
            timeout=5,
            capture_output=True,
        )
    except Exception as e:
        print(f"[notifier] notify-send failed: {e}")
        _print_notification(title, message)


def _print_notification(title: str, message: str):
    """Console fallback when all notification backends fail."""
    border = "─" * 50
    print(f"\n┌{border}┐")
    print(f"│ {title:<48} │")
    print(f"├{border}┤")
    for line in message.splitlines():
        print(f"│ {line:<48} │")
    print(f"└{border}┘\n")


def _dispatch(title: str, message: str, timeout_seconds: int):
    """Choose the best notification backend and send."""
    if _PLYER_AVAILABLE:
        _send_plyer(title, message, timeout_seconds)
        return

    if _IS_MACOS:
        _send_macos_osascript(title, message)
        return

    # Linux: try notify-send
    _send_linux_notify(title, message, timeout_seconds * 1000)


def show_result(
    raw_text: str,
    clean_text: str,
    duration_seconds: int = 3,
    enabled: bool = True,
):
    """
    Show a floating notification with raw and cleaned transcript.

    Args:
        raw_text:         Raw Whisper output.
        clean_text:       LLM-cleaned output.
        duration_seconds: How long the notification is visible.
        enabled:          If False, skip (respects config ui.show_notification).
    """
    if not enabled:
        return

    title = "VoiceFlow"
    raw_short = _truncate(raw_text, 60)
    clean_short = _truncate(clean_text, 60)
    message = f"Raw: {raw_short}\nClean: {clean_short}"

    # Always print to console regardless
    print(f"[notifier] Raw:   {raw_short}")
    print(f"[notifier] Clean: {clean_short}")

    # Fire notification in a non-blocking thread so pipeline isn't held up
    t = threading.Thread(
        target=_dispatch,
        args=(title, message, duration_seconds),
        daemon=True,
    )
    t.start()
