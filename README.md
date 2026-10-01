# Hush

## Milestone 3 container deployment

The Linux cloud service runs as the same versioned `linux/amd64` image locally
and on the GCP VM. The macOS client remains native because microphone access,
global hotkeys, Accessibility, and text insertion require macOS permissions.

```bash
cp .env.example .env
# Replace the placeholder HUSH_TEAM_TOKEN in .env.
docker compose build hush
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:57327/status
```

Compose starts Hush, Ollama, and a one-time model initialization service. Hush
data, the Whisper download cache, and Ollama models use named volumes. See
[`deliverables/Hush_Milestone3_Runbook.md`](deliverables/Hush_Milestone3_Runbook.md)
for Artifact Registry and VM deployment commands. Never commit `.env`.

**Push-to-talk dictation with a thin desktop client and a self-hosted cloud transcription server.**

Hold a hotkey → speak → release → polished text appears wherever your cursor is.
The laptop streams microphone chunks to your authorized Hush VM; the VM owns
transcription, cleanup, snippets, and history.

---

## What it does

1. **Hold** Left Control (configurable) - microphone starts recording
2. **Speak** anything naturally (filler words, false starts, all fine)
3. **While speaking**, 16 kHz mono audio chunks stream to the Hush VM and live
   partial transcripts appear on the cloud dashboard.
4. **Release** the hotkey — the VM finalizes Whisper transcription, expands
   snippets, cleans the text, and stores the result in VM SQLite.
5. The desktop receives only the final result and inserts it into the text field
   that was active when dictation began.
6. A floating notification shows raw vs. cleaned text for 3 seconds.

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
4. Choose **Allow** for Microphone, enable **Hush** under Input Monitoring for
   the global hotkey, then enable **Hush** under Accessibility for text insertion.

If Hush is absent from either privacy pane, use **+** to select
`/Applications/Hush.app`. Do not add Terminal or Python for the installed app.

See [the macOS app guide](docs/MACOS_APP_RELEASE.md) for the complete install,
reinstall, and troubleshooting flow.

---

## Source Requirements

| Component | Purpose |
|-----------|---------|
| Python 3.10+ | Runtime |
| [uv](https://docs.astral.sh/uv/) | Application environment and dependency manager |
| Hush VM | Whisper, cleanup, snippets, dashboard, and SQLite history |
| Shared team token | Authenticates desktop WebSocket sessions and dashboard changes |
| PortAudio | Audio I/O backend |
| xdotool (Linux) | Text injection |

---

## Run From Source

These instructions are for a repository checkout. They create a local Python
environment and have different macOS permission requirements from the installed
app. See [docs/setup.md](docs/setup.md) for the complete source setup and
diagnostic guide.

### 1. Install uv

VoiceFlow uses [uv](https://docs.astral.sh/uv/) to manage its application
environment. Install it once if it is not already available:

```bash
# macOS with Homebrew
brew install uv

# Linux or other supported platforms
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Run the installer

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
create the project-local configuration files. The macOS installer is the
recommended path for this repository.

### 3. Configure the cloud connection

Set the VM URL in `data/config.toml`. Keep the shared token out of Git; prefer
the environment variable when launching Hush:

```toml
[cloud]
base_url = "http://VM_PUBLIC_IP:57327"
token = ""
```

```bash
HUSH_TEAM_TOKEN="YOUR_SHARED_TEAM_TOKEN" uv run --no-dev python -m voiceflow.app.main
```

The VM firewall must still restrict TCP `57327` to the team public IP addresses.

### 4. Launch Hush

```bash
uv run --no-dev python -m voiceflow.app.main
```

The desktop does not load or download a speech model. The VM downloads and
caches `faster-whisper` `base.en` on its first transcription request.

---

## Manual Installation (without an installer)

```bash
# macOS
brew install portaudio

# Ubuntu/Debian
sudo apt-get install portaudio19-dev xdotool libnotify-bin

# Install uv once if needed: https://docs.astral.sh/uv/getting-started/installation/

# Python application dependencies
uv sync --no-dev

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

[cloud]
base_url = "http://VM_PUBLIC_IP:57327"
token = ""                 # Prefer HUSH_TEAM_TOKEN instead of saving this.
client_id = ""             # Generated and persisted on first launch.
connect_timeout_seconds = 5
final_timeout_seconds = 90

[ui]
show_notification = true
notification_duration = 3
dashboard_port = 57327
```

### Cloud speech model

Live WebSocket sessions use `faster-whisper` `base.en` on the VM. The desktop
does not load Parakeet or Whisper and has no local transcription fallback.

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

## Optional Gemini Transcribe test

To compare the VM transcription path with Google Cloud's Gemini 3.5 Transcribe
preview model, use the separate button-driven diagnostic prototype in
`scripts/gemini_transcribe_button.py`. Audio recorded through this script is
sent to Google Cloud.

```bash
gcloud auth application-default login
uv run --with google-genai python scripts/gemini_transcribe_button.py \
  --project project-25e4d84e-0cf5-4f81-89b \
  --language en-US
```

Open the printed local URL, click **Start recording**, speak, then click
**Stop and transcribe**. The script records from the default microphone, trims
silence, sends a WAV clip to `gemini-3.5-transcribe-preview`, and prints the
transcript in the browser page.

Optional flags:

```bash
--location global
--port 57328
--no-open
--diarization
--word-timestamps
--vocab "Hush"
--vocab "University of Houston"
```

---

## macOS Notes

- Text injection uses **Quartz** by default on macOS.
- The tray icon appears in the menu bar.
- The installed **Hush.app** needs Microphone, Input Monitoring, and Accessibility. macOS opens the
  relevant pages as Hush requests them. Do not add Terminal, Python, or a
  virtual-environment path for the installed app.
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

**VM Ollama not running / cleanup unavailable**
```bash
# Run on the VM:
ollama serve
```
Hush degrades gracefully to the raw VM transcript if the configured cleanup
provider is unavailable.

**pynput permission error while running from source on macOS**
```
System Settings → Privacy & Security → Input Monitoring → add Terminal (or Python)
```
For an installed `Hush.app`, add Hush itself under both Input Monitoring and
Accessibility.

**Whisper downloading the model on every VM start**
The model is cached on the VM under its service user's Hugging Face cache. If it
re-downloads, check that the service has a stable writable home directory.

**Tray icon not appearing on Linux (Wayland)**
pystray requires a system tray. On pure Wayland, install `gnome-shell-extension-appindicator` or switch to X11.

---

## License

MIT — free to use, modify, and distribute.
