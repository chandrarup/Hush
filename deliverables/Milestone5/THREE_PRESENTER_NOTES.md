# Hush Milestone 5 — three presenter notes

Prepared October 25, 2026. Target: **9:45 total**, with 15 seconds of buffer.

Roles follow the requested responsibilities. **Speaking order: Presenter 1 →
Presenter 3 → Presenter 2.** This keeps the entire live demonstration together.
Presenter names can be added later.

| Presenter | Responsibility | Recording time | Duration |
| --- | --- | --- | --- |
| Presenter 1 | Both PowerPoint slides and introduction | 0:00–1:40 | 1:40 |
| Presenter 3 | Website, live Kubernetes demonstration, and manifests | 1:40–8:40 | 7:00 |
| Presenter 2 | Written analysis, evidence limits, and closing | 8:40–9:45 | 1:05 |

The longer demo allocation includes real commands and replacement/scaling waits;
it does not require seven minutes of continuous speech. Rehearse with actual
cloud response times. Keep speaker notes on a second screen or outside the
shared window; show every slide, document, and website in Chrome. Switch to the Cloud Shell browser tab for on-camera command blocks.

## Chrome tabs and the terminal

Resume and pause from **Mac Terminal**, outside the timed recording. Use
**Google Cloud Shell in Chrome** for the live Kubernetes commands. No repository
clone or file upload is needed there. Keep the same Cloud Shell session open.
The native microphone/history demonstration is optional and omitted from this
rubric-focused recording.

Open these Chrome tabs:

