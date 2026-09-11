"""Stable interfaces between the application and operating-system adapters."""

from dataclasses import dataclass
from typing import Protocol


class TextService(Protocol):
    def inject_text(self, text: str, preferred_method: str = "quartz") -> bool: ...


class NotificationService(Protocol):
    def show_result(
        self,
        raw_text: str,
        clean_text: str,
        duration_seconds: int = 3,
        enabled: bool = True,
    ) -> None: ...


class ContextService(Protocol):
    def get_active_context(self) -> dict: ...


class TrayService(Protocol):
    def get_tray(self): ...


class PermissionService(Protocol):
    def is_first_launch(self) -> bool: ...
    def check_accessibility_permission(self) -> bool: ...
    def get_all_permissions(self) -> dict: ...
    def mark_onboarded(self) -> None: ...
    def open_system_settings(self, permission_type: str) -> bool: ...

    def print_permission_guide(self) -> None: ...


@dataclass(frozen=True)
class PlatformServices:
    """The platform capabilities consumed by the application layer."""

    name: str
    default_injection_method: str
    text: TextService
    notifications: NotificationService
    context: ContextService
    tray: TrayService
    permissions: PermissionService
