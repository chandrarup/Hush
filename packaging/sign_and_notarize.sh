#!/usr/bin/env bash
# Sign, notarize, and staple a Hush DMG. Secrets stay in the macOS Keychain.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Hush"
VERSION="${HUSH_VERSION:-1.0.0}"
APP_PATH="${1:-$REPO_DIR/dist/$APP_NAME.app}"
DMG_PATH="$REPO_DIR/dist/$APP_NAME-$VERSION.dmg"
SIGNING_IDENTITY="${HUSH_SIGNING_IDENTITY:-}"
NOTARY_PROFILE="${HUSH_NOTARY_PROFILE:-}"

fail() {
  echo "Release preflight failed: $*" >&2
  exit 1
}

[[ "$(uname)" == "Darwin" ]] || fail "macOS is required for signing and notarization."
[[ -d "$APP_PATH" ]] || fail "Hush.app was not found at: $APP_PATH"
[[ -n "$SIGNING_IDENTITY" ]] || fail "Set HUSH_SIGNING_IDENTITY to a Developer ID Application identity."
[[ -n "$NOTARY_PROFILE" ]] || fail "Set HUSH_NOTARY_PROFILE to a notarytool Keychain profile."

security find-identity -v -p codesigning | grep -Fq "$SIGNING_IDENTITY" || \
  fail "The requested signing identity is not available in this login Keychain."

sign_target() {
  codesign --force --timestamp --options runtime --sign "$SIGNING_IDENTITY" "$1"
}

# Sign individual Mach-O files before signing nested bundles and the app itself.
while IFS= read -r -d '' target; do
  sign_target "$target"
done < <(
  find "$APP_PATH" -depth -type f \( -name '*.dylib' -o -name '*.so' -o -perm -111 \) -print0
)

while IFS= read -r -d '' target; do
  sign_target "$target"
done < <(
  find "$APP_PATH" -depth -type d \( -name '*.framework' -o -name '*.xpc' -o -name '*.appex' -o -name '*.bundle' \) -print0
)

sign_target "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

HUSH_VERSION="$VERSION" bash "$REPO_DIR/packaging/build_dmg.sh" "$APP_PATH"
xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARY_PROFILE" --wait
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"
spctl --assess --type open --verbose=4 "$DMG_PATH"

echo "Release-ready artifact: $DMG_PATH"
