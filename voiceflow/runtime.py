"""Runtime paths and environment setup for source and packaged Hush builds."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path


APP_NAME = "Hush"


def is_packaged_macos_app() -> bool:
    """Return whether this process is running from a frozen macOS app bundle."""
    return platform.system() == "Darwin" and bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    """Keep packaged-app state outside the signed application bundle."""
    if is_packaged_macos_app():
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".voiceflow"


def configure_runtime_environment() -> None:
    """Direct downloaded model data to user-owned storage for packaged builds."""
    if not is_packaged_macos_app():
        return

    models_dir = user_data_dir() / "Models"
    models_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(models_dir))
