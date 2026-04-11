"""
onboarding.py — First-launch detection and macOS permission checking.

Called by api_server.py to power the /permissions endpoints.
Also used by main.py to decide whether to show the onboarding wizard.
"""

import pathlib
import subprocess
import sys

_IS_MACOS = sys.platform == "darwin"

ONBOARDED_FLAG  = pathlib.Path.home() / ".voiceflow" / ".onboarded"
VOICEFLOW_DIR   = pathlib.Path.home() / ".voiceflow"


# ── First-launch ───────────────────────────────────────────────────── #

def is_first_launch() -> bool:
    """True if the user has not yet completed onboarding."""
    return not ONBOARDED_FLAG.exists()


def mark_onboarded():
    """Write the flag file so onboarding is skipped on next launch."""
    VOICEFLOW_DIR.mkdir(parents=True, exist_ok=True)
    ONBOARDED_FLAG.touch()
    print("[onboarding] Marked as onboarded.")


# ── Permission checks ──────────────────────────────────────────────── #

def check_microphone() -> bool:
    """Return True if the app has microphone access."""
    try:
        import sounddevice as sd
        devs = sd.query_devices()
        if isinstance(devs, dict):
            return devs.get("max_input_channels", 0) > 0
        return any(d.get("max_input_channels", 0) > 0 for d in devs)
    except Exception:
        return False


def check_input_monitoring() -> bool:
    """
    Return True if Input Monitoring appears to be granted.
    pynput's IS_TRUSTED is unreliable after first grant (gives false negatives)
    so we do a best-effort check and default to True to avoid blocking the wizard.
    The real test is whether the hotkey actually works at runtime.
    """
    try:
        from pynput import keyboard as kb
        lst = kb.Listener(on_press=lambda k: None, on_release=lambda k: None, suppress=False)
        lst.start()
        trusted = getattr(lst, "IS_TRUSTED", None)
        lst.stop()
        # IS_TRUSTED = False means *definitely* denied (fresh macOS block).
        # IS_TRUSTED = True or None means granted or indeterminate — let through.
        return trusted is not False
    except Exception:
        return True  # Can't check — assume OK


def check_accessibility() -> bool:
    """Return True if Accessibility permission is granted."""
    if not _IS_MACOS:
        return True
    try:
        from Quartz import AXIsProcessTrusted
        return bool(AXIsProcessTrusted())
    except Exception:
        return True


def get_all_permissions() -> dict:
    """Return status of all three required permissions."""
    return {
        "microphone":      check_microphone(),
        "input_monitoring": check_input_monitoring(),
        "accessibility":   check_accessibility(),
    }


def all_granted(perms: dict | None = None) -> bool:
    p = perms or get_all_permissions()
    return all(p.values())


# ── System Settings deep-links ─────────────────────────────────────── #

_SETTINGS_URLS = {
    "microphone":       "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    "input_monitoring": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
    "accessibility":    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
}


def open_system_settings(perm_type: str) -> bool:
    """
    Deep-link into the correct System Settings pane.
    Returns True if the URL was successfully dispatched.
    """
    url = _SETTINGS_URLS.get(perm_type)
    if not url:
        return False
    try:
        subprocess.run(["open", url], check=True)
        return True
    except Exception as e:
        print(f"[onboarding] Could not open System Settings: {e}")
        return False
