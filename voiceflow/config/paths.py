"""Application-owned filesystem paths.

VoiceFlow keeps user preferences under ``~/.voiceflow`` but stores the local
transcription history alongside the checkout in ``data/history.db``. Keeping
these paths in one module prevents runtime modules from constructing paths
independently or depending on the caller's current working directory.
"""

from pathlib import Path


# voiceflow/config/paths.py -> repository root (Hush/).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
HISTORY_DB_PATH = DATA_DIR / "history.db"
