#!/bin/bash
set -euo pipefail
HUSH_LAUNCH_ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ -x "$HUSH_LAUNCH_ROOT/.venv/bin/python" ]]; then
  HUSH_LAUNCH_PYTHON="$HUSH_LAUNCH_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  HUSH_LAUNCH_PYTHON="$(command -v python3)"
else
  echo 'Python 3.11 or newer is required to read your saved Hush configuration.' >&2
  exit 1
fi
"$HUSH_LAUNCH_PYTHON" "$HUSH_LAUNCH_ROOT/scripts/open_cloud_dashboard.py" "$@"
