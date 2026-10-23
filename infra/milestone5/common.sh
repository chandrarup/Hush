#!/usr/bin/env bash
set -euo pipefail
HUSH_INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HUSH_INFRA_DIR/release.env"
HUSH_EXPECTED_CONTEXT="gke_${GOOGLE_CLOUD_PROJECT}_${HUSH_REGION}_${HUSH_CLUSTER}"
if [[ "$(kubectl config current-context)" != "$HUSH_EXPECTED_CONTEXT" ]]; then
  echo "Wrong Kubernetes context. Select $HUSH_EXPECTED_CONTEXT before continuing." >&2
  exit 1
fi
