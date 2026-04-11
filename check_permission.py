"""
Run this script to find the EXACT binary path macOS is checking for Input Monitoring.
Copy the output path and add it to System Settings -> Privacy & Security -> Input Monitoring
"""
import sys
import os
import subprocess

print("=" * 60)
print("VoiceFlow Permission Diagnostic")
print("=" * 60)

# The actual executable macOS checks
print(f"\n1. sys.executable (THIS is what macOS checks):")
print(f"   {sys.executable}")

print(f"\n2. sys.version:")
print(f"   {sys.version}")

# Check if it resolves to something else (symlink)
real = os.path.realpath(sys.executable)
print(f"\n3. Resolved real path (follow symlinks):")
print(f"   {real}")

# Check current trust status
try:
    from pynput import keyboard
    lst = keyboard.Listener(on_press=lambda k: None)
    lst.start()
    import time; time.sleep(0.3)
    print(f"\n4. IS_TRUSTED: {lst.IS_TRUSTED}")
    lst.stop()
except Exception as e:
    print(f"\n4. Error checking trust: {e}")

print("\n" + "=" * 60)
print("ACTION REQUIRED:")
print("=" * 60)
print(f"\nAdd THIS exact path to:")
print(f"  System Settings -> Privacy & Security -> Input Monitoring")
print(f"  System Settings -> Privacy & Security -> Accessibility")
print(f"\n  PATH: {sys.executable}")
if real != sys.executable:
    print(f"\n  Also try the resolved path: {real}")
print(f"\nSteps:")
print(f"  1. Click + in Input Monitoring")
print(f"  2. Press Cmd+Shift+G")
print(f"  3. Paste the path above (without the filename)")
print(f"  4. Select the python binary and click Open")
print(f"  5. Quit Terminal completely (Cmd+Q) and reopen")
print("=" * 60)
