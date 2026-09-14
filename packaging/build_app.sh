#!/usr/bin/env bash
# Build a self-contained Hush.app for local packaging and release validation.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
uv sync --directory "$REPO_DIR" --group build

cd "$REPO_DIR/packaging"

"$REPO_DIR/.venv/bin/python" setup_app.py py2app \
  --dist-dir "$REPO_DIR/dist" \
  --bdist-base "$REPO_DIR/build"
