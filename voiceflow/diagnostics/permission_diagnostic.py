"""Print interpreter and global-input permission diagnostics."""

from __future__ import annotations

import platform
import sys
import time
from pathlib import Path


def find_python_app(executable: str | None = None, base_prefix: str | None = None) -> Path | None:
    """Find the selectable macOS Python.app behind a venv or Homebrew symlink."""
    roots = [Path(executable or sys.executable).resolve(), Path(base_prefix or sys.base_prefix).resolve()]
    for root in roots:
        for parent in (root, *root.parents):
            if parent.name == "Python.app" and parent.is_dir():
                return parent
            candidate = parent / "Resources" / "Python.app"
            if candidate.is_dir():
                return candidate
    return None


def main() -> None:
    print("Let's Hush. Permission guide\n")
    if sys.platform != "darwin":
        print("These privacy steps apply only to macOS. See docs/setup.md for your platform.")
        return

    print("1. Open Apple menu > System Settings > Privacy & Security.")
    print("   Choose Accessibility inside Privacy & Security, not the main sidebar item.")
    print("2. Click +, authenticate if asked, then press Command+Shift+G.")
    print("   Paste this folder, press Return, select Terminal.app, and turn it on:")
    print("\n   /System/Applications/Utilities\n")
    print("3. Repeat step 2 in Privacy & Security > Input Monitoring.")
    print("   If you launch Hush from Codex, ChatGPT, VS Code, or iTerm, allow that")
    print("   launcher in both lists instead. Use the same launcher to run Hush.")

    app = find_python_app()
    if app:
        print("\nIf keys or typing still fail, add Python.app in both lists:")
        print("   Click +, press Command+Shift+G, and paste this exact folder:")
        print(f"\n   {app.parent}\n")
        print("   Select Python.app and turn its switch on. Do not select .venv/bin/python.")
    else:
        print("\nNo selectable Python.app was found. Allow your launcher first; do not guess a path.")

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

    print("\n4. Quit the launcher with Command+Q, reopen it, then start Hush again.")
    print("5. Allow Microphone when prompted. It appears only after Hush requests it.")
    print("\nFor diagnostics, this Python executable resolves to:")
    print(f"   {Path(sys.executable).resolve()}")
    print("\nThese instructions do not grant or verify permissions.")


if __name__ == "__main__":
    main()
