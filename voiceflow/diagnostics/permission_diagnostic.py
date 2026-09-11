"""Print interpreter and global-input permission diagnostics."""

from __future__ import annotations

import os
import platform
import sys
import time


def main() -> None:
    real_path = os.path.realpath(sys.executable)
    print("=" * 60)
    print("VoiceFlow Permission Diagnostic")
    print("=" * 60)
    print(f"\nOperating system: {platform.system()}")
    print(f"Python executable: {sys.executable}")
    print(f"Resolved executable: {real_path}")
    print(f"Python version: {sys.version.split()[0]}")

    try:
        from pynput import keyboard

        listener = keyboard.Listener(on_press=lambda _: None)
        listener.start()
        time.sleep(0.3)
        trusted = getattr(listener, "IS_TRUSTED", None)
        listener.stop()
        print(f"Global keyboard trust: {trusted}")
    except Exception as exc:
        print(f"Global keyboard diagnostic failed: {exc}")

    print("\nIf global hotkeys do not work, grant the keyboard/input permission")
    print("to the launcher that starts VoiceFlow, then restart that launcher.")
    print("The active platform backend owns any OS-specific permission details.")


if __name__ == "__main__":
    main()
