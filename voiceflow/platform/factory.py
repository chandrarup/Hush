"""Factory for routing operating-system capabilities to backend bundles."""

import platform as _platform
import threading

from .adapters import GenericPlatformServices, LinuxPlatformServices, MacOSPlatformServices, WindowsPlatformServices
from .contracts import PlatformServices


_PLATFORM_BUILDERS = {
    "Darwin": MacOSPlatformServices,
    "Linux": LinuxPlatformServices,
    "Windows": WindowsPlatformServices,
}
_services: PlatformServices | None = None
_lock = threading.Lock()


def create_platform_services(system_name: str | None = None) -> PlatformServices:
    """Create a platform bundle without leaking OS checks to callers."""
    name = system_name or _platform.system()
    builder = _PLATFORM_BUILDERS.get(name, GenericPlatformServices)
    return builder()


def get_platform_services() -> PlatformServices:
    """Return the process-wide platform service bundle."""
    global _services
    if _services is None:
        with _lock:
            if _services is None:
                _services = create_platform_services()
    return _services