- [Slides 1 and 2](http://127.0.0.1:57330/slides.html).
- [Hush website](https://hush.34.36.104.111.nip.io/).
- [Active certificate](https://console.cloud.google.com/security/ccm/lbCertificates/details/mcrt-fc66f5c5-065f-4592-ae83-f32c8d9b2aaa?project=hush-milestone-2-20260922).
- [GitHub manifests](https://github.com/chandrarup/Hush/tree/codex/milestone5-gke/infra/milestone5).
- [Written-analysis PDF](http://127.0.0.1:57330/analysis.html).
- [Submission artifacts](http://127.0.0.1:57330/artifacts.html) — preparation only; do not tour this page during the video.
- [Numbered terminal commands](http://127.0.0.1:57330/commands.html) and these notes.

The slides are views of the existing two-slide deck. The PDF is the existing
submission PDF. No upload to Google Slides or another service is required.

## Setup — do not read this on camera

- Resume outside the timer, 30–60 minutes before recording. The last verified
  standby had zero application replicas. These notes do not resume anything.
- Run setup and baseline blocks below in the same Cloud Shell window. All
  commands are also on the numbered command page; no pod names need typing.
- Privately authenticate the Hush browser tab; make one physical Left Control
  test in a blank text field, then wait for Idle.
- Show two Ready application replicas and usable HPA metrics before recording.
  Remove a completed previous `hush-load` Job during preflight so it can run anew.
- Use v3.0.2 and the source permalink in the submission Word document. Keep
  earlier v3.0.1 rehearsal evidence identified as historical. Check
  [all four live recording proofs](SUBMISSION_CHECKLIST.md) before submission.
- The load Job deliberately repeats sample audio and creates test transcripts.
  Show the clean application test first; identify load-test entries separately.
- Have the two-slide PPT, Hush website, certificate console, GitHub manifests,
  Cloud Shell and the Chrome analysis/artifact tabs ready. No secret or billing
  pages should be shown.

### Mac Terminal: resume first, outside the timer

```bash
cd '/Users/ashrithvadde/Documents/EDSAI/Sem 3/Cloud Computing/Project/Hush'
bash infra/milestone5/resume-demo.sh
```

### Cloud Shell: connect before recording

Run this after the Mac resume helper succeeds. This block only connects Cloud
Shell to the cluster and creates an evidence directory; it does not resume or
scale the application. Keep this same Cloud Shell session open afterward.

```bash
gcloud config set project hush-milestone-2-20260922
gcloud container clusters get-credentials hush-m5 --region=us-central1 --project=hush-milestone-2-20260922
export HUSH_HOSTNAME='hush.34.36.104.111.nip.io'
export HUSH_EVIDENCE_DIR="$HOME/hush-milestone5-evidence/recording-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$HUSH_EVIDENCE_DIR"
```

### Verify the clean baseline before recording

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush delete job hush-load --ignore-not-found --wait=true
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get managedcertificate hush-cert-nip -o jsonpath='{.status.certificateStatus}{"\n"}'
```

## Presenter 1 — PowerPoint — 0:00–1:40

### 0:00–0:15 — Introduction

**Show:** The Chrome slides tab, slide 1. Start the recording timer.

**Say:**

“Hush is our push-to-talk transcription application. For Milestone 5, we moved
from manually managed compute to GKE. We will show healthy replicas, automatic
replacement, autoscaling, and a public HTTPS endpoint.”

### 0:15–1:00 — Slide 1: orchestration topology

**Show:** Point along the request path, then to the database, storage, HPA, and PDB.

**Say:**

“The client reaches our public HTTPS load balancer. The Ingress defines the
hostname and routing, and the Service selects the Hush pods. The load balancer
uses those selected pod endpoints. Each replica runs the same versioned API and
speech model.

“History and application state are stored in Cloud SQL. Audio files are stored
in Cloud Storage, so replacing a pod does not remove that managed data. The HPA
keeps at least two replicas during the demo and can grow to four under CPU load.
The disruption budget limits overlapping maintenance evictions.”

### 1:00–1:40 — Slide 2: health probes and handoff

**Show:** Point to the liveness and readiness columns and their failure actions.

**Say:**

“Liveness uses `/health` to check whether the API responds, without querying the
database. Repeated failure can restart the container.

“Readiness uses `/ready` to check the database and other serving dependencies.
Failure removes the replica from traffic while it recovers. A database outage
should not restart every healthy application process. A startup probe gives
initialization time to finish.

“I’ll hand over to our demo presenter to show this configuration working.”

**Handoff:** Presenter 3 takes over at 1:40. Presenter 1 does not explain the
YAML or repeat the live demonstration.

## Presenter 3 — live demo — 1:40–8:40

### 1:40–2:35 — Trusted HTTPS and the HTTP redirect

**Show:** Hush at <https://hush.34.36.104.111.nip.io/>. Open the browser's security
details and certificate, then the Google Cloud certificate tab showing Active.

**Say:**

“This is Hush on our free public hostname. The browser trusts its certificate,
and Google Cloud reports the application certificate as Active. We did not need
to buy a domain.”

**Run in the prepared terminal:**

```bash
curl --connect-timeout 10 --max-time 15 -sS -o /dev/null -D - "http://${HUSH_HOSTNAME}/" \
  | tee "$HUSH_EVIDENCE_DIR/http-redirect.txt"
```

**Point to:** HTTP 301 and the HTTPS Location header. Type the explicit HTTP
address in the browser and show the final HTTPS address.

**Say:**

“This HTTP 301 response points to the same hostname over HTTPS. The browser
trusts the certificate, and the managed certificate is Active. We will now show
that the application runs as healthy replicas.”

### 2:35–4:15 — Two replicas and live automatic replacement

**Run:**

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-before.txt"
```

**Say:**

“These are two separate Hush replicas, both Running and Ready. The Deployment
requests two. I will delete exactly one existing pod, and the controller should
create its replacement automatically.”

**Paste the whole block below. It selects and prints one healthy pod
automatically; there is no name to replace. It stops if exactly two healthy
candidates are not available.**

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

**Say while the watch is visible:**

“This new name identifies a different pod. We have not created it manually or
changed the desired replica count. The other replica remains available while
the replacement starts. Readiness determines when the replacement can serve.

“The old pod may remain Terminating while its connections drain. That extra
terminating row is not an autoscaler increase.”

**Once the replacement is Ready:** Press Ctrl-C and run:

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-after.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
```

**Say:**

“We have restored two healthy replicas through automatic replacement. These
before-and-after outputs are also part of our working artifacts.”

**If more waiting narration is useful, substitute this within the time block:**

“The application image includes its speech model. Durable history and audio are
outside the pod, in managed services. Replacement therefore restores compute
without requiring us to copy data from the deleted pod.”

**Timing rule:** Rehearse this wait beforehand. An unready replacement does not
complete the demonstration. Do not force-delete or manually start a replacement.

### 4:15–4:30 — Start the bounded load

**Run:**

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

**Say:**

“This temporary Job sends real transcription requests for three minutes. We
have captured the two-replica baseline. While CPU load builds, I’ll show the
health checks and committed configuration.”

### 4:30–6:10 — Probe responses and essential files

**Run:**

```bash
curl --connect-timeout 10 --max-time 15 -fsS "https://${HUSH_HOSTNAME}/health"
printf '\n'
curl --connect-timeout 10 --max-time 15 -fsS "https://${HUSH_HOSTNAME}/ready"
printf '\n'
```

**Say:**

“These are actual responses from two separate endpoints. Liveness confirms the
API responds. Readiness also checks the database, storage, loaded credentials,
and initialized model. That separates a stuck process from a temporary
dependency problem.”

**Switch to GitHub at the final published commit. Explain only these fields:**

- `deployment.yaml`: “Two replicas, one pinned image, and separate `/health`
  liveness and `/ready` readiness probes.”
- `service.yaml`: “The selector connects the Service to the Hush application
  pods; port 80 maps to the application HTTP port.”
- `ingress.yaml`: “The public hostname and path route to this Service.”
- `certificate.yaml`: “The managed certificate covers that hostname, and the
  FrontendConfig enables the HTTPS redirect.”
- `hpa.yaml`: “The CPU target is 60 percent, with a minimum of two and a maximum
  of four replicas.”

Point only to those essential fields. Do not read YAML line by line or show
credentials. The additional infrastructure files do not need a separate tour.

### 6:10–7:55 — Actual autoscaling

**Run:**

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush top pods -l app=hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush describe hpa hush \
  | tee "$HUSH_EVIDENCE_DIR/hpa-events.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide
```

**If still changing, watch:**

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush --watch \
  | tee "$HUSH_EVIDENCE_DIR/hpa-watch.txt"
```

**Say, using only the actual observed values:**

“Our baseline was two. CPU increased under transcription load, and this HPA
event records the controller's scaling decision. The count is now [actual
count], and [actual Ready count] application pods are healthy. We did not run a
manual scale command. The load-generator pod is separate from these replicas.

“The maximum of four bounds growth. After load ends, the stabilization window
delays scale-down to avoid rapid changes. The minimum remains two while active.”

**Exit the watch with Ctrl-C. Save:**

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush \
  | tee "$HUSH_EVIDENCE_DIR/hpa-after.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-after-scaling.txt"
```

**Timing rule:** A change to three is sufficient; do not wait for four merely
because four is the maximum. Show both the count change and healthy added
replicas. Capture the return to two after recording if it takes longer.

### 7:55–8:40 — PDB and handoff

**Show:** GitHub `pdb.yaml`, then the Deployment's rollout strategy. Run:

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pdb hush
```

**Say:**

“Our PodDisruptionBudget allows at most one unavailable pod during voluntary
eviction. With two healthy replicas, it protects the remaining one during
maintenance. Rolling updates use a separate strategy: zero unavailable replicas
and one extra pod.

“The direct deletion earlier bypasses PDB; it proved automatic replacement. The
budget addresses eviction-based maintenance. I’ll hand over to our analysis
presenter to explain the failure this helps prevent.”

**Handoff:** Presenter 2 takes over at 8:40. Keep the live evidence visible long
enough for the recording to show it. No further destructive tests are needed.

## Presenter 2 — written analysis and closing — 8:40–9:45

### 8:40–9:15 — Explain the half-page analysis

**Show:** The written-analysis PDF tab in Chrome.

**Say:**

“Without a disruption budget, overlapping maintenance evictions can remove both
replicas before replacements are ready. With no usable backend, requests may
receive intermittent 503 responses; interrupted connections may also cause 502s.

“Our design combines two minimum replicas, one allowed unavailable pod during
eviction, readiness checks, and graceful draining. Our earlier eviction test
rejected a second overlapping eviction. This supports that safeguard; it does
not mean PDB prevents direct deletion, database outages, or every node failure.”

### 9:15–9:35 — Explain the evidence and its limits

**Show:** Keep the analysis PDF visible in Chrome. No submission-folder tour.

**Say:**

“An earlier test allowed one eviction and blocked a second overlapping eviction.
We did not observe HTTP 5xx, but transport errors occurred. This supports the
tested safeguard, not a zero-downtime claim.”

### 9:35–9:45 — Close

**Show:** The Chrome slides tab or Hush website. Only use this statement if the required live
proofs have actually succeeded.

**Say:**

“Hush now demonstrates managed replicas, automatic recovery, autoscaling, and
trusted HTTPS. The committed configuration and captured evidence support these
results. Thank you.”

**Stop:** End at 9:45, never beyond 10:00. The 15-second buffer includes small
handoff delays; it is not another presentation section.

## After the recording — demo presenter

Review the video before submission. Replace the submission folder's before/after
pod outputs with this recording's fresh captures. Keep HPA evidence with the
repository artifacts. Return to Mac Terminal and pause only after the demo and any agreed access window:

```bash
cd '/Users/ashrithvadde/Documents/EDSAI/Sem 3/Cloud Computing/Project/Hush'
kubectl config use-context gke_hush-milestone-2-20260922_us-central1_hush-m5
bash infra/milestone5/pause-demo.sh
```

Keep these presenter notes in the repository; they are not additional required
submission artifacts. Do not add them to the six-file submission folder.


After recording, download the evidence using block 11 on the numbered Cloud
Shell command page. Cloud Shell files are not automatically saved on your Mac.
The Mac still runs the native hotkey client and local browser document preview.
