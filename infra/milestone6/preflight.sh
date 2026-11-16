#!/usr/bin/env bash
set -euo pipefail

: "${HUSH_PROJECT:?HUSH_PROJECT is required}"
: "${HUSH_COMMIT_SHA:?HUSH_COMMIT_SHA is required}"
: "${HUSH_BRANCH:?HUSH_BRANCH is required}"
: "${HUSH_EXPECTED_BRANCH:?HUSH_EXPECTED_BRANCH is required}"

[[ "$HUSH_PROJECT" == "hush-milestone-2-20260922" ]] || {
  echo "Unexpected Google Cloud project." >&2
  exit 1
}
[[ "$HUSH_BRANCH" == "$HUSH_EXPECTED_BRANCH" ]] || {
  echo "Build branch does not match the deployment branch." >&2
  exit 1
}
[[ "$HUSH_COMMIT_SHA" =~ ^[0-9a-f]{40}$ ]] || {
  echo "A real 40-character Git commit SHA is required." >&2
  exit 1
}

echo "Release preflight passed: branch=$HUSH_BRANCH sha=$HUSH_COMMIT_SHA project=$HUSH_PROJECT"
