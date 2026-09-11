"""Windows context adapter."""

from ..common.context import NullContext


class WindowsContext(NullContext):
    """Portable context fallback for Windows."""
