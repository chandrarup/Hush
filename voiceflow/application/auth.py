"""Authentication seam for hosted application adapters."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Principal:
    """Verified identity supplied by an authentication adapter."""

    subject: str


class Authenticator(Protocol):
    """Resolve request headers to a verified principal or reject them."""

    def authenticate(self, headers: Mapping[str, str]) -> Principal | None: ...
