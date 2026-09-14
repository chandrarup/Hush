# VoiceFlow

**Local push-to-talk speech-to-text dictation — a Wispr Flow replica using 100% open-source tools.**

Hold a hotkey → speak → release → polished text appears wherever your cursor is.
No cloud APIs. No subscriptions. No data leaves your machine.

---

## What it does

1. **Hold** Left Control (configurable) - microphone starts recording
2. **Speak** anything naturally (filler words, false starts, all fine)
3. **Release** the hotkey — pipeline runs automatically:
   - Voice Activity Detection trims silence
   - Whisper (`large-v3-turbo`) transcribes your speech
   - Llama 3.2 (via Ollama) removes filler words, fixes grammar, resolves self-corrections
   - Clean text is injected directly into whatever text field is focused
4. A floating notification shows raw vs. cleaned text for 3 seconds

**Example:**
> You say: *"um so I was thinking like maybe we should uh meet at 4pm actually no 3pm works better"*
> Text injected: `I was thinking maybe we should meet at 3pm.`

---

## Install Hush.app on macOS

This is the recommended path for people who want to use Hush, not develop it.
It does not require Python, `uv`, a virtual environment, Terminal permission,
or a manually selected executable path.

1. Download `Hush-<version>.dmg` from the GitHub Release.
2. Open it and drag **Hush** to **Applications**.
3. Eject the DMG, then open **Hush** from Applications. Hush opens its local
   dashboard in your browser.
4. Choose **Allow** for Microphone, then choose **Enable** for Accessibility
   and turn on **Hush** in the System Settings page that macOS opens.

Input Monitoring is not a required setup step for the free Hush build. macOS
does not reliably list an unsigned app in that pane, while Accessibility covers
the event-listening and text-insertion path Hush uses. If the hotkey works, the
setup is complete. Do not add Terminal or Python to any privacy list for the
installed app.

See [the macOS app guide](docs/MACOS_APP_RELEASE.md) for the complete install,
reinstall, and troubleshooting flow.

---

## Source Requirements

