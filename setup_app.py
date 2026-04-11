"""
setup_app.py — py2app configuration for VoiceFlow.
Usage: python setup_app.py py2app

NOTE: py2app with PyTorch produces a ~5-8 GB bundle.
This is best used for creating a signed .app for the Mac App Store
or for enterprise distribution. For general public distribution,
use install.sh + build_dmg.sh instead.
"""
from setuptools import setup
import sys

APP    = ['main.py']
DATA   = [
    ('ui',     ['ui/index.html', 'ui/onboarding.html']),
    ('',       ['config.py', 'history.py', 'api_server.py',
                'onboarding.py', 'cleaner.py', 'transcriber.py',
                'audio.py', 'vad.py', 'injector.py', 'context.py',
                'tray.py', 'notifier.py']),
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
    setup_requires=['py2app'],
    name='VoiceFlow',
    version='1.0.0',
)
