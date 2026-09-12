"""Configuration loading, defaults, and application-owned paths."""

from .loader import CONFIG_DIR, CONFIG_PATH, VOCAB_PATH, load_config, load_vocab
from .paths import DATA_DIR, HISTORY_DB_PATH, PROJECT_ROOT
from .snippets import SNIPPETS_PATH, add_snippet, load_snippets, remove_snippet

__all__ = [
    "CONFIG_DIR",
    "CONFIG_PATH",
    "DATA_DIR",
    "HISTORY_DB_PATH",
    "PROJECT_ROOT",
    "SNIPPETS_PATH",
    "VOCAB_PATH",
    "add_snippet",
    "load_config",
    "load_vocab",
    "load_snippets",
    "remove_snippet",
]
