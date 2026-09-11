"""Linux text injection strategies."""

from __future__ import annotations

import shutil
import subprocess

from ..common.clipboard import paste_with_gui, print_injection_failure


class LinuxTextInjector:
    def inject_text(self, text: str, preferred_method: str = "auto") -> bool:
        if not text or not text.strip():
            return False
        text = text.strip()
        strategies = {
            "auto": (self._xdotool, self._clipboard_paste, self._gui_paste),
            "xdotool": (self._xdotool, self._clipboard_paste, self._gui_paste),
            "clipboard": (self._clipboard_paste, self._xdotool, self._gui_paste),
            "pyautogui": (self._gui_paste, self._clipboard_paste, self._xdotool),
        }
        for strategy in strategies.get(preferred_method, strategies["auto"]):
            if strategy(text):
                return True
        return print_injection_failure()

    @staticmethod
    def _xdotool(text: str) -> bool:
        if shutil.which("xdotool") is None:
            return False
        try:
            result = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", "0", text],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as exc:
            print(f"[text] xdotool failed: {exc}")
            return False

    @staticmethod
    def _clipboard_paste(text: str) -> bool:
        try:
            import pyperclip

            pyperclip.copy(text)
            return paste_with_gui(text, "ctrl+v")
        except Exception:
            return False

    @staticmethod
    def _gui_paste(text: str) -> bool:
        return paste_with_gui(text, "ctrl+v")
