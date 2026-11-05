#!/usr/bin/env bash
# One Cloud Build step owns the deployment and its failure trap so rollback
# still runs when rollout, public HTTPS, or authenticated smoke checks fail.
set -Eeuo pipefail

source "$(dirname "$0")/preflight.sh"

: "${HUSH_IMAGE_TAG:?HUSH_IMAGE_TAG is required}"
HUSH_FORCE_HEALTH_FAILURE="${HUSH_FORCE_HEALTH_FAILURE:-0}"
[[ "$HUSH_FORCE_HEALTH_FAILURE" == "0" || "$HUSH_FORCE_HEALTH_FAILURE" == "1" ]] || {
  echo "HUSH_FORCE_HEALTH_FAILURE must be 0 or 1." >&2
  exit 1
}

readonly IMAGE_REPOSITORY="us-central1-docker.pkg.dev/${HUSH_PROJECT}/hush-containers/hush"
readonly PUBLIC_BASE="https://hush.34.36.104.111.nip.io"
[[ "$HUSH_IMAGE_TAG" == "${IMAGE_REPOSITORY}:${HUSH_COMMIT_SHA}" ]] || {
  echo "Image tag does not match this commit and Artifact Registry repository." >&2
  exit 1
}

new_image=""
previous_image=""
previous_revision=""
previous_sha=""
deployment_started=0
readiness_body="$(mktemp)"

for command in gcloud kubectl curl python3; do
  command -v "$command" >/dev/null || {
    echo "Required deployment command is missing: $command" >&2
    exit 1
  }
done

deployment_image() {
  kubectl -n hush get deployment hush -o 'jsonpath={.spec.template.spec.containers[?(@.name=="hush")].image}'
}

deployment_revision() {
  kubectl -n hush get deployment hush -o 'jsonpath={.metadata.annotations.deployment\.kubernetes\.io/revision}'
}

deployment_release_sha() {
  kubectl -n hush get deployment hush -o 'jsonpath={.spec.template.spec.containers[?(@.name=="hush")].env[?(@.name=="HUSH_RELEASE_SHA")].value}'
}

check_public_ready() {
  local expected_sha="$1"
  local consecutive=0
  local attempt
  for attempt in $(seq 1 30); do
    if curl --fail --silent --show-error --connect-timeout 8 --max-time 20 \
        --output "$readiness_body" "${PUBLIC_BASE}/ready" && \
        python3 - "$readiness_body" "$expected_sha" <<'PY'
import json
import sys

try:
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    raise SystemExit(1)
if payload.get("status") != "ready" or payload.get("mode") != "managed":
    raise SystemExit(1)
if not all(payload.get("checks", {}).values()) or not payload.get("checks"):
    raise SystemExit(1)
if sys.argv[2] and payload.get("release_sha") != sys.argv[2]:
    raise SystemExit(1)
PY
    then
      consecutive=$((consecutive + 1))
      if (( consecutive >= 4 )); then
        echo "External HTTPS /ready passed four consecutive checks; expected_sha=${expected_sha:-previous-release}"
        return 0
      fi
    else
      consecutive=0
    fi
    sleep 5
  done
  echo "External HTTPS /ready did not stabilize for expected_sha=${expected_sha:-previous-release}." >&2
  return 1
}

check_authenticated_history() {
  local token
  local attempt
  token="$(gcloud secrets versions access latest \
    --secret=hush-team-token --project="$HUSH_PROJECT")" || return 1
  [[ -n "$token" ]] || return 1
  # The bearer token and response body are never written to Cloud Build logs.
  for attempt in $(seq 1 5); do
    if curl --fail --silent --show-error --connect-timeout 8 --max-time 20 \
        --output /dev/null --header "Authorization: Bearer ${token}" \
        "${PUBLIC_BASE}/history?limit=1"; then
      echo "Authenticated /history smoke check passed."
      return 0
    fi
    sleep 5
  done
  echo "Authenticated /history smoke check did not pass." >&2
  return 1
}

