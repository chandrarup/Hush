#!/usr/bin/env bash
# VoiceFlow.command — Double-clickable launcher for VoiceFlow
# macOS recognises .command files and can run them from Finder / DMG
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV" ]; then
  echo "VoiceFlow isn't installed yet."
  echo "Please run install.sh first:"
  echo "  bash \"$SCRIPT_DIR/install.sh\""
  read -p "Press any key to exit..." -n1
  exit 1
fi

# Start Ollama in background if not already running
if command -v ollama &>/dev/null && ! pgrep -x ollama &>/dev/null; then
  ollama serve &>/dev/null &
  sleep 1
fi

cd "$SCRIPT_DIR"
exec "$VENV/bin/python" main.py
