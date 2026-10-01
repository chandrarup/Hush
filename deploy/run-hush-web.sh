#!/usr/bin/env bash

set -euo pipefail

: "${HUSH_TEAM_TOKEN:?Set HUSH_TEAM_TOKEN in the systemd EnvironmentFile before starting Hush.}"

metadata_url="http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip"
public_ip="$({
  curl -fsS \
    --retry 10 \
    --retry-all-errors \
    --retry-delay 2 \
    --connect-timeout 2 \
    -H "Metadata-Flavor: Google" \
    "$metadata_url"
})"

export HUSH_ALLOWED_HOSTS="${public_ip},localhost,127.0.0.1"
export HUSH_SERVER_MODE="cloud"

exec /home/ashrith_vadde/hush/.venv/bin/uvicorn \
  voiceflow.web.api_server:app \
  --host 0.0.0.0 \
  --port 57327
