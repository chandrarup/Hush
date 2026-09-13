"""Check the Hush environment without recording or changing permissions."""

import argparse
import importlib
import sys


def check_dependencies():
    modules = ["toml", "numpy", "sounddevice", "webrtcvad", "faster_whisper",
               "requests", "fastapi", "uvicorn", "aiofiles", "PIL", "ollama",
               "plyer", "pyperclip"]
    if sys.platform == "darwin":
        modules.extend(["Quartz", "ApplicationServices"])
    for module in modules:
        importlib.import_module(module)
    # GUI imports can contact the desktop or request permissions during setup.
    for module in ("pynput", "pystray", "pyautogui"):
        importlib.import_module(module)
    import sounddevice
    sounddevice.get_portaudio_version()
    print("Core imports, GUI package presence, and PortAudio passed.")
    print("Microphone, hotkey access, and text injection are not tested.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Create missing config and load the speech model")
    args = parser.parse_args()
    try:
        check_dependencies()
        if args.prepare:
            from voiceflow.config import load_config
            from voiceflow.core.transcriber import create_transcriber
            config = load_config()
            print("Preparing speech recognition. The first run downloads model files.", flush=True)
            transcriber = create_transcriber(**config["asr"])
            print(f"Speech model loaded: {type(transcriber).__name__}")
            del transcriber
    except Exception as exc:
        print(f"Setup check failed: {exc}", file=sys.stderr)
        print("Rerun ./lets-hush. For download errors, check internet access or your agent's network permissions.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
