"""Execution seam for local threads and future durable cloud dispatchers."""

from collections.abc import Callable
from typing import Any, Protocol


class JobDispatcher(Protocol):
    """Submit work without exposing the execution mechanism to callers."""

    def dispatch(self, target: Callable[..., Any], *args: Any, **kwargs: Any) -> None: ...


class LocalThreadDispatcher:
    """Run one local job in a daemon thread.

    Cloud adapters can implement the same interface by publishing a durable
    job instead of starting a process-local thread.
    """

    def __init__(self, name: str = "voiceflow-job") -> None:
        self.name = name

    def dispatch(self, target: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        import threading

        threading.Thread(
            target=target,
            args=args,
            kwargs=kwargs,
            daemon=True,
            name=self.name,
        ).start()
