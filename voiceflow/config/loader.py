"""
config.py - Loads ~/.voiceflow/config.toml and provides defaults.
Creates the config file and vocab file if they do not exist.
"""

import os
import pathlib
import tempfile
import toml

from .defaults import DEFAULT_CONFIG

CONFIG_DIR = pathlib.Path.home() / ".voiceflow"
CONFIG_PATH = CONFIG_DIR / "config.toml"
VOCAB_PATH = CONFIG_DIR / "vocab.txt"

def _write_default_config():
    """Write the default config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _write_toml_atomically(DEFAULT_CONFIG)
    print(f"[config] Created default config at {CONFIG_PATH}")


def _ensure_vocab():
    """Create an empty vocab file if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not VOCAB_PATH.exists():
        VOCAB_PATH.touch()
        print(f"[config] Created empty vocab file at {VOCAB_PATH}")


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config() -> dict:
    """
    Load configuration from ~/.voiceflow/config.toml.
    Creates the file with defaults if it does not exist.
    Returns a fully-populated config dict (missing keys filled from defaults).
    """
    _ensure_vocab()

    if not CONFIG_PATH.exists():
        _write_default_config()
        return dict(DEFAULT_CONFIG)

    try:
        user_cfg = toml.load(CONFIG_PATH)
        # Deep-merge so missing keys fall back to defaults
        merged = _deep_merge(DEFAULT_CONFIG, user_cfg)
        print(f"[config] Loaded config from {CONFIG_PATH}")
        return merged
    except Exception as e:
        print(f"[config] WARNING: Failed to parse config ({e}). Using defaults.")
        return dict(DEFAULT_CONFIG)


def load_vocab() -> list[str]:
    """
    Load personal vocabulary from ~/.voiceflow/vocab.txt.
    Returns a list of non-empty, stripped strings.
    """
    _ensure_vocab()
    try:
        lines = VOCAB_PATH.read_text(encoding="utf-8").splitlines()
        vocab = [line.strip() for line in lines if line.strip()]
        if vocab:
            print(f"[config] Loaded {len(vocab)} vocab entries from {VOCAB_PATH}")
        return vocab
    except Exception as e:
        print(f"[config] WARNING: Could not read vocab file ({e}).")
        return []


def update_config_value(section: str, key: str, value) -> None:
    """Persist one user setting without making callers manage TOML files."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = toml.load(str(CONFIG_PATH)) if CONFIG_PATH.exists() else {}
    config.setdefault(section, {})[key] = value
    _write_toml_atomically(config)


def _write_toml_atomically(config: dict) -> None:
    """Write TOML beside the destination, then replace it atomically."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp_path: str | None = None
    file_descriptor, temp_path = tempfile.mkstemp(
        dir=CONFIG_DIR,
        prefix=f".{CONFIG_PATH.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            toml.dump(config, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, CONFIG_PATH)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
