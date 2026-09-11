"""Optional clipboard and GUI helpers shared by desktop adapters."""

from __future__ import annotations

import time


def paste_with_gui(text: str, paste_key: str) -> bool:
    """Paste text through the optional pyperclip/pyautogui dependencies."""
    try:
        import pyperclip
        import pyautogui

        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey(*paste_key.split("+"))
        return True
    except Exception as exc:
        print(f"[text] GUI paste failed: {exc}")
        return False


def print_injection_failure() -> bool:
    print("[text] No compatible text-injection backend succeeded.")
    return False
