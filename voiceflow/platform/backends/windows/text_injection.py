"""Windows text injection adapter."""

from ..common.clipboard import paste_with_gui, print_injection_failure


class WindowsTextInjector:
    """Use the Windows clipboard and Ctrl+V through pyautogui."""

    def inject_text(self, text: str, preferred_method: str = "auto") -> bool:
        if not text or not text.strip():
            return False
        if paste_with_gui(text.strip(), "ctrl+v"):
            return True
        return print_injection_failure()
