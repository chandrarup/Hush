"""Portable text injection fallback."""

from ..common.clipboard import paste_with_gui, print_injection_failure


class GenericTextInjector:
    def inject_text(self, text: str, preferred_method: str = "auto") -> bool:
        if not text or not text.strip():
            return False
        if paste_with_gui(text.strip(), "ctrl+v"):
            return True
        return print_injection_failure()
