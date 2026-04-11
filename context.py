"""
context.py — Detect the active macOS application.

Used to give the LLM context about WHERE the user is typing,
so the output is formatted correctly for that app.

Examples:
  "Google Chrome" → format as a clean AI prompt
  "Slack"         → casual conversational message
  "Code"          → preserve ALL technical terms exactly
  "Mail"          → professional email tone
  "Terminal"      → minimal cleanup, don't touch command-like text
"""

import subprocess
import sys
import time
import functools

_IS_MACOS = sys.platform == "darwin"

# Cache the last detected app for 0.5s to avoid repeated osascript calls
_last_app: str | None = None
_last_app_time: float = 0.0
_APP_CACHE_TTL = 0.5  # seconds


def get_active_app() -> str | None:
    """
    Return the display name of the frontmost macOS application.
    Returns None on non-macOS or on error.

    Examples: "Google Chrome", "Slack", "Code", "Terminal", "Mail"
    """
    global _last_app, _last_app_time

    if not _IS_MACOS:
        return None

    now = time.monotonic()
    if _last_app is not None and (now - _last_app_time) < _APP_CACHE_TTL:
        return _last_app

    try:
        script = (
            'tell application "System Events" to '
            'get name of first process whose frontmost is true'
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=2,
        )
        app = result.stdout.strip()
        if app:
            _last_app = app
            _last_app_time = now
            return app
    except Exception as e:
        print(f"[context] Could not detect active app: {e}")

    return None


# ── Browser sub-detection ─────────────────────────────────────────── #
# When the browser is active, try to determine if it's an AI chat page
# by reading the window title.

AI_CHAT_URLS = [
    "chatgpt.com", "chat.openai.com",
    "claude.ai",
    "perplexity.ai",
    "gemini.google.com",
    "copilot.microsoft.com",
    "you.com", "phind.com", "poe.com",
    "character.ai",
]

BROWSER_APPS = {"Google Chrome", "Safari", "Firefox", "Arc", "Brave Browser", "Microsoft Edge"}


def get_active_context() -> dict:
    """
    Return a dict with app name and an optional sub-context hint.

    Returns:
        {
            "app": "Google Chrome",
            "is_ai_chat": True,
            "hint": "The user is typing a prompt into Claude (claude.ai)..."
        }
    """
    app = get_active_app()
    ctx = {"app": app, "is_ai_chat": False, "hint": None}

    if app in BROWSER_APPS:
        title = _get_browser_title(app)
        if title:
            for ai_url in AI_CHAT_URLS:
                if ai_url in title.lower():
                    service = _ai_service_name(ai_url)
                    ctx["is_ai_chat"] = True
                    ctx["hint"] = (
                        f"The user is typing a prompt into {service}. "
                        f"Write it as a clear, well-structured prompt. "
                        f"Preserve ALL technical details, variable names, "
                        f"and specific instructions exactly as spoken."
                    )
                    print(f"[context] AI chat detected: {service} (via '{app}')")
                    break

    return ctx


def _get_browser_title(app: str) -> str | None:
    """Get the title of the frontmost browser window via osascript."""
    if not _IS_MACOS:
        return None
    try:
        # Different AppleScript for different browsers
        if app in ("Google Chrome", "Brave Browser", "Microsoft Edge"):
            script = f'tell application "{app}" to get title of active tab of front window'
        elif app == "Safari":
            script = 'tell application "Safari" to get name of current tab of front window'
        elif app == "Arc":
            script = 'tell application "Arc" to get title of active tab of front window'
        elif app == "Firefox":
            # Firefox doesn't expose tabs via AppleScript easily — use window name
            script = 'tell application "System Events" to get name of front window of process "Firefox"'
        else:
            return None

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=2,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def _ai_service_name(url_fragment: str) -> str:
    names = {
        "chatgpt.com":            "ChatGPT",
        "chat.openai.com":        "ChatGPT",
        "claude.ai":              "Claude",
        "perplexity.ai":          "Perplexity",
        "gemini.google.com":      "Gemini",
        "copilot.microsoft.com":  "Microsoft Copilot",
        "you.com":                "You.com",
        "phind.com":              "Phind",
        "poe.com":                "Poe",
        "character.ai":           "Character.AI",
    }
    return names.get(url_fragment, "an AI assistant")


# ── Quick test ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    import json
    ctx = get_active_context()
    print(json.dumps(ctx, indent=2))
