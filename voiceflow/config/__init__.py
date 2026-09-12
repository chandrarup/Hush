"""Configuration loading, defaults, and application-owned paths."""

from .loader import CONFIG_DIR, CONFIG_PATH, VOCAB_PATH, load_config, load_vocab
from .paths import DATA_DIR, HISTORY_DB_PATH, PROJECT_ROOT

__all__ = [
    "CONFIG_DIR",
    "CONFIG_PATH",
    "DATA_DIR",
    "HISTORY_DB_PATH",
    "PROJECT_ROOT",
    "VOCAB_PATH",
    "load_config",
    "load_vocab",
]
