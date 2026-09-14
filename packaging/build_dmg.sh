#!/usr/bin/env bash
# Package a built Hush.app for Finder installation. Signing happens before this step.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Hush"
VERSION="${HUSH_VERSION:-1.0.0}"
APP_PATH="${1:-$REPO_DIR/dist/$APP_NAME.app}"
DIST_DIR="$REPO_DIR/dist"
DMG_PATH="$DIST_DIR/$APP_NAME-$VERSION.dmg"
STAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hush-dmg.XXXXXX")"

cleanup() {
  rm -rf "$STAGE_DIR"
}
trap cleanup EXIT

if [[ ! -d "$APP_PATH" ]]; then
  echo "Hush.app was not found at: $APP_PATH" >&2
  echo "Build the application first with packaging/build_app.sh." >&2
  exit 1
fi

mkdir -p "$DIST_DIR"
cp -R "$APP_PATH" "$STAGE_DIR/$APP_NAME.app"
ln -s /Applications "$STAGE_DIR/Applications"

rm -f "$DMG_PATH"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGE_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "Created $DMG_PATH"
echo "Sign and notarize the release artifact before publishing it."
