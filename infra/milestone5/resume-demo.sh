#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
kubectl -n "$HUSH_NAMESPACE" scale deployment hush --replicas=2
kubectl -n "$HUSH_NAMESPACE" rollout status deployment hush --timeout=900s
kubectl -n "$HUSH_NAMESPACE" wait --for=condition=ScalingActive hpa/hush --timeout=180s
curl --retry 15 --retry-delay 10 --retry-all-errors --connect-timeout 10 --max-time 20 -fsS "https://${HUSH_HOSTNAME}/ready"
HUSH_REDIRECT_HEADERS="$(curl --connect-timeout 10 --max-time 20 -sS -o /dev/null -D - "http://${HUSH_HOSTNAME}/")"
printf '%s\n' "$HUSH_REDIRECT_HEADERS"
printf '%s\n' "$HUSH_REDIRECT_HEADERS" | head -1 | grep -q ' 301 '
printf '%s\n' "$HUSH_REDIRECT_HEADERS" | grep -Fi "location: https://${HUSH_HOSTNAME}" >/dev/null
kubectl -n "$HUSH_NAMESPACE" exec deployment/hush -- env \
  HUSH_LOAD_TARGET=http://127.0.0.1:57327 HUSH_PUBLIC_HOST="$HUSH_HOSTNAME" \
  HUSH_LOAD_SECONDS=1 HUSH_LOAD_CONCURRENCY=1 python scripts/milestone5_load.py
kubectl -n "$HUSH_NAMESPACE" get pods,hpa
echo "Ready for demo preflight at https://${HUSH_HOSTNAME}/. Automatic transcription check passed."
