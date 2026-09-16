#!/usr/bin/env bash
# install.sh — One-command Hush installer
# Usage: bash install.sh
# Requires: macOS 12+, internet connection (first run)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$REPO_DIR/.venv"
LAUNCH_SCRIPT="$REPO_DIR/VoiceFlow.command"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.voiceflow.plist"

# ── Colors ─────────────────────────────────────────────────────────── #
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓${NC} $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $1"; }
info() { echo -e "  → $1"; }

echo ""
echo "  ╔═══════════════════════════════╗"
echo "  ║   VoiceFlow Installer  v1.0   ║"
echo "  ╚═══════════════════════════════╝"
echo ""

# ── 1. Check Python ────────────────────────────────────────────────── #
info "Checking Python..."
if ! command -v python3 &>/dev/null; then
  warn "Python 3 not found. Installing via Homebrew..."
  if ! command -v brew &>/dev/null; then
    echo -e "${RED}Error: Homebrew not installed. Please install it from https://brew.sh${NC}"
    exit 1
  fi
  brew install python3
fi
PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
PYVER=$("$PY" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "Python $PYVER found at $PY"

# ── 2. Check uv ─────────────────────────────────────────────────────── #
info "Checking uv..."
if ! command -v uv &>/dev/null; then
  if command -v brew &>/dev/null; then
    brew install uv
  else
    echo -e "${RED}Error: uv is not installed and Homebrew is unavailable.${NC}"
    echo "Install uv from https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
  fi
fi
UV_BIN="$(command -v uv)"
ok "uv $($UV_BIN --version | awk '{print $2}') found at $UV_BIN"

# ── 3. Create and sync the application environment ─────────────────── #
info "Creating virtual environment with uv..."
"$UV_BIN" venv --python "$PY" "$VENV"
ok "Virtualenv created at $VENV"

# Install the optional Parakeet engine on macOS; Whisper remains the fallback.
info "Syncing application dependencies with uv (may take a few minutes)..."
"$UV_BIN" sync --project "$REPO_DIR" --python "$PY" --extra parakeet --no-dev -q
ok "Application dependencies installed"

# Migrate legacy home-directory data before creating project-local defaults.
info "Migrating legacy application data..."
"$VENV/bin/python" -c 'from voiceflow.config.migration import migrate_legacy_data; [print(f"  {action}") for action in migrate_legacy_data()]'

# ── 4. Check Ollama ───────────────────────────────────────────────── #
info "Checking Ollama..."
if ! command -v ollama &>/dev/null; then
  warn "Ollama not found. Installing..."
  if command -v brew &>/dev/null; then
    brew install ollama
  else
    warn "Please install Ollama manually: https://ollama.com/download"
  fi
fi
if command -v ollama &>/dev/null; then
  ok "Ollama found"
  info "Pulling llama3.2:3b model (first pull only, ~2 GB)..."
  ollama pull llama3.2:3b || warn "Could not pull model — run 'ollama pull llama3.2:3b' manually"
fi

# ── 5. Create config ──────────────────────────────────────────────── #
CONFIG_DIR="$REPO_DIR/data"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.toml" ]; then
  info "Writing default config..."
  cat > "$CONFIG_DIR/config.toml" << 'EOF'
[hotkey]
key = "ctrl_r"      # Change to cmd_r, f9, f10, etc.

[asr]
engine = "auto"     # auto | parakeet | whisper

[llm]
ollama_model   = "llama3.2:3b"
ollama_base_url = "http://localhost:11434"
cleanup_level  = "light"  # none | light | medium | high
temperature    = 0.1
max_tokens     = 500

[injection]
method = "auto"     # auto | quartz | clipboard | pyautogui

[ui]
show_notification     = true
notification_duration = 3
dashboard_port        = 57327
EOF
  ok "Config written to $CONFIG_DIR/config.toml"
else
  ok "Config already exists — skipping"
fi

# ── 6. Create launcher ────────────────────────────────────────────── #
info "Creating launcher script..."
cat > "$LAUNCH_SCRIPT" << EOF
#!/usr/bin/env bash
# VoiceFlow launcher — double-click or run from terminal
cd "$REPO_DIR"
# Start Ollama in background if not running
if command -v ollama &>/dev/null && ! pgrep -x ollama &>/dev/null; then
  ollama serve &>/dev/null &
  sleep 1
fi
exec "$VENV/bin/python" -m voiceflow.app.main
EOF
chmod +x "$LAUNCH_SCRIPT"
ok "Launcher created: $LAUNCH_SCRIPT"

# ── 7. LaunchAgent for auto-start ────────────────────────────────── #
info "Setting up auto-start at login..."
cat > "$LAUNCH_AGENT" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>           <string>com.voiceflow</string>
  <key>ProgramArguments</key>
  <array>
    <string>$VENV/bin/python</string>
    <string>-m</string>
    <string>voiceflow.app.main</string>
  </array>
  <key>WorkingDirectory</key> <string>$REPO_DIR</string>
  <key>RunAtLoad</key>        <true/>
  <key>KeepAlive</key>        <false/>
  <key>StandardOutPath</key>  <string>$REPO_DIR/data/hush.log</string>
  <key>StandardErrorPath</key><string>$REPO_DIR/data/hush.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    <key>HOME</key><string>$HOME</string>
  </dict>
</dict>
</plist>
EOF
launchctl load -w "$LAUNCH_AGENT" 2>/dev/null || true
ok "Auto-start configured (runs at login)"

# ── Done ─────────────────────────────────────────────────────────── #
echo ""
echo -e "${GREEN}  ╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║   Installation complete! 🎙            ║${NC}"
echo -e "${GREEN}  ╚═══════════════════════════════════════╝${NC}"
echo ""
echo "  To start now:       open '$LAUNCH_SCRIPT'"
echo "  Or from terminal:   bash '$LAUNCH_SCRIPT'"
echo "  Dashboard:          http://localhost:57327"
echo "  Config:             $CONFIG_DIR/config.toml"
echo ""
echo "  VoiceFlow will start automatically at login."
echo ""
