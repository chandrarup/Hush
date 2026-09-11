"""
setup_app.py — py2app configuration for VoiceFlow.
Usage: uv run --group build --extra parakeet python packaging/setup_app.py py2app

Build dependencies are managed by uv. Run the command above from the repository
root after syncing the build group.

NOTE: py2app with PyTorch produces a ~5-8 GB bundle.
This is best used for creating a signed .app for the Mac App Store
or for enterprise distribution. For general public distribution,
use install.sh + packaging/build_dmg.sh instead.
"""
from pathlib import Path

from setuptools import setup

REPO_ROOT = Path(__file__).resolve().parents[1]

APP    = [str(REPO_ROOT / 'main.py')]
DATA   = [
    ('voiceflow/web/ui', [str(REPO_ROOT / 'voiceflow/web/ui/index.html'),
                          str(REPO_ROOT / 'voiceflow/web/ui/onboarding.html')]),
]
OPTIONS = {
    'argv_emulation': False,
    'semi_standalone': False,
    'plist': {
        # App identity
        'CFBundleName':            'VoiceFlow',
        'CFBundleIdentifier':      'com.voiceflow.app',
        'CFBundleVersion':         '1.0.0',
        'CFBundleShortVersionString': '1.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 VoiceFlow',
        # macOS permissions (Info.plist usage descriptions)
        'NSMicrophoneUsageDescription':
            'VoiceFlow needs microphone access to transcribe your speech.',
        'NSAppleEventsUsageDescription':
            'VoiceFlow needs Accessibility access to type text into other apps.',
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
        'numpy', 'transformers',
    ],
    'excludes': ['tkinter', 'test', 'unittest'],
    'strip': True,
}

setup(
    app=APP,
    data_files=DATA,
    options={'py2app': OPTIONS},
    name='VoiceFlow',
    version='1.0.0',
)
