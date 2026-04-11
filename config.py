"""
config.py — Loads ~/.voiceflow/config.toml and provides defaults.
Creates the config file and vocab file if they do not exist.
"""

import os
import sys
import pathlib
import toml

CONFIG_DIR = pathlib.Path.home() / ".voiceflow"
CONFIG_PATH = CONFIG_DIR / "config.toml"
VOCAB_PATH = CONFIG_DIR / "vocab.txt"

DEFAULT_CONFIG = {
    "hotkey": {
        "key": "ctrl_r",
    },
    "asr": {
        # engine: "auto" | "parakeet" | "whisper"
        # auto = Parakeet on Mac (10x faster), Whisper elsewhere
        "engine": "auto",
        "model": "",          # leave empty for engine default
        "language": "en",
        "compute_type_gpu": "float16",
        "compute_type_cpu": "int8",
    },
    "llm": {
        # Tier 1: Your Docker LLM (same setup as AlphaScanner)
        "docker_llm_url":   "http://localhost:12434/engines/llama.cpp/v1",
        "docker_llm_model": "",   # leave empty to auto-detect from /models
        # Tier 2: Ollama fallback
        "ollama_model":     "llama3.2:3b",
        "ollama_base_url":  "http://localhost:11434",
        "temperature": 0.1,
        "max_tokens": 500,
        # Cleanup level: none | light | medium | high
        "cleanup_level": "light",
    },
    "injection": {
        # quartz = native macOS CGEvent (best, no clipboard flash)
        # clipboard = pbcopy + Cmd+V
        # pyautogui = last resort
        # xdotool = Linux
        "method": "quartz" if sys.platform == "darwin" else "xdotool",
    },
    "ui": {
        "show_notification": True,
        "notification_duration": 3,
        "dashboard_port": 57327,
    },
}


def _write_default_config():
    """Write the default config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        toml.dump(DEFAULT_CONFIG, f)
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
