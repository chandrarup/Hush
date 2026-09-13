"""macOS text injection strategies."""

from __future__ import annotations

import subprocess
import threading
import time

from ..common.clipboard import paste_with_gui, print_injection_failure


class MacOSTextInjector:
    """Inject text through Quartz, clipboard paste, or pyautogui fallback."""

    def inject_text(self, text: str, preferred_method: str = "auto") -> bool:
        if not text or not text.strip():
            return False
        text = text.strip()
        strategies = {
            "auto": (self._quartz, self._clipboard_paste, self._gui_paste),
            "quartz": (self._quartz, self._clipboard_paste, self._gui_paste),
            "clipboard": (self._clipboard_paste, self._quartz, self._gui_paste),
            "pyautogui": (self._gui_paste, self._quartz, self._clipboard_paste),
        }
        for strategy in strategies.get(preferred_method, strategies["auto"]):
            if strategy(text):
                return True
        return print_injection_failure()

    @staticmethod
    def _quartz(text: str) -> bool:
        try:
            from Quartz import (
                CGEventCreateKeyboardEvent,
                CGEventKeyboardSetUnicodeString,
                CGEventPost,
                CGEventSourceCreate,
                kCGEventSourceStateHIDSystemState,
                kCGHIDEventTap,
            )

            source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
            for start in range(0, len(text), 50):
                for char in text[start : start + 50]:
                    key_down = CGEventCreateKeyboardEvent(source, 0, True)
                    CGEventKeyboardSetUnicodeString(key_down, len(char), char)
                    CGEventPost(kCGHIDEventTap, key_down)
                    key_up = CGEventCreateKeyboardEvent(source, 0, False)
                    CGEventKeyboardSetUnicodeString(key_up, len(char), char)
                    CGEventPost(kCGHIDEventTap, key_up)
                if start + 50 < len(text):
                    time.sleep(0.01)
            print(f"[text] Quartz injected {len(text)} characters.")
            return True
        except Exception as exc:
            print(f"[text] Quartz injection failed: {exc}")
            return False

    @staticmethod
    def _clipboard_paste(text: str) -> bool:
        try:
            previous = subprocess.run(["pbpaste"], capture_output=True, timeout=2).stdout
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True, timeout=3)
            time.sleep(0.06)
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
                capture_output=True,
                timeout=5,
            )
            if previous:
                threading.Thread(
                    target=MacOSTextInjector._restore_clipboard,
                    args=(previous,),
                    daemon=True,
                    name="clipboard-restore",
                ).start()
            return result.returncode == 0
        except Exception as exc:
            print(f"[text] Clipboard paste failed: {exc}")
            return False

    @staticmethod
    def _restore_clipboard(previous: bytes) -> None:
        time.sleep(0.5)
        try:
            subprocess.run(["pbcopy"], input=previous, timeout=2)
        except Exception:
            pass

    @staticmethod
    def _gui_paste(text: str) -> bool:
        return paste_with_gui(text, "command+v")


def check_accessibility_permission() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted

        trusted = bool(AXIsProcessTrusted())
        if not trusted:
            print("[permission] Accessibility is required for text injection.")
            print("[permission] System Settings -> Privacy & Security -> Accessibility")
        return trusted
    except Exception as exc:
        print(f"[permission] Could not determine Accessibility status: {exc}")
        return False
