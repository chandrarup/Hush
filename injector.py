"""
injector.py — Text injection for macOS.

Priority chain:
  1. Quartz CGEvent  — native macOS low-level keystrokes via pyobjc
                       No clipboard, no flash, works in EVERY app including
                       browser AI chat inputs (ChatGPT, Claude, Perplexity)
  2. pbcopy + osascript Cmd+V  — clipboard paste, fast and reliable
  3. pyautogui.write()  — last resort, slowest

Install the native method:
  pip install pyobjc-framework-Quartz

The Quartz method is how Super Whisper and OpenWhispr inject text.
It posts Unicode keyboard events directly to the HID event system —
no window focus juggling, no clipboard side effects.
"""

import sys
import time
import subprocess
import shutil

_IS_MACOS = sys.platform == "darwin"

# ── Try importing Quartz (pyobjc) ─────────────────────────────────── #
try:
    import Quartz
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSourceCreate,
        CGEventKeyboardSetUnicodeString,
        kCGHIDEventTap,
        kCGEventSourceStateHIDSystemState,
    )
    _QUARTZ_AVAILABLE = True
except ImportError:
    _QUARTZ_AVAILABLE = False

# ── Optional fallbacks ────────────────────────────────────────────── #
try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

# xdotool for Linux
_XDOTOOL = shutil.which("xdotool") if not _IS_MACOS else None


# ──────────────────────────────────────────────────────────────────── #
#  Method 1 — Quartz CGEvent (macOS native, best)                       #
# ──────────────────────────────────────────────────────────────────── #

def _quartz_type(text: str) -> bool:
    """
    Type text using low-level CGEvent Unicode keyboard events.
    Works in every macOS app — browsers, terminals, Slack, VS Code, etc.
    Does NOT touch the clipboard.

    Requires: pip install pyobjc-framework-Quartz
    Requires: Accessibility permission for your Terminal / Python binary.
    """
    if not _QUARTZ_AVAILABLE:
        return False

    try:
        src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

        # Type in chunks to avoid overwhelming the event queue
        CHUNK = 50
        for i in range(0, len(text), CHUNK):
            chunk = text[i : i + CHUNK]
            for char in chunk:
                # Key down
                ev_down = CGEventCreateKeyboardEvent(src, 0, True)
                CGEventKeyboardSetUnicodeString(ev_down, len(char), char)
                CGEventPost(kCGHIDEventTap, ev_down)
                # Key up
                ev_up = CGEventCreateKeyboardEvent(src, 0, False)
                CGEventKeyboardSetUnicodeString(ev_up, len(char), char)
                CGEventPost(kCGHIDEventTap, ev_up)
            # Brief pause between chunks — prevents dropped characters
            if i + CHUNK < len(text):
                time.sleep(0.01)

        print(f"[injector] ✓ Quartz CGEvent — injected {len(text)} chars.")
        return True

    except Exception as e:
        print(f"[injector] Quartz failed: {e}")
        return False


# ──────────────────────────────────────────────────────────────────── #
#  Method 2 — pbcopy + osascript Cmd+V (macOS clipboard)               #
# ──────────────────────────────────────────────────────────────────── #

def _mac_clipboard_paste(text: str) -> bool:
    """
    Copy to clipboard via pbcopy, then simulate Cmd+V via osascript.
    Faster than pyautogui. Works everywhere that accepts paste.
    Side effect: overwrites clipboard temporarily.
    """
    try:
        # Save old clipboard so we can restore it after paste
        try:
            old = subprocess.run(["pbpaste"], capture_output=True, timeout=2).stdout
        except Exception:
            old = b""

        # Write new text to clipboard
        subprocess.run(
            ["pbcopy"],
            input=text.encode("utf-8"),
            check=True,
            timeout=3,
        )
        time.sleep(0.06)  # let clipboard settle

        # Simulate Cmd+V
        script = 'tell application "System Events" to keystroke "v" using command down'
        result = subprocess.run(
            ["osascript", "-e", script],
            timeout=5,
            capture_output=True,
        )
        time.sleep(0.08)

        # Restore old clipboard (async, best-effort)
        if old:
            def _restore():
                time.sleep(0.5)
                try:
                    subprocess.run(["pbcopy"], input=old, timeout=2)
                except Exception:
                    pass
            import threading
            threading.Thread(target=_restore, daemon=True).start()

        ok = result.returncode == 0
        if ok:
            print(f"[injector] ✓ pbcopy+osascript — injected {len(text)} chars.")
        return ok

    except Exception as e:
        print(f"[injector] pbcopy+osascript failed: {e}")
        return False


