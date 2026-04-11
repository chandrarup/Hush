#!/usr/bin/env python3
"""
diag_hotkey.py — Standalone hotkey diagnostic for VoiceFlow.

Runs ONLY the pynput listener (no ASR, no audio, no tray) and prints
every key event it receives.  Use this to confirm whether pynput can
see key events before running the full app.

Usage:
    python diag_hotkey.py

Press any key.  Press Ctrl+C to quit.
"""

import sys
import time

try:
    from pynput import keyboard as _kb
    print("[diag] pynput imported OK")
except ImportError:
    print("[diag] FATAL: pynput not installed. Run: pip install pynput")
    sys.exit(1)


def on_press(key):
    try:
        print(f"[diag] PRESS   {repr(key):<35}  (type={type(key).__name__})")
    except Exception as e:
        print(f"[diag] PRESS   <error reading key: {e}>")


def on_release(key):
    try:
        print(f"[diag] RELEASE {repr(key):<35}  (type={type(key).__name__})")
    except Exception as e:
        print(f"[diag] RELEASE <error reading key: {e}>")


print("=" * 60)
print("  VoiceFlow Hotkey Diagnostic")
print("=" * 60)
print("Press any key to test. Press Ctrl+C to quit.\n")
print("WHAT TO LOOK FOR:")
print("  ✓ If you see PRESS lines → pynput is working")
print("  ✗ If you see nothing    → Input Monitoring not granted")
print("    Fix: System Settings → Privacy & Security → Input Monitoring")
print("         → Add Terminal (or Python) → Restart\n")

listener = _kb.Listener(on_press=on_press, on_release=on_release, suppress=False)
listener.start()

trusted = getattr(listener, 'IS_TRUSTED', None)
if trusted is False:
    print("!" * 60)
    print("⚠  IS_TRUSTED = False — macOS will block ALL key events")
    print("   Grant Input Monitoring permission and restart.")
    print("!" * 60 + "\n")
elif trusted is True:
    print(f"✓ IS_TRUSTED = True — permission granted, events should flow\n")
else:
    print(f"[diag] IS_TRUSTED = {trusted}  (None = old pynput, assume OK)\n")

try:
    while listener.running:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n[diag] Stopped by user.")
    listener.stop()
