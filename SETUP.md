# VoiceFlow Setup Guide

This file is the full setup checklist for running VoiceFlow on a new machine.
It includes the macOS privacy permissions that are easy to miss during a normal
`pip install`.

VoiceFlow needs three separate things to work:

- Input Monitoring: lets the app detect the push-to-talk hotkey.
- Microphone: lets the app record audio.
- Accessibility: lets the app paste/type the final transcript into the focused app.

After changing any macOS privacy setting, quit the running VoiceFlow process and
restart it. macOS usually does not apply these permissions to an already-running
Python process.

## 1. Clone The Repository

```bash
git clone https://github.com/chandrarup/Hush.git
cd Hush
```

## Agent Setup Notes

Claude, Codex, or another coding agent can perform the file, venv, dependency,
config, model-download, and verification steps in this guide. In sandboxed agent
environments, PyPI, Hugging Face, and Ollama access may require explicit network
approval. DNS errors while installing packages or loading Parakeet usually mean
network access is blocked, not that the dependency list is wrong.

macOS privacy settings are the main manual step. A user must approve Input
Monitoring, Accessibility, and Microphone access in System Settings; an agent can
only print the exact paths to add and run diagnostics afterward.

## 2. Install System Dependencies

### macOS

Install Homebrew first if needed: https://brew.sh

```bash
brew install portaudio ollama python@3.12
```

`portaudio` is required by `sounddevice`. `ollama` is used for local transcript
cleanup. Python 3.12 is a good known-working runtime for this project.

### Linux

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-dev gcc portaudio19-dev xdotool libnotify-bin python3-tk
curl -fsSL https://ollama.com/install.sh | sh
```

## 3. Create The Python Environment

On macOS, prefer Python 3.12 if available:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Notes:

- `librosa` is required for the Parakeet ASR path used on Apple Silicon.
- `setuptools<81` is required because `webrtcvad` still imports `pkg_resources`.
- `pytest` is included so the repository smoke tests work after setup.

## 4. Set Up Ollama

Start Ollama:

```bash
ollama serve
```

In a second terminal, pull the cleanup model:

```bash
ollama pull llama3.2:3b
```

VoiceFlow can still run without Ollama, but it will inject raw ASR text instead
of cleaned text.

## 5. Create VoiceFlow Config Files

The app creates `~/.voiceflow/config.toml` and `~/.voiceflow/vocab.txt` on first
startup. To create them without launching the whole app:

```bash
source .venv/bin/activate
python -c 'from config import load_config; load_config()'
```

The current macOS defaults should include:

```toml
[hotkey]
key = "ctrl_r"

[asr]
engine = "auto"

