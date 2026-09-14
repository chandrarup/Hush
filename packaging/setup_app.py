"""py2app configuration for the self-contained Hush macOS application."""
import os
from pathlib import Path
import sys

from setuptools import setup

REPO_ROOT = Path(__file__).resolve().parents[1]

# Modulegraph walks optional transformer imports deeply on Python 3.12.
sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))

APP_NAME = "Hush"
BUNDLE_ID = "com.chandrarup.hush"
VERSION = os.environ.get("HUSH_VERSION", "1.0.0").removeprefix("v")

APP = [str(REPO_ROOT / "main.py")]
DATA = [
    ("ui", [
        str(REPO_ROOT / "voiceflow/web/ui/index.html"),
        str(REPO_ROOT / "voiceflow/web/ui/onboarding.html"),
    ]),
]
OPTIONS = {
    'argv_emulation': False,
    'semi_standalone': False,
    'iconfile': str(REPO_ROOT / 'assets/HushIcon.icns'),
    'plist': {
        # App identity
        'CFBundleName':            APP_NAME,
        'CFBundleDisplayName':     APP_NAME,
        'CFBundleIdentifier':      BUNDLE_ID,
        'CFBundleVersion':         VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHumanReadableCopyright': 'Copyright © 2026 Hush',
        # macOS permissions (Info.plist usage descriptions)
        'NSMicrophoneUsageDescription':
            'Hush needs microphone access to transcribe your speech.',
        'NSAppleEventsUsageDescription':
            'Hush uses System Events only to paste your approved dictation into the active app.',
        # Hide from Dock (runs as menu bar app only)
        'LSUIElement': True,
        'LSBackgroundOnly': False,
        # Minimum macOS version
        'LSMinimumSystemVersion': '12.0',
    },
    'packages': [
        'fastapi', 'uvicorn', 'starlette', 'anyio',
        'voiceflow', 'voiceflow.app', 'voiceflow.core',
        'voiceflow.config', 'voiceflow.prompts',
        'voiceflow.platform', 'voiceflow.platform.backends',
        'voiceflow.platform.backends.common', 'voiceflow.platform.backends.macos',
        'voiceflow.platform.backends.linux', 'voiceflow.platform.backends.windows',
        'voiceflow.platform.backends.generic',
        'voiceflow.web', 'voiceflow.diagnostics',
        'faster_whisper', 'sounddevice', '_sounddevice_data',
        'pynput', 'ollama', 'requests', 'toml',
        'pystray', 'PIL', 'plyer',
        'numpy', 'AVFoundation', 'ApplicationServices', 'Quartz',
    ],
    # The first distributable app uses faster-whisper. Keeping the optional
    # Parakeet/Torch stack out avoids a multi-gigabyte bundle and lets its
    # conditional import fall back to Whisper at runtime.
    'excludes': [
        'tkinter', 'test', 'unittest',
        'torch', 'torchvision', 'torchaudio', 'transformers', 'librosa',
    ],
    'strip': True,
}

setup(
    app=APP,
    data_files=DATA,
    options={'py2app': OPTIONS},
    name=APP_NAME,
    version=VERSION,
)
