"""macOS active-application context adapter."""

from __future__ import annotations

import subprocess
import time


AI_CHAT_URLS = {
    "chatgpt.com": "ChatGPT",
    "chat.openai.com": "ChatGPT",
    "claude.ai": "Claude",
    "perplexity.ai": "Perplexity",
    "gemini.google.com": "Gemini",
    "copilot.microsoft.com": "Microsoft Copilot",
    "you.com": "You.com",
    "phind.com": "Phind",
    "poe.com": "Poe",
    "character.ai": "Character.AI",
}
BROWSER_APPS = {"Google Chrome", "Safari", "Firefox", "Arc", "Brave Browser", "Microsoft Edge"}


class MacOSActiveContext:
    def __init__(self) -> None:
        self._cached_app = None
        self._cached_at = 0.0

    def get_active_context(self) -> dict:
        app = self._active_app()
        context = {"app": app, "is_ai_chat": False, "hint": None}
        if app in BROWSER_APPS:
            title = self._browser_title(app)
            service = self._find_ai_service(title)
            if service:
                context.update(
                    is_ai_chat=True,
                    hint=(
                        f"The user is typing a prompt into {service}. Write it as a clear, "
                        "well-structured prompt. Preserve all technical details, variable "
                        "names, and specific instructions exactly as spoken."
                    ),
                )
        return context

    def _active_app(self) -> str | None:
        now = time.monotonic()
        if self._cached_app and now - self._cached_at < 0.5:
            return self._cached_app
        script = 'tell application "System Events" to get name of first process whose frontmost is true'
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
            app = result.stdout.strip()
            if app:
                self._cached_app, self._cached_at = app, now
                return app
        except Exception as exc:
            print(f"[context] Could not detect active app: {exc}")
        return None

    @staticmethod
    def _browser_title(app: str) -> str | None:
        scripts = {
            "Google Chrome": f'tell application "{app}" to get title of active tab of front window',
            "Brave Browser": f'tell application "{app}" to get title of active tab of front window',
            "Microsoft Edge": f'tell application "{app}" to get title of active tab of front window',
            "Safari": 'tell application "Safari" to get name of current tab of front window',
            "Arc": 'tell application "Arc" to get title of active tab of front window',
            "Firefox": 'tell application "System Events" to get name of front window of process "Firefox"',
        }
        try:
            result = subprocess.run(["osascript", "-e", scripts[app]], capture_output=True, text=True, timeout=2)
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    @staticmethod
    def _find_ai_service(title: str | None) -> str | None:
        lowered = (title or "").lower()
        return next((service for url, service in AI_CHAT_URLS.items() if url in lowered), None)