[injection]
method = "quartz"
```

## 6. macOS Privacy Permissions

Open:

```text
System Settings -> Privacy & Security
```

You may need to unlock settings or enter your password before adding apps.

### Input Monitoring

Go to:

```text
System Settings -> Privacy & Security -> Input Monitoring
```

Add and enable the process that launches VoiceFlow:

- Terminal, if you run `python main.py` from Terminal.
- ChatGPT or Codex, if you run it from the ChatGPT/Codex app terminal.
- Python.app, if macOS checks the Python framework process directly.

If the `.venv/bin/python` files are greyed out in the picker, that is normal:
they are symlinks. Use the real Python app bundle instead.

First print the exact paths macOS is checking:

```bash
source .venv/bin/activate
python check_permission.py
```

Look for:

```text
sys.executable
Resolved real path
```

For Homebrew Python 3.12 on Apple Silicon, the selectable app is usually here:

```text
/opt/homebrew/Cellar/python@3.12/3.12.13_2/Frameworks/Python.framework/Versions/3.12/Resources/Python.app
```

In the macOS file picker:

1. Click `+`.
2. Press `Cmd+Shift+G`.
3. Paste the parent folder:

```text
/opt/homebrew/Cellar/python@3.12/3.12.13_2/Frameworks/Python.framework/Versions/3.12/Resources
```

4. Select `Python.app`.
5. Turn the toggle on.

If the Homebrew Python version is different, use the `Resolved real path` from
`check_permission.py`, then go to that Python framework's `Resources` folder and
select `Python.app`.

### Accessibility

Go to:

```text
System Settings -> Privacy & Security -> Accessibility
```

Add and enable the same launcher(s):

- Terminal or ChatGPT/Codex, depending on where you run VoiceFlow.
- Python.app, using the same `Resources/Python.app` path above if needed.

Accessibility is required for Quartz text injection. Without it, transcription
may work, but the final text may not appear in the focused app.

### Microphone

Go to:

```text
System Settings -> Privacy & Security -> Microphone
```

Enable Terminal, ChatGPT/Codex, or Python.app if macOS prompts for microphone
access. The permission usually appears after the first attempt to record.

## 7. Verify Permissions And Hotkey Events

Run:

```bash
source .venv/bin/activate
python diag_hotkey.py
```

Press the Control key and a few other keys.

Good output looks like this:

```text
[diag] PRESS   <Key.ctrl: <59>>
[diag] PRESS   'c'
```

If `IS_TRUSTED = False` appears but `PRESS` and `RELEASE` lines still appear,
`pynput` is receiving events and the hotkey path can work.

If no `PRESS` or `RELEASE` lines appear, Input Monitoring is still missing for
the actual running process. Add Terminal, ChatGPT/Codex, and Python.app as
described above, then quit and restart the terminal/app.

Keyboard note: some macOS keyboards report Control as generic `Key.ctrl` instead
of `Key.ctrl_r`. The app treats `ctrl`, `ctrl_l`, and `ctrl_r` as equivalent.

## 8. Verify ASR Dependencies

Parakeet on Apple Silicon:

```bash
source .venv/bin/activate
python -c 'from transcriber import create_transcriber; t=create_transcriber(engine="parakeet"); print(type(t).__name__)'
```

Expected:

```text
ParakeetTranscriber
```

The first run may download model files from Hugging Face and cache them under
`~/.cache/huggingface/`.

If Parakeet cannot start, the app falls back to Whisper:

```bash
python -c 'from transcriber import create_transcriber; t=create_transcriber(engine="whisper"); print(type(t).__name__)'
```

## 9. Run Tests

```bash
source .venv/bin/activate
python -m pytest
```

Expected:

```text
2 passed
```

## 10. Launch VoiceFlow

```bash
source .venv/bin/activate
python main.py
```

Expected startup signs:

```text
[transcriber] Auto-selected engine: parakeet
[main] Hotkey : ctrl_r
[main] Dashboard : http://localhost:57327
[main] Ready - hold hotkey to record, release to transcribe.
```

Hold Control, speak, then release. The terminal should show:

```text
[main] STARTED
[main] STOPPED - running pipeline...
```

Then the app should transcribe and inject text into the focused input field.

## 11. Troubleshooting

### Hotkey Does Nothing

Run:

```bash
python diag_hotkey.py
```

If no key events appear, fix Input Monitoring. Add Terminal, ChatGPT/Codex, and
Python.app, then fully quit and reopen the launcher.

If key events appear but recording does not start, check `~/.voiceflow/config.toml`
and try a simpler hotkey:

```toml
[hotkey]
key = "ctrl"
```

### It Records But Does Not Type Into Other Apps

Fix Accessibility. Add the same launcher and Python.app under:

```text
System Settings -> Privacy & Security -> Accessibility
```

Also make sure the text field you want to type into is focused before releasing
the hotkey.

### It Does Not Ask For Microphone Permission

Run the app from the same launcher you granted permissions to, then press the
hotkey long enough to start recording. If macOS still does not prompt, manually
check:

```text
System Settings -> Privacy & Security -> Microphone
```

### Parakeet Falls Back To Whisper

Install dependencies again:

```bash
python -m pip install -r requirements.txt
```

Then run:

```bash
python -c 'import librosa; print(librosa.__version__)'
```

If model files are missing, rerun the Parakeet check from section 8 with network
access.

### `webrtcvad` Warns About `pkg_resources`

This project pins `setuptools<81` because `webrtcvad` imports `pkg_resources`.
Reinstall requirements if the warning becomes an import error:

```bash
python -m pip install -r requirements.txt
```

### Ollama Is Unreachable

Start Ollama:

```bash
ollama serve
```

Verify the model exists:

```bash
ollama list
```

If `llama3.2:3b` is missing:

```bash
ollama pull llama3.2:3b
```

### Avoiding Login Autostart

`install.sh` creates a LaunchAgent so VoiceFlow starts at login. For a manual
developer setup, use the venv commands in this file instead of `install.sh`.
