# Exact demo commands — Mac Terminal

Run every block below in **the same Mac Terminal window**, in order. These
commands use the repository and Google Cloud tools already on this Mac. Do not
use Google Cloud Shell for this recording: it has a different filesystem and
would need its own checkout and setup. Chrome displays every document and web
page; Mac Terminal is the only separate window used for commands.

No pod names, project names, hostname, or paths need replacing. The deletion
block chooses one healthy application pod automatically and prints its name.
Press **Ctrl-C** when instructed to stop a watch; then paste the next block.
Opening these notes does not run any command or resume cloud compute.

## 0 — Setup and resume — before recording

Open Applications → Utilities → Terminal. Copy this entire block, paste, and
press Return. Allow 30–60 minutes for preflight before the timed recording.

```bash
cd '/Users/ashrithvadde/Documents/EDSAI/Sem 3/Cloud Computing/Project/Hush'
gcloud container clusters get-credentials hush-m5 --region=us-central1 --project=hush-milestone-2-20260922
export HUSH_HOSTNAME='hush.34.36.104.111.nip.io'
export HUSH_EVIDENCE_DIR="$PWD/deliverables/Milestone5/evidence/recording-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$HUSH_EVIDENCE_DIR"
bash infra/milestone5/resume-demo.sh
```

Continue only when the helper finishes successfully. It restores two replicas,
waits for readiness, checks HTTPS/HTTP redirect, and runs a short transcription
check. The check creates one test history entry. Keep this Terminal window open
for the rest of the demo so the saved evidence-directory variable remains set.

## 1 — Clean baseline — before recording

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush delete job hush-load --ignore-not-found --wait=true
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get managedcertificate hush-cert-nip -o jsonpath='{.status.certificateStatus}{"\n"}'
```

Expected: exactly two Ready application pods, available HPA CPU metrics, and
certificate Active. After a rehearsal, let the HPA return to two before starting
the recording. Stop and correct preflight failures rather than continuing.

## 2 — HTTP redirects to HTTPS — 1:40–2:35

```bash
curl --connect-timeout 10 --max-time 15 -sS -o /dev/null -D - "http://${HUSH_HOSTNAME}/" \
  | tee "$HUSH_EVIDENCE_DIR/http-redirect.txt"
```

Show HTTP 301 and the HTTPS Location header. Show the browser's trusted
certificate and the Cloud Console's Active status separately in Chrome.

## 3 — Show and save the two replicas — 2:35

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-before.txt"
```

## 4 — Automatically select and delete one healthy pod — 2:35–4:15

Paste this whole block. It selects the oldest non-terminating Running/Ready
application pod only when exactly two healthy candidates exist. There is no
pod-name placeholder. It refuses to delete if selection fails.

```bash
HUSH_DELETE_POD="$(
  kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o json |
  python3 -c '
import json, sys
pods = [p for p in json.load(sys.stdin)["items"]
        if not p["metadata"].get("deletionTimestamp")
        and p.get("status", {}).get("phase") == "Running"
        and any(c.get("type") == "Ready" and c.get("status") == "True"
                for c in p.get("status", {}).get("conditions", []))]
if len(pods) != 2:
    sys.exit("Stopped: exactly two healthy application pods are required. Finish preflight first.")
print(min(pods, key=lambda p: (p["metadata"].get("creationTimestamp", ""), p["metadata"]["name"]))["metadata"]["name"])
'
)"
if [ -n "$HUSH_DELETE_POD" ]; then
  printf 'Automatically selected pod: %s\n' "$HUSH_DELETE_POD"
  kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pod "$HUSH_DELETE_POD" -o wide
  if kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush delete pod "$HUSH_DELETE_POD" --wait=false; then
    kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide --watch \
      | tee "$HUSH_EVIDENCE_DIR/pod-replacement-watch.txt"
  fi
fi
```

Keep the deletion and replacement visible live. Once the replacement's new name
is **1/1 Ready**, press **Ctrl-C**. The old pod may remain Terminating while it
drains; it is not an HPA scale-up. If the selector prints Stopped, finish preflight
and rerun this block; do not enter a pod name manually.

## 5 — Save the replacement result — before starting load

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-after.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
```

## 6 — Start actual load — 4:15–4:30

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush \
  | tee "$HUSH_EVIDENCE_DIR/hpa-before.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush apply -f infra/milestone5/demo/load-job.yaml
```

This starts a bounded real transcription load test. Its repeated sample entries
are expected load-test data. Show the clean dictation demonstration before this.

## 7 — Show separate health checks — 4:30–6:10

```bash
curl --connect-timeout 10 --max-time 15 -fsS "https://${HUSH_HOSTNAME}/health"
printf '\n'
curl --connect-timeout 10 --max-time 15 -fsS "https://${HUSH_HOSTNAME}/ready"
printf '\n'
```

Then return to Chrome to explain the essential GitHub manifest fields.

## 8 — Show autoscaling evidence — 6:10–7:55

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush top pods -l app=hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush describe hpa hush \
  | tee "$HUSH_EVIDENCE_DIR/hpa-events.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide
```

If the count is still changing, paste this watch block; press **Ctrl-C** once the
change is visible, then run block 9. There is no requirement to reach four if
the HPA has already changed two to three and the added replica is healthy.

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush --watch \
  | tee "$HUSH_EVIDENCE_DIR/hpa-watch.txt"
```

## 9 — Save scaling and show the PDB — 7:55–8:40

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush \
  | tee "$HUSH_EVIDENCE_DIR/hpa-after.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-after-scaling.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pdb hush
```

Return to Chrome for `pdb.yaml`, the analysis PDF, and the closing. Evidence files
are saved automatically in the timestamped directory set by block 0.

## 10 — Pause again — after recording and the access window

```bash
cd '/Users/ashrithvadde/Documents/EDSAI/Sem 3/Cloud Computing/Project/Hush'
kubectl config use-context gke_hush-milestone-2-20260922_us-central1_hush-m5
bash infra/milestone5/pause-demo.sh
```

Do not run this during the demo. Retained managed resources can still incur
charges after application replicas are paused.