| Component | Purpose |
|-----------|---------|
| Python 3.10+ | Runtime |
| [uv](https://docs.astral.sh/uv/) | Application environment and dependency manager |
| [Ollama](https://ollama.com) | Local LLM server |
| PortAudio | Audio I/O backend |
| librosa (Parakeet extra) | Required for Parakeet ASR on Apple Silicon |
| xdotool (Linux) | Text injection |

---

## Run From Source

These instructions are for a repository checkout. They create a local Python
environment and have different macOS permission requirements from the installed
app. See [docs/setup.md](docs/setup.md) for the complete source setup and
diagnostic guide.

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
# or download from https://ollama.com/download
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Start the Ollama server (keep this running in the background):
```bash
ollama serve
```

### 2. Install uv

VoiceFlow uses [uv](https://docs.astral.sh/uv/) to manage its application
environment. Install it once if it is not already available:

```bash
# macOS with Homebrew
brew install uv

# Linux or other supported platforms
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Run the installer

On macOS, use the beginner-friendly project launcher. It runs the installer and
then lets you reopen the exact permission instructions for your machine:

```bash
./lets-hush
```

After setup, use `./lets-hush --permissions` for source-run permission
instructions on this Mac. Use `./lets-hush --start` to launch Hush.

For Ubuntu/Debian, the equivalent cross-platform helper is:

```bash
bash scripts/setup_cross_platform.sh
```

Both setup paths use `uv` to create or update the application environment,
create the project-local `data/` files, and prepare the local LLM. The macOS installer
is the recommended path for this repository.

### 4. Launch VoiceFlow

```bash
uv run --no-dev python -m voiceflow.app.main
```

On first launch, Whisper will download the `large-v3-turbo` model (~1.5 GB). This only happens once; it is cached in `~/.cache/huggingface/`.

---

## Manual Installation (without an installer)

```bash
# macOS
brew install portaudio

# Ubuntu/Debian
sudo apt-get install portaudio19-dev xdotool libnotify-bin

# Install uv once if needed: https://docs.astral.sh/uv/getting-started/installation/

# Python application dependencies
# macOS: include the Parakeet accelerator path
uv sync --extra parakeet --no-dev
# Linux/Windows: Whisper-only default
# uv sync --no-dev

# Ollama model
ollama pull llama3.2:3b
```

---

## Configuration

Edit `data/config.toml`:

```toml
[hotkey]
key = "ctrl_l"        # Left Control - change to "ctrl", "f9", "alt_r", etc.

[asr]
engine = "auto"            # auto | parakeet | whisper
model = ""                 # leave empty for engine default
language = "en"            # Transcription language code
compute_type_gpu = "float16"
compute_type_cpu = "int8"

[llm]
docker_llm_url = "http://localhost:12434/engines/llama.cpp/v1"
docker_llm_model = ""
ollama_model = "llama3.2:3b"
ollama_base_url = "http://localhost:11434"
cleanup_level = "light"    # none | light | medium | high
temperature = 0.1
max_tokens = 500

[injection]
method = "auto"            # auto | quartz | clipboard | pyautogui | xdotool

[ui]
show_notification = true
notification_duration = 3
dashboard_port = 57327
```

### ASR engine options

| Engine | Best for | Notes |
|--------|----------|-------|
| `auto` | Recommended | Uses Parakeet when an accelerator is available, otherwise Whisper |
| `parakeet` | Apple Silicon speed | Requires `transformers`, `torch`, and `librosa` |
| `whisper` | Compatibility | Uses `faster-whisper` and supports more languages |

### Whisper model options (from fastest to most accurate)

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | ~75 MB | ★★★★★ | ★★ |
| `base` | ~145 MB | ★★★★ | ★★★ |
| `small` | ~483 MB | ★★★ | ★★★★ |
| `medium` | ~1.5 GB | ★★ | ★★★★ |
| `large-v3-turbo` | ~1.6 GB | ★★★ | ★★★★★ |

### Available hotkeys

| Config value | Key |
|-------------|-----|
| `ctrl_l` | Left Control (default) |
| `ctrl_r` | Right Control |
| `alt_r` | Right Alt |
| `alt_l` | Left Alt |
| `f9` – `f12` | Function keys |
| `cmd` | Command (macOS) |

---

## Personal Vocabulary

Add custom words, names, or technical terms to `data/vocab.txt` (one per line).
These are passed to Whisper as hints to improve recognition accuracy.

```
# data/vocab.txt — example
LangChain
PyTorch
Professor Roysam
University of Houston
CAR-T
```

---

## macOS Notes

- Text injection uses **Quartz** by default on macOS.
- The tray icon appears in the menu bar.
- The installed **Hush.app** needs Microphone and Accessibility. macOS opens the
  relevant pages as Hush requests them. Do not add Terminal, Python, or a
  virtual-environment path for the installed app.
- Input Monitoring is not a required step for the free installed build. The
  hotkey can work in other apps after Accessibility is enabled even if Hush is
  absent from that pane.
- Source runs are different: see [docs/setup.md](docs/setup.md) for the
  launcher-specific Terminal and Python.app guidance.

---

## Project Structure

```
voiceflow/
├── app/
│   └── main.py              # Application orchestration and runtime entry point
├── config/
│   ├── defaults.py           # Default configuration values
│   └── loader.py             # User config and vocabulary loading
├── prompts/
│   └── cleanup.py            # Versioned LLM prompt catalog
├── core/
│   ├── audio.py             # Push-to-talk recording
│   ├── vad.py               # Voice-activity detection and silence trimming
│   ├── transcriber.py       # Parakeet/Whisper ASR strategies
│   ├── cleaner.py           # LLM transcript cleanup
│   └── history.py            # SQLite transcription history
├── platform/
│   ├── factory.py             # Central OS detection and backend routing
│   ├── contracts.py           # Stable platform capability interfaces
│   ├── adapters.py            # macOS/Linux/Windows/generic bundles
│   └── backends/              # Concrete OS adapters by capability
├── web/
│   ├── api_server.py          # Local FastAPI dashboard server
│   └── ui/                    # Dashboard and onboarding pages
└── diagnostics/
    ├── permission_diagnostic.py # Interpreter and permission diagnostics
    └── hotkey_diagnostic.py     # Global keyboard event diagnostics

docs/
├── setup.md                    # Detailed installation and macOS permissions
└── architecture.md             # Runtime boundaries and platform design

pyproject.toml                  # Application dependencies and tool settings
uv.lock                         # Reproducible resolved dependency set

packaging/
├── build_dmg.sh                # DMG build helper
└── setup_app.py                # Optional py2app configuration

scripts/
└── setup_cross_platform.sh     # Linux/macOS helper for development setups
```

The root `main.py` is only a thin launcher; implementation code lives under
the `voiceflow/` package. `VoiceFlow.command` is the double-click launcher and
`install.sh` is the canonical macOS installer.

`pyproject.toml` is the application manifest. VoiceFlow is an executable
application, not a reusable Python package, so it sets `tool.uv.package = false`.
`uv.lock` records the resolved dependency versions. Use `uv sync` to prepare the
environment and `uv run` to execute commands inside it; do not install this
repository with `pip` or `pip install -e .`.

---

## Troubleshooting

**"No module named sounddevice"**
```bash
uv sync --no-dev
# macOS: brew install portaudio first
```

**Text not injecting on Linux**
```bash
sudo apt-get install xdotool
# or change config: method = "clipboard"
```

**Ollama not running / LLM unavailable**
```bash
# In a separate terminal:
ollama serve
```
VoiceFlow degrades gracefully — if Ollama is unavailable, it injects the raw Whisper transcript.

**pynput permission error while running from source on macOS**
```
System Settings → Privacy & Security → Input Monitoring → add Terminal (or Python)
```
This does not apply to an installed `Hush.app`; use the app's Accessibility
setup instead.

**Whisper downloading model on every run**
The model is cached in `~/.cache/huggingface/`. If it re-downloads, check that directory is writable.

**Tray icon not appearing on Linux (Wayland)**
pystray requires a system tray. On pure Wayland, install `gnome-shell-extension-appindicator` or switch to X11.

---

## License

MIT — free to use, modify, and distribute.
