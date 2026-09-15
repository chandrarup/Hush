#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 /path/to/VoiceFlow.app /path/to/output/VoiceFlow.dmg"
  exit 1
fi

APP_PATH="$1"
OUTPUT_DMG="$2"
VOL_NAME="VoiceFlow"
STAGE_DIR="$(mktemp -d)"

mkdir -p "$STAGE_DIR"
cp -R "$APP_PATH" "$STAGE_DIR/"
ln -s /Applications "$STAGE_DIR/Applications"

hdiutil create -volname "$VOL_NAME" -srcfolder "$STAGE_DIR" -ov -format UDZO "$OUTPUT_DMG"
rm -rf "$STAGE_DIR"

echo "DMG created at: $OUTPUT_DMG"
