"""Portable context adapter used where active-window metadata is unavailable."""


class NullContext:
    def get_active_context(self) -> dict:
        return {"app": None, "is_ai_chat": False, "hint": None}
