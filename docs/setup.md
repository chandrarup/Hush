# VoiceFlow Setup Guide

This file is the full setup checklist for running VoiceFlow on a new machine.
It includes the macOS privacy permissions that are easy to miss during a normal
application dependency setup.

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

Install uv before creating the application environment. It is the only Python
environment/dependency tool used by this repository.

### uv

```bash
# macOS with Homebrew
brew install uv

# Linux or other supported platforms
curl -LsSf https://astral.sh/uv/install.sh | sh
```

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
sudo apt-get install -y python3-dev gcc portaudio19-dev xdotool libnotify-bin python3-tk
curl -fsSL https://ollama.com/install.sh | sh
```

## 3. Create The Python Environment With uv

`pyproject.toml` is the source of truth for the VoiceFlow application. It keeps
runtime, optional Parakeet, development, and packaging dependencies separate.
`tool.uv.package = false` intentionally tells uv that this is an executable
application, not a library that should be installed into site-packages.

On macOS, prefer Python 3.12 if available:

```bash
uv venv --python 3.12 .venv
uv sync --extra parakeet --no-dev
```

On Linux:

```bash
uv sync --no-dev
```

Notes:

- `uv sync` creates or updates `.venv` and installs the exact versions recorded
  in `uv.lock`; no manual activation is required when using `uv run`.
- `librosa` (0.10.x/0.11.x) is required for the Parakeet ASR path used on Apple
  Silicon.
- `setuptools<81` is required because `webrtcvad` still imports `pkg_resources`.
- The `dev` dependency group contains pytest and is installed only for tests.
- The `build` dependency group contains py2app and is installed only when
  creating a macOS application bundle.

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
uv run --no-dev python -c 'from voiceflow.config import load_config; load_config()'
```

The current macOS defaults should include:

```toml
[hotkey]
key = "ctrl_r"

[asr]
engine = "auto"

[injection]
method = "auto"
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

- Terminal, if you run `python -m voiceflow.app.main` from Terminal.
- ChatGPT or Codex, if you run it from the ChatGPT/Codex app terminal.
- Python.app, if macOS checks the Python framework process directly.

If the `.venv/bin/python` files are greyed out in the picker, that is normal:
they are symlinks. Use the real Python app bundle instead.

Print the exact instructions and the Python.app folder for this specific Mac:

```bash
./lets-hush --permissions
```

The command first explains how to add Terminal.app from the fixed folder
`/System/Applications/Utilities`. It then finds the selectable Python.app behind
the project's virtual environment and prints its parent folder. Do not guess or
copy a Homebrew path from this guide: the version and location vary by Mac.

In the macOS file picker:

1. Click `+`.
2. Press `Cmd+Shift+G`.
3. Paste the exact Python.app parent folder printed by `./lets-hush --permissions`.

4. Select `Python.app`.
5. Turn the toggle on.

If no Python.app path is printed, allow the app you use to start Hush first
(Terminal, Codex, ChatGPT, VS Code, or iTerm). Do not try to select the greyed-out
`.venv/bin/python` files.

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
uv run --no-dev python -m voiceflow.diagnostics.hotkey_diagnostic
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
uv run --no-dev --extra parakeet python -c 'from voiceflow.core.transcriber import create_transcriber; t=create_transcriber(engine="parakeet"); print(type(t).__name__)'
```

Expected:

```text
ParakeetTranscriber
```

The first run may download model files from Hugging Face and cache them under
`~/.cache/huggingface/`.

If Parakeet cannot start, the app falls back to Whisper:

```bash
uv run --no-dev python -c 'from voiceflow.core.transcriber import create_transcriber; t=create_transcriber(engine="whisper"); print(type(t).__name__)'
```

## 9. Run Tests

```bash
uv run --group dev pytest
```

Expected:

```text
3 passed
```

## 10. Launch VoiceFlow

```bash
uv run --no-dev python -m voiceflow.app.main
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
uv run --no-dev python -m voiceflow.diagnostics.hotkey_diagnostic
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

Synchronize the optional ASR dependencies again:

```bash
uv sync --extra parakeet --no-dev
```

Then run:

```bash
uv run --no-dev --extra parakeet python -c 'import librosa; print(librosa.__version__)'
```

If model files are missing, rerun the Parakeet check from section 8 with network
access.

### `webrtcvad` Warns About `pkg_resources`

This project pins `setuptools<81` because `webrtcvad` imports `pkg_resources`.
Synchronize the locked environment if the warning becomes an import error:

```bash
uv sync --no-dev
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
