"""Concrete platform bundles composed from capability adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .backends.generic.context import GenericContext
from .backends.generic.notifications import GenericNotifications
from .backends.generic.permissions import GenericPermissions
from .backends.generic.text_injection import GenericTextInjector
from .backends.linux.context import LinuxContext
from .backends.linux.notifications import LinuxNotifications
from .backends.linux.permissions import LinuxPermissions
from .backends.linux.text_injection import LinuxTextInjector
from .backends.macos.context import MacOSActiveContext
from .backends.macos.notifications import MacOSNotifications
from .backends.macos.permissions import MacOSPermissions
from .backends.macos.recording_hud import MacOSRecordingHUD
from .backends.macos.text_injection import MacOSTextInjector
from .backends.windows.context import WindowsContext
from .backends.windows.notifications import WindowsNotifications
from .backends.windows.permissions import WindowsPermissions
from .backends.windows.text_injection import WindowsTextInjector
from .contracts import PlatformServices

if TYPE_CHECKING:
    from .backends.common.tray import TrayIcon


class _TrayService:
    def __init__(self, tray: TrayIcon) -> None:
        self._tray = tray

    def get_tray(self) -> TrayIcon:
        return self._tray


def _tray_for(permissions, activity_hud=None) -> _TrayService:
    # Importing pystray connects to X11 on Linux, so defer it until the desktop
    # application actually asks for a tray instead of during web API startup.
    from .backends.common.tray import TrayIcon

    return _TrayService(
        TrayIcon(
            open_settings=lambda: permissions.open_system_settings("accessibility"),
            activity_hud=activity_hud,
        )
    )


class MacOSPlatformServices(PlatformServices):
    def __init__(self) -> None:
        permissions = MacOSPermissions()
        super().__init__(
            name="macOS",
            default_injection_method="quartz",
            text=MacOSTextInjector(),
            notifications=MacOSNotifications(),
            context=MacOSActiveContext(),
            tray=_tray_for(permissions, activity_hud=MacOSRecordingHUD()),
            permissions=permissions,
        )


class LinuxPlatformServices(PlatformServices):
    def __init__(self) -> None:
        permissions = LinuxPermissions()
        super().__init__(
            name="Linux",
            default_injection_method="xdotool",
            text=LinuxTextInjector(),
            notifications=LinuxNotifications(),
            context=LinuxContext(),
            tray=_tray_for(permissions),
            permissions=permissions,
        )


class WindowsPlatformServices(PlatformServices):
    def __init__(self) -> None:
        permissions = WindowsPermissions()
        super().__init__(
            name="Windows",
            default_injection_method="clipboard",
            text=WindowsTextInjector(),
            notifications=WindowsNotifications(),
            context=WindowsContext(),
            tray=_tray_for(permissions),
            permissions=permissions,
        )


class GenericPlatformServices(PlatformServices):
    def __init__(self) -> None:
        permissions = GenericPermissions()
        super().__init__(
            name="Generic desktop",
            default_injection_method="clipboard",
            text=GenericTextInjector(),
            notifications=GenericNotifications(),
            context=GenericContext(),
            tray=_tray_for(permissions),
            permissions=permissions,
        )
