# Exact demo commands — Mac resume, Cloud Shell demonstration

**Use Mac Terminal only to resume before recording and pause afterward. Run
blocks 0–9 and 11 in the same Google Cloud Shell session in Chrome.** No Git
clone, repository checkout, virtual environment, or file upload is needed in
Cloud Shell. The load command uses the image already deployed in GKE.

Open Google Cloud Console, select `hush-milestone-2-20260922`, and click
**Activate Cloud Shell**. Expand it for readable on-camera output. Approve the
normal Google Cloud authorization prompt if shown.

The recording covers only required Milestone 5 proof: both slides, HTTPS and
redirect, two healthy replicas, live deletion/replacement, actual autoscaling,
separate health checks, the five committed manifest types, and the PDB analysis.
Skip the microphone demo, history tour, billing, IAM, database migration, and
Docker/build setup. Pod names are displayed automatically; none need typing.

Use v3.0.2 and the source permalink in the submission Word document. Earlier
rehearsal evidence is identified by its actual release. Check all four live
proofs using [the submission checklist](SUBMISSION_CHECKLIST.md).

## Mac only — resume before recording, outside the timer

Run this 30–60 minutes before the recording. Wait for it to finish successfully.

```bash
cd '/Users/ashrithvadde/Documents/EDSAI/Sem 3/Cloud Computing/Project/Hush'
bash infra/milestone5/resume-demo.sh
```

The helper restores two replicas and runs a short transcription check. That
check creates one test history entry. It is preflight, not part of the video.

## 0 — Cloud Shell connection only — before recording

Paste this in Cloud Shell after Mac resume has completed. Keep this same Cloud
Shell session open through evidence download so its variables remain available.

```bash
gcloud config set project hush-milestone-2-20260922
gcloud container clusters get-credentials hush-m5 --region=us-central1 --project=hush-milestone-2-20260922
export HUSH_HOSTNAME='hush.34.36.104.111.nip.io'
export HUSH_EVIDENCE_DIR="$HOME/hush-milestone5-evidence/recording-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$HUSH_EVIDENCE_DIR"
```

Expected Kubernetes context:
`gke_hush-milestone-2-20260922_us-central1_hush-m5`. This block does not change
the application replica count.

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
export HUSH_LOAD_IMAGE="$(kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush -o jsonpath='{.spec.template.spec.containers[0].image}')"
python3 - <<'HUSH_JOB' | kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush apply -f -
import json, os, sys
image = os.environ.get("HUSH_LOAD_IMAGE", "")
if not image:
    sys.exit("Stopped: could not read the deployed application image.")
container = {"name": "load", "image": image, "command": ["python", "scripts/milestone5_load.py"],
             "envFrom": [{"configMapRef": {"name": "hush-config"}}],
             "env": [{"name": k, "value": v} for k, v in {
                 "HUSH_LOAD_TARGET": "http://hush.hush.svc.cluster.local",
                 "HUSH_PUBLIC_HOST": "hush.34.36.104.111.nip.io",
                 "HUSH_LOAD_SECONDS": "180", "HUSH_LOAD_CONCURRENCY": "4"}.items()],
             "resources": {"requests": {"cpu": "250m", "memory": "512Mi"},
                           "limits": {"cpu": "250m", "memory": "512Mi"}}}
pod = {"restartPolicy": "Never", "serviceAccountName": "hush-runtime",
       "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10001},
       "containers": [container]}
print(json.dumps({"apiVersion": "batch/v1", "kind": "Job",
                  "metadata": {"name": "hush-load", "namespace": "hush", "labels": {"app": "hush-load"}},
                  "spec": {"backoffLimit": 0, "activeDeadlineSeconds": 240,
                           "ttlSecondsAfterFinished": 3600,
                           "template": {"metadata": {"labels": {"app": "hush-load"}}, "spec": pod}}}))
HUSH_JOB
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

Switch Chrome tabs to GitHub. Point briefly to the five required files:
Deployment, Service, Ingress, HPA, and PDB. Only explain their key fields.

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

Switch Chrome tabs for `pdb.yaml`, the analysis PDF, and the closing. Evidence files
are saved automatically in the timestamped directory set by block 0.

## 10 — Mac only: pause after recording and the access window

Return to **Mac Terminal**, outside the recording, and run:

```bash
cd '/Users/ashrithvadde/Documents/EDSAI/Sem 3/Cloud Computing/Project/Hush'
kubectl config use-context gke_hush-milestone-2-20260922_us-central1_hush-m5
bash infra/milestone5/pause-demo.sh
```

The application is intentionally unavailable while paused. Retained managed
resources may still incur charges. Use Cloud Shell block 11 to download its
captured evidence before closing that session.

## 11 — Download the captured evidence — after recording

Run this in the same session so the timestamped evidence path is still set.
The archive includes before/after pod output, HPA evidence, and redirect headers.

```bash
tar -czf "$HOME/hush-milestone5-evidence.tar.gz" -C "$HUSH_EVIDENCE_DIR" .
cloudshell download "$HOME/hush-milestone5-evidence.tar.gz"
```

Extract the downloaded archive on your Mac and use its fresh `pods-before.txt`
and `pods-after.txt` in the submission folder. Keep the HPA evidence with the
working artifacts. Do not substitute the old rehearsal outputs for this capture.

References: [launch Cloud Shell](https://docs.cloud.google.com/shell/docs/launching-cloud-shell)
and [download files](https://docs.cloud.google.com/shell/docs/using-cloudshell-command).
The older all-Mac command sheet is retained as an alternative, not the recording workflow.
