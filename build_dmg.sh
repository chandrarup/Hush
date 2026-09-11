#!/usr/bin/env bash
# build_dmg.sh — Create distributable VoiceFlow DMG
# Usage: bash build_dmg.sh
# Requires: create-dmg  (brew install create-dmg)
set -euo pipefail

VERSION="1.0.0"
APP_NAME="VoiceFlow"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
DIST_DIR="$(pwd)/dist"
STAGE_DIR="$(mktemp -d)"

echo "→ Staging distribution files..."
mkdir -p "$STAGE_DIR"

# Copy project files (exclude venv, __pycache__, .git)
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
         --exclude='*.pyc' --exclude='dist' --exclude='build' \
         "$(pwd)/" "$STAGE_DIR/${APP_NAME}/"

echo "→ Compiling Python source code to hide plain text..."
# Compile all .py files to .pyc in the staging directory, then delete the .py files.
find "$STAGE_DIR/${APP_NAME}" -name "*.py" -type f | while read -r pyfile; do
    # Only compile our source files, leave tests or installer scripts alone if any
    python3 -c "import py_compile; py_compile.compile('$pyfile', cfile='${pyfile}c')"
    rm "$pyfile"
done

# Make executable
chmod +x "$STAGE_DIR/${APP_NAME}/VoiceFlow.command"
chmod +x "$STAGE_DIR/${APP_NAME}/install.sh"

mkdir -p "$DIST_DIR"

if ! command -v create-dmg &>/dev/null; then
  echo "create-dmg not found. Install with: brew install create-dmg"
  # Fallback: simple hdiutil DMG
  echo "→ Creating simple DMG with hdiutil..."
  hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE_DIR" \
    -ov -format UDZO "$DIST_DIR/$DMG_NAME"
else
  echo "→ Creating branded DMG with create-dmg..."
  CMD_ARGS=(
    "--volname" "$APP_NAME"
    "--window-size" "660" "400"
    "--icon-size" "100"
    "--icon" "VoiceFlow" "180" "200"
  )
  
  if [ -f "assets/icon.icns" ]; then
    CMD_ARGS+=("--volicon" "assets/icon.icns")
  fi

  create-dmg "${CMD_ARGS[@]}" "$DIST_DIR/$DMG_NAME" "$STAGE_DIR/"

fi

rm -rf "$STAGE_DIR"
echo ""
echo "✅ DMG created: $DIST_DIR/$DMG_NAME"
echo ""
echo "To distribute:"
echo "  1. Upload $DMG_NAME to GitHub Releases"
echo "  2. Users: Open DMG → double-click 'VoiceFlow' folder → run install.sh"
echo ""