rollback_on_failure() {
  local original_status=$?
  trap - EXIT
  rm -f "$readiness_body"
  if (( original_status == 0 )); then
    exit 0
  fi
  if (( deployment_started == 0 )); then
    echo "Release failed before Deployment mutation; no rollback needed." >&2
    exit "$original_status"
  fi

  set +e
  echo "Release failed; checking Deployment before rollback to revision ${previous_revision}." >&2
  local current_image
  current_image="$(deployment_image)"
  if [[ "$current_image" == "$new_image" ]]; then
    kubectl -n hush rollout undo deployment/hush --to-revision="$previous_revision"
    if (( $? != 0 )); then
      echo "ROLLBACK FAILED: rollout undo failed." >&2
      exit 1
    fi
  elif [[ "$current_image" == "$previous_image" ]]; then
    echo "Deployment still serves the previous image; no undo needed." >&2
  else
    echo "ROLLBACK FAILED: another image is active; refusing to overwrite it." >&2
    exit 1
  fi

  kubectl -n hush rollout status deployment/hush --timeout=420s
  if (( $? != 0 )); then
    echo "ROLLBACK FAILED: previous revision did not become ready." >&2
    exit 1
  fi
  current_image="$(deployment_image)"
  if [[ "$current_image" != "$previous_image" ]]; then
    echo "ROLLBACK FAILED: serving image differs from the saved image." >&2
    exit 1
  fi
  check_public_ready "$previous_sha"
  if (( $? != 0 )); then
    echo "ROLLBACK FAILED: external HTTPS did not stabilize." >&2
    exit 1
  fi
  check_authenticated_history
  if (( $? != 0 )); then
    echo "ROLLBACK FAILED: authenticated smoke check failed." >&2
    exit 1
  fi
  echo "Rollback verified: revision=${previous_revision} image=${previous_image}" >&2
  exit "$original_status"
}

trap rollback_on_failure EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

new_image="$(gcloud artifacts docker images describe "$HUSH_IMAGE_TAG" \
  --project="$HUSH_PROJECT" --format='value(image_summary.fully_qualified_digest)')"
[[ "$new_image" =~ ^${IMAGE_REPOSITORY}@sha256:[0-9a-f]{64}$ ]] || {
  echo "Artifact Registry did not return a valid immutable digest." >&2
  exit 1
}
echo "Deploying commit=${HUSH_COMMIT_SHA} image=${new_image}"

gcloud container clusters get-credentials hush-m5 --region=us-central1 \
  --project="$HUSH_PROJECT" --quiet
previous_image="$(deployment_image)"
previous_revision="$(deployment_revision)"
previous_sha="$(deployment_release_sha)"
if [[ ! "$previous_sha" =~ ^[0-9a-f]{40}$ ]]; then
  previous_sha=""
fi
[[ "$previous_image" =~ ^${IMAGE_REPOSITORY}@sha256:[0-9a-f]{64}$ ]] || {
  echo "Previous Deployment image is not an immutable Hush digest." >&2
  exit 1
}
[[ "$previous_revision" =~ ^[0-9]+$ ]] || {
  echo "Previous Deployment revision is unavailable." >&2
  exit 1
}
echo "Saved previous revision=${previous_revision} image=${previous_image}"

if [[ "$previous_image" == "$new_image" && "$previous_sha" == "$HUSH_COMMIT_SHA" ]]; then
  echo "This commit and digest are already deployed; checking serving health without mutation."
  check_public_ready "$HUSH_COMMIT_SHA"
  check_authenticated_history
  if [[ "$HUSH_FORCE_HEALTH_FAILURE" == "1" ]]; then
    echo "Controlled health-gate failure requested; no Deployment mutation occurred." >&2
    exit 42
  fi
  echo "Existing release verified: commit=${HUSH_COMMIT_SHA} image=${new_image}"
  exit 0
fi

patch="$(printf '{"spec":{"template":{"spec":{"containers":[{"name":"hush","image":"%s","env":[{"name":"HUSH_RELEASE_SHA","value":"%s"}]}]}}}}' \
  "$new_image" "$HUSH_COMMIT_SHA")"
deployment_started=1
kubectl -n hush patch deployment hush --type=strategic -p "$patch"
kubectl -n hush rollout status deployment/hush --timeout=420s
current_image="$(deployment_image)"
[[ "$current_image" == "$new_image" ]] || {
  echo "Rollout image does not match the Artifact Registry digest." >&2
  exit 1
}
echo "Rollout ready: revision=$(deployment_revision) image=${new_image}"

check_public_ready "$HUSH_COMMIT_SHA"
check_authenticated_history

if [[ "$HUSH_FORCE_HEALTH_FAILURE" == "1" ]]; then
  echo "Controlled health-gate failure requested for rollback demonstration." >&2
  exit 42
fi

echo "Release verified: commit=${HUSH_COMMIT_SHA} image=${new_image} public_https=ready authenticated_history=passed"
