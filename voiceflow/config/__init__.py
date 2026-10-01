"""Configuration loading, project-local paths, and default values."""

from .loader import (
    CONFIG_DIR,
    CONFIG_PATH,
    VOCAB_PATH,
    load_config,
    load_vocab,
    persist_cloud_client_id,
)
from .paths import DATA_DIR, HISTORY_DB_PATH, ONBOARDED_PATH, PROJECT_ROOT
from .snippets import (
    SNIPPETS_PATH,
    add_snippet,
    get_snippets_snapshot,
    load_snippets,
    remove_snippet,
    update_snippet,
)

__all__ = [
    "CONFIG_DIR",
    "CONFIG_PATH",
    "DATA_DIR",
    "HISTORY_DB_PATH",
    "ONBOARDED_PATH",
    "PROJECT_ROOT",
    "SNIPPETS_PATH",
    "VOCAB_PATH",
    "add_snippet",
    "get_snippets_snapshot",
    "load_config",
    "load_snippets",
    "load_vocab",
    "persist_cloud_client_id",
    "remove_snippet",
    "update_snippet",
]
