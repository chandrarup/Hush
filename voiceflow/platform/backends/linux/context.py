"""Linux context adapter."""

from ..common.context import NullContext


class LinuxContext(NullContext):
    """Safe fallback until an X11/Wayland window integration is configured."""