# ──────────────────────────────────────────────────────────────────── #
#  Method 3 — pyautogui (last resort, slow)                             #
# ──────────────────────────────────────────────────────────────────── #

def _pyautogui_type(text: str) -> bool:
    if not _PYAUTOGUI:
        return False
    try:
        # pyautogui.write can't handle Unicode; use clipboard+hotkey instead
        import pyperclip as _pc
        _pc.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("command" if _IS_MACOS else "ctrl", "v")
        print(f"[injector] ✓ pyautogui — injected {len(text)} chars.")
        return True
    except Exception as e:
        print(f"[injector] pyautogui failed: {e}")
        return False


# ──────────────────────────────────────────────────────────────────── #
#  Linux fallback — xdotool                                             #
# ──────────────────────────────────────────────────────────────────── #

def _xdotool_type(text: str) -> bool:
    if not _XDOTOOL:
        return False
    # Use clipboard for single-quote safety
    if "'" in text:
        return _linux_clipboard_paste(text)
    try:
        result = subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "0", text],
            timeout=10, capture_output=True,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[injector] xdotool failed: {e}")
        return False


def _linux_clipboard_paste(text: str) -> bool:
    if not _PYPERCLIP:
        return False
    try:
        import pyperclip
        pyperclip.copy(text)
        time.sleep(0.05)
        if _XDOTOOL:
            subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                           timeout=5, capture_output=True)
            return True
        if _PYAUTOGUI:
            pyautogui.hotkey("ctrl", "v")
            return True
    except Exception as e:
        print(f"[injector] Linux clipboard paste failed: {e}")
    return False


# ──────────────────────────────────────────────────────────────────── #
#  Public API                                                           #
# ──────────────────────────────────────────────────────────────────── #

def inject_text(text: str, preferred_method: str = "quartz") -> bool:
    """
    Inject text into the currently focused input field.

    Args:
        text:             Text to inject.
        preferred_method: "quartz" | "clipboard" | "pyautogui" | "xdotool"

    Returns True on success.

    macOS method priority:
      quartz    → CGEvent Unicode (native, no clipboard, works everywhere)
      clipboard → pbcopy + Cmd+V (fast, slight clipboard flash)
      pyautogui → last resort

    Linux method priority:
      xdotool → clipboard+xdotool → pyautogui
    """
    if not text or not text.strip():
        return False

    text = text.strip()
    print(f"[injector] Injecting {len(text)} chars (preferred={preferred_method})")

    if _IS_MACOS:
        if preferred_method == "quartz":
            if _quartz_type(text):    return True
            if _mac_clipboard_paste(text): return True
            if _pyautogui_type(text): return True

        elif preferred_method == "clipboard":
            if _mac_clipboard_paste(text): return True
            if _quartz_type(text):    return True
            if _pyautogui_type(text): return True

        else:  # pyautogui
            if _pyautogui_type(text): return True
            if _quartz_type(text):    return True
            if _mac_clipboard_paste(text): return True

        print("[injector] All macOS injection methods failed.")
        return False

    # Linux
    if preferred_method in ("xdotool", "quartz"):
        if _xdotool_type(text):          return True
        if _linux_clipboard_paste(text): return True
    else:
        if _linux_clipboard_paste(text): return True
        if _xdotool_type(text):          return True

    if _pyautogui_type(text):
        return True

    print("[injector] All injection methods failed.")
    return False


def check_accessibility_permission() -> bool:
    """
    Check if Accessibility permission is granted (needed for Quartz injection).
    Returns True if granted or if not on macOS.
    Prints instructions if not granted.
    """
    if not _IS_MACOS:
        return True
    try:
        # AXIsProcessTrusted is the definitive check
        from Quartz import AXIsProcessTrusted
        trusted = AXIsProcessTrusted()
        if not trusted:
            print("\n[injector] ⚠  Accessibility permission required!")
            print("  Go to: System Settings → Privacy & Security → Accessibility")
            print("  Add your Terminal app (or Python binary) to the allowed list.")
            print("  Then restart VoiceFlow.\n")
        return trusted
    except Exception:
        return True  # Can't check — assume OK
