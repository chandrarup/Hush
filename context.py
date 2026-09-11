"""
context.py — Detect the active macOS application.

Latency fix: app detection is now done in a background thread that polls
every 300 ms.  get_active_context() reads from the cache and NEVER blocks
the hotkey handler (previously could block up to 2 s on osascript timeout).

Used to give the LLM context about WHERE the user is typing so the output
is formatted correctly for that app.

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
import threading

_IS_MACOS = sys.platform == "darwin"

# ── Background watcher state ─────────────────────────────────────── #
_context_cache: dict = {"app": None, "is_ai_chat": False, "hint": None}
_context_lock = threading.Lock()
_watcher_started = False


def start_context_watcher(interval: float = 0.3) -> None:
    """
    Start a background daemon thread that polls the active app every
    `interval` seconds and stores the result in a thread-safe cache.

    After calling this once at startup, get_active_context() returns
    instantly from the cache — it never calls osascript in the hotkey path.
    """
    global _watcher_started
    if _watcher_started:
        return
    _watcher_started = True

    def _watcher():
        while True:
            ctx = _get_active_context_blocking()
            with _context_lock:
                _context_cache.update(ctx)
            time.sleep(interval)

    t = threading.Thread(target=_watcher, daemon=True, name="ctx-watcher")
    t.start()
    print(f"[context] ✓ Background app watcher started (polling every {interval:.0f}s)")


def get_active_context() -> dict:
    """
    Return the latest cached active-app context.  Never blocks — safe to
    call directly from the hotkey handler.

    Returns dict with keys: app, is_ai_chat, hint
    """
    with _context_lock:
        return dict(_context_cache)


# ── Blocking implementation (runs only in the background thread) ──── #

def _get_active_app_blocking() -> "str | None":
    """
    Call osascript to get the frontmost app name.
    May take up to 2 s — only called from the background watcher thread,
    never from the hotkey handler.
    """
    if not _IS_MACOS:
        return None
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
        return app if app else None
    except Exception as e:
        print(f"[context] Could not detect active app: {e}")
        return None


AI_CHAT_URLS = [
    "chatgpt.com", "chat.openai.com",
    "claude.ai",
    "perplexity.ai",
    "gemini.google.com",
    "copilot.microsoft.com",
    "you.com", "phind.com", "poe.com",
    "character.ai",
]

BROWSER_APPS = {
    "Google Chrome", "Safari", "Firefox",
    "Arc", "Brave Browser", "Microsoft Edge",
}


def _get_active_context_blocking() -> dict:
    """
    Full blocking context detection.  Only called from the watcher thread.
    """
    app = _get_active_app_blocking()
    ctx: dict = {"app": app, "is_ai_chat": False, "hint": None}

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
                    break

    return ctx


def _get_browser_title(app: str) -> "str | None":
    if not _IS_MACOS:
        return None
    try:
        if app in ("Google Chrome", "Brave Browser", "Microsoft Edge"):
            script = f'tell application "{app}" to get title of active tab of front window'
        elif app == "Safari":
            script = 'tell application "Safari" to get name of current tab of front window'
        elif app == "Arc":
            script = 'tell application "Arc" to get title of active tab of front window'
        elif app == "Firefox":
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
        "chatgpt.com": "ChatGPT", "chat.openai.com": "ChatGPT",
        "claude.ai": "Claude",
        "perplexity.ai": "Perplexity",
        "gemini.google.com": "Gemini",
        "copilot.microsoft.com": "Microsoft Copilot",
        "you.com": "You.com", "phind.com": "Phind",
        "poe.com": "Poe", "character.ai": "Character.AI",
    }
    return names.get(url_fragment, "an AI assistant")


# ── Quick test ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    import json
    ctx = _get_active_context_blocking()
    print(json.dumps(ctx, indent=2))
