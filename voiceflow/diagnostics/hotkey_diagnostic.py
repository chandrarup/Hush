#!/usr/bin/env python3
"""Standalone cross-platform global-hotkey diagnostic."""

from __future__ import annotations

import sys
import time


def main() -> None:
    try:
        from pynput import keyboard

        print("[diag] pynput imported OK")
    except ImportError:
        print("[diag] FATAL: pynput not installed. Run: uv sync --no-dev")
        sys.exit(1)

    def on_press(key):
        print(f"[diag] PRESS   {repr(key):<35} (type={type(key).__name__})")

    def on_release(key):
        print(f"[diag] RELEASE {repr(key):<35} (type={type(key).__name__})")

    print("=" * 60)
    print("VoiceFlow Global Hotkey Diagnostic")
    print("=" * 60)
    print("Press any key to test. Press Ctrl+C to quit.\n")

    listener = keyboard.Listener(on_press=on_press, on_release=on_release, suppress=False)
    listener.start()
    trusted = getattr(listener, "IS_TRUSTED", None)
    print(f"Global keyboard trust: {trusted}")
    print("If no PRESS/RELEASE lines appear, grant keyboard/input permission and restart.\n")

    try:
        while listener.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[diag] Stopped by user.")
        listener.stop()


if __name__ == "__main__":
    main()
