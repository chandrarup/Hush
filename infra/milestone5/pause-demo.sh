#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
kubectl -n "$HUSH_NAMESPACE" delete job -l app=hush-load --ignore-not-found --wait=false
kubectl -n "$HUSH_NAMESPACE" scale deployment hush --replicas=0
if [[ -n "$(kubectl -n "$HUSH_NAMESPACE" get pods -l app=hush -o name)" ]]; then
  kubectl -n "$HUSH_NAMESPACE" wait --for=delete pod -l app=hush --timeout=300s
fi
kubectl -n "$HUSH_NAMESPACE" wait --for=condition=ScalingActive=false hpa/hush --timeout=180s
kubectl -n "$HUSH_NAMESPACE" get deployment,hpa
echo 'Application compute is paused. The retained load balancer and database still incur charges.'
