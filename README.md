# VoiceFlow

**Local push-to-talk speech-to-text dictation — a Wispr Flow replica using 100% open-source tools.**

Hold a hotkey → speak → release → polished text appears wherever your cursor is.
No cloud APIs. No subscriptions. No data leaves your machine.

---

## What it does

1. **Hold** Right Ctrl (configurable) — microphone starts recording
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

## Requirements

| Component | Purpose |
|-----------|---------|
| Python 3.10+ | Runtime |
| [Ollama](https://ollama.com) | Local LLM server |
| PortAudio | Audio I/O backend |
| librosa | Required for Parakeet ASR on Apple Silicon |
| xdotool (Linux) | Text injection |

---

## Quick Start

For a complete machine setup checklist, including macOS Input Monitoring,
Accessibility, Microphone permissions, Python.app selection, and diagnostics,
see [SETUP.md](SETUP.md).

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

### 2. Run the setup script

```bash
cd voiceflow
bash setup.sh
```

This will:
- Install system dependencies (PortAudio, xdotool on Linux)
- Install all Python packages
- Create `~/.voiceflow/config.toml` with defaults
- Create `~/.voiceflow/vocab.txt` (empty)
- Pull the `llama3.2:3b` model via Ollama

### 3. Launch VoiceFlow

```bash
python main.py
```

On first launch, Whisper will download the `large-v3-turbo` model (~1.5 GB). This only happens once; it is cached in `~/.cache/huggingface/`.

---

## Manual Installation (without setup.sh)

```bash
# macOS
brew install portaudio

# Ubuntu/Debian
sudo apt-get install portaudio19-dev xdotool libnotify-bin

# Python deps
pip install -r requirements.txt

# Ollama model
ollama pull llama3.2:3b
```

---

## Configuration

Edit `~/.voiceflow/config.toml`:

```toml
[hotkey]
key = "ctrl_r"        # Right Ctrl — change to "ctrl", "f9", "alt_r", etc.

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
method = "quartz"          # quartz | clipboard | pyautogui | xdotool

[ui]
show_notification = true
notification_duration = 3
dashboard_port = 57327
```

### ASR engine options

| Engine | Best for | Notes |
|--------|----------|-------|
| `auto` | Recommended | Uses Parakeet on macOS when available, otherwise Whisper |
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
| `ctrl_r` | Right Control (default) |
| `ctrl_l` | Left Control |
| `alt_r` | Right Alt |
| `alt_l` | Left Alt |
| `f9` – `f12` | Function keys |
| `cmd` | Command (macOS) |

---

## Personal Vocabulary

Add custom words, names, or technical terms to `~/.voiceflow/vocab.txt` (one per line).
These are passed to Whisper as hints to improve recognition accuracy.

```
# ~/.voiceflow/vocab.txt — example
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
- Grant **Input Monitoring** for the hotkey:
  `System Settings → Privacy & Security → Input Monitoring`
- Grant **Accessibility** for text injection:
  `System Settings → Privacy & Security → Accessibility`
- Grant **Microphone** for recording:
  `System Settings → Privacy & Security → Microphone`
- If `.venv/bin/python` is greyed out in the macOS picker, run
  `python check_permission.py` and add the resolved `Python.app` bundle instead.
- See [SETUP.md](SETUP.md) for the full step-by-step permission flow.

---

## Project Structure

```
voiceflow/
├── main.py          # Entry point — wires everything together
├── audio.py         # Push-to-talk recording (sounddevice)
├── vad.py           # Silence trimming (webrtcvad)
├── transcriber.py   # ASR (faster-whisper)
├── cleaner.py       # LLM text cleanup (ollama)
├── injector.py      # Text injection (xdotool / clipboard / pyautogui)
├── tray.py          # System tray icon (pystray + Pillow)
├── notifier.py      # Desktop notification (plyer)
├── config.py        # Config loader (~/.voiceflow/config.toml)
├── setup.sh         # One-command setup
├── requirements.txt
└── README.md
```

---

## Troubleshooting

**"No module named sounddevice"**
```bash
pip install sounddevice
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

**pynput permission error on macOS**
```
System Settings → Privacy & Security → Input Monitoring → add Terminal (or Python)
```

**Whisper downloading model on every run**
The model is cached in `~/.cache/huggingface/`. If it re-downloads, check that directory is writable.

**Tray icon not appearing on Linux (Wayland)**
pystray requires a system tray. On pure Wayland, install `gnome-shell-extension-appindicator` or switch to X11.

---

## License

MIT — free to use, modify, and distribute.
