"""Canonical paths for source runs and packaged macOS installations."""

from pathlib import Path

from voiceflow.runtime import is_packaged_macos_app, user_data_dir


# ``voiceflow/config/paths.py`` lives two levels below the repository root.
# Keeping this resolution in one module prevents individual components from
# silently writing user data to different locations.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = user_data_dir() if is_packaged_macos_app() else PROJECT_ROOT / "data"

CONFIG_DIR = DATA_DIR
CONFIG_PATH = DATA_DIR / "config.toml"
VOCAB_PATH = DATA_DIR / "vocab.txt"
SNIPPETS_PATH = DATA_DIR / "snippets.toml"
HISTORY_DB_PATH = DATA_DIR / "history.db"
ONBOARDED_PATH = DATA_DIR / ".onboarded"
LOG_PATH = DATA_DIR / "hush.log"

LEGACY_DATA_DIR = Path.home() / ".voiceflow"
LEGACY_BACKUP_DIR = DATA_DIR / ".legacy"
