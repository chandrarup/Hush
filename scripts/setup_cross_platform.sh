#!/usr/bin/env bash
# =============================================================================
#  VoiceFlow Setup Script
#  Supports: macOS (Homebrew) and Ubuntu/Debian Linux
# =============================================================================
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       VoiceFlow Setup                   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

OS="$(uname -s)"

# ── System dependencies ───────────────────────────────────────────────────── #

if [[ "$OS" == "Darwin" ]]; then
    echo ">>> Detected macOS"

    # Check for Homebrew
    if ! command -v brew &>/dev/null; then
        echo "  Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    echo ">>> Installing system deps via Homebrew..."
    # PortAudio is required by sounddevice
    brew install portaudio 2>/dev/null || true
    # pyautogui on macOS may need these
    brew install python-tk 2>/dev/null || true

    echo ""
    echo "NOTE (macOS): Text injection uses pyautogui, which requires"
    echo "Accessibility permissions."
    echo ""
    echo "  Go to: System Settings → Privacy & Security → Accessibility"
    echo "  Add your Terminal app (or the Python binary) to the allowed list."
    echo ""

elif [[ "$OS" == "Linux" ]]; then
    echo ">>> Detected Linux"
    sudo apt-get update -qq
    sudo apt-get install -y \
        portaudio19-dev \
        xdotool \
        libnotify-bin \
        python3-tk \
        python3-dev \
        gcc \
        2>/dev/null || true
else
    echo "WARNING: Unknown OS '$OS'. Proceeding anyway..."
fi

# ── uv and Python dependencies ────────────────────────────────────────────── #
echo ""
echo ">>> Checking uv..."

if ! command -v uv &>/dev/null; then
    if command -v brew &>/dev/null; then
        brew install uv
    elif command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
fi

UV_BIN="$(command -v uv || true)"
if [ -z "$UV_BIN" ] && [ -x "$HOME/.local/bin/uv" ]; then
    UV_BIN="$HOME/.local/bin/uv"
fi
if [ -z "$UV_BIN" ]; then
    echo "ERROR: uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

SYNC_ARGS=(--project "$REPO_DIR" --no-dev)
if [[ "$OS" == "Darwin" ]]; then
    SYNC_ARGS+=(--extra parakeet)
fi
"$UV_BIN" sync "${SYNC_ARGS[@]}"

# ── Config directory & files ──────────────────────────────────────────────── #
echo ""
echo ">>> Setting up ~/.voiceflow configuration..."

mkdir -p ~/.voiceflow

if [ ! -f ~/.voiceflow/config.toml ]; then
    cat > ~/.voiceflow/config.toml << 'TOML'
[hotkey]
key = "ctrl_r"

[asr]
model = "large-v3-turbo"
language = "en"
compute_type_gpu = "float16"
compute_type_cpu = "int8"

[llm]
model = "llama3.2:3b"
fallback_model = "phi3:mini"
temperature = 0.1
max_tokens = 500

[injection]
method = "auto"

[ui]
show_notification = true
notification_duration = 3
TOML
    echo "  Created ~/.voiceflow/config.toml"
else
    echo "  Config already exists - skipping."
fi

# Create empty vocab file
if [ ! -f ~/.voiceflow/vocab.txt ]; then
    touch ~/.voiceflow/vocab.txt
    echo "  Created ~/.voiceflow/vocab.txt (empty - add custom words one per line)"
fi

# ── Ollama setup ──────────────────────────────────────────────────────────── #
echo ""
echo ">>> Checking for Ollama..."

if command -v ollama &>/dev/null; then
    echo "  Ollama found. Pulling llama3.2:3b model..."
    ollama pull llama3.2:3b
    echo "  Model ready."
else
    echo ""
    echo "  ⚠  Ollama is NOT installed."
    echo "  Install it from: https://ollama.com"
    echo ""
    echo "  macOS:  brew install ollama  OR  download from https://ollama.com/download"
    echo "  Linux:  curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
    echo "  After installing, run:"
    echo "    ollama serve          # (in a separate terminal or as a service)"
    echo "    ollama pull llama3.2:3b"
    echo ""
    echo "  VoiceFlow works without Ollama - it will use raw Whisper output instead."
fi

# ── Done ─────────────────────────────────────────────────────────────────── #
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  Setup complete!                        ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  Run VoiceFlow:"
echo "    uv run --project \"$REPO_DIR\" --no-dev python -m voiceflow.app.main"
echo ""
echo "  Usage:"
echo "    • Hold Right Ctrl (default) to start recording"
echo "    • Release to transcribe and inject text"
echo "    • Right-click the tray icon to Quit"
echo ""
echo "  Customize:"
echo "    • ~/.voiceflow/config.toml  - hotkey, models, language"
echo "    • ~/.voiceflow/vocab.txt    - personal vocabulary (one word/phrase per line)"
echo ""
