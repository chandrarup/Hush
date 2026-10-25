# Milestone 5: tabs, files, and a 9:45 recording

Prepared October 25, 2026. Use this run sheet for the recording sequence. The
[longer guide](Hush_Milestone5_10_Minute_Demo_Guide.md) provides expanded narration.
Use [the three-presenter notes](THREE_PRESENTER_NOTES.md) for the agreed role split:
Presenter 1 handles slides (0:00–1:40), Presenter 3 handles the demo (1:40–8:40),
and Presenter 2 handles the written analysis and closing (8:40–9:45).
Compute was paused after the successful native hotkey test; resume before use.
This document does not start the application or run a load test.

## Before the recording day

Use release **v3.0.2**, image digest
`sha256:946ba2c9d177aeade0a8980db8559692abc9a0e42ba773054eca00c83c30650d`.
The Word artifact document supplies the final source permalink. Original v3.0.1
rehearsal evidence remains labeled with its actual date and release. Use
[the recording/submission checklist](SUBMISSION_CHECKLIST.md) to verify the four
required live demonstrations before calling the video complete.

Rehearse the real replacement and autoscaling waits. This schedule allocates
about 100 seconds to replacement and gives the autoscaler approximately three
and a half minutes after load starts. Those are time allocations, not startup
guarantees. If a rehearsal exceeds them, resolve the delay or rebalance the
presentation before recording. Do not replace required live proof with old logs.

## Hybrid workflow: Mac resume, Cloud Shell demo

Resume and pause using the existing Mac scripts, outside the recording. Run the
live Kubernetes commands in Google Cloud Shell in Chrome. No Git clone is
needed: [the command page](http://127.0.0.1:57330/commands.html) includes an inline
load Job that uses the currently deployed image. It also selects a healthy pod
automatically. Only the connection and evidence-directory setup run in Cloud
Shell before recording.

## Open these screens in this order

| Screen | What to prepare | What you show |
| --- | --- | --- |
| 1. Chrome slides tab | <http://127.0.0.1:57330/slides.html>, views of the existing two-slide deck | Slide 1: topology. Slide 2: liveness versus readiness. |
| 2. Hush website | <https://hush.34.36.104.111.nip.io/>; authenticate privately before recording | Trusted HTTPS and certificate details. |
| 3. Google Cloud certificate | [Certificate details](https://console.cloud.google.com/security/ccm/lbCertificates/details/mcrt-fc66f5c5-065f-4592-ae83-f32c8d9b2aaa?project=hush-milestone-2-20260922) | The application's managed certificate says **Active**. If this saved console link changes, locate it through Network Security → Certificate Manager → Classic certificates. |
| 4. Cloud Shell | Same Cloud Shell session from setup onward, commands below ready to paste | Two healthy replicas, live deletion/replacement, probes, HPA, and evidence capture. |
| 5. GitHub | [Milestone 5 manifests](https://github.com/chandrarup/Hush/tree/codex/milestone5-gke/infra/milestone5), switched to the final published commit | The committed Deployment, Service, Ingress, certificate/redirect, HPA, and PDB. |
| 6. Chrome analysis tab | <http://127.0.0.1:57330/analysis.html> | The missing-PDB failure mechanism and the limits of our safeguard. |

All slides, documents, websites, and the Cloud Shell terminal are shown in
Chrome. Keep that same Cloud Shell session open; use Ctrl-C to leave
a watch before pasting the next command. The GKE cluster
overview, Cloud SQL, Storage, IAM, Billing, and Secret Manager do not need separate
tours in this milestone. A hotkey demonstration is not required for this recording.
The local dashboard is for setup; the cloud URL is the public application proof.

Chrome can show a site-controls icon instead of a literal padlock. Open its
connection/security details and show the certificate for the Hush hostname.

## Preflight: 30–60 minutes before recording, outside the timer

First run on **Mac Terminal**, outside the recording:

```bash
cd '/Users/ashrithvadde/Documents/EDSAI/Sem 3/Cloud Computing/Project/Hush'
bash infra/milestone5/resume-demo.sh
```

Then connect **Cloud Shell**, before the recording timer starts:

```bash
gcloud config set project hush-milestone-2-20260922
gcloud container clusters get-credentials hush-m5 --region=us-central1 --project=hush-milestone-2-20260922
export HUSH_HOSTNAME='hush.34.36.104.111.nip.io'
export HUSH_EVIDENCE_DIR="$HOME/hush-milestone5-evidence/recording-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$HUSH_EVIDENCE_DIR"
```

Expected context: `gke_hush-milestone-2-20260922_us-central1_hush-m5`.
The resume helper restores two replicas and runs a short transcription check;
that check creates a history entry. Wait for both Pods and load-balancer backends
to be ready. Mac resume, authentication, startup, and warm-up do not belong in the
10-minute recording.

Open the public Hush tab and authenticate privately if needed. The video focuses
on the browser's trusted HTTPS endpoint, not microphone setup or text insertion.

Prepare fresh evidence and a clean two-replica baseline:

```bash
export HUSH_HOSTNAME='hush.34.36.104.111.nip.io'
export HUSH_EVIDENCE_DIR="$HOME/hush-milestone5-evidence/recording-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$HUSH_EVIDENCE_DIR"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush delete job hush-load --ignore-not-found --wait=true
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get managedcertificate hush-cert-nip -o jsonpath='{.status.certificateStatus}{"\n"}'
```

After a rehearsal, let the HPA return to two automatically before the final
baseline. Ensure metrics are available and the certificate says Active.

The bounded load Job intentionally transcribes the same fixture repeatedly and
saves test entries. These can make history look repetitive again; they are
generated load, not repeated hotkey activation. Show the clean application demo
before starting load. Record the test interval so generated entries can be
identified later; preserve real dictations when cleaning up.

## Timed screen order and narration

| Time | Show and do | Explain |
| --- | --- | --- |
| 0:00–0:15 | Slide 1, introduce Hush | “We moved from manually managed compute to GKE replicas that recover and scale behind HTTPS.” |
| 0:15–1:00 | Slide 1 topology | Client → HTTPS load balancer → Ingress/Service-selected Pods → Cloud SQL and Cloud Storage. Two replicas, HPA, and PDB. Ingress defines routing; it is not another application container. |
| 1:00–1:40 | Slide 2 | `/health` checks the running API only; failure can restart the container. `/ready` checks database and serving dependencies; failure removes the replica from traffic. Database trouble should not cause restart storms. |
| 1:40–2:35 | HTTPS website, certificate details, Active console status, Cloud Shell redirect response | Show the trusted hostname, Active certificate, and HTTP 301 to HTTPS. Omit the microphone/history demo. |
| 2:35–4:15 | Terminal: two Ready Pods, delete one live, watch a different Pod become Ready | The Deployment recreates a missing replica without a manual start/scale command. Explain readiness and graceful draining while waiting. Save before/after output. |
| 4:15–4:30 | Start the bounded load Job; capture initial HPA state | “This sends real transcription requests. We will return to the HPA while it responds to CPU load.” |
| 4:30–6:10 | Live probe responses, then GitHub manifest snippets | Show the two endpoint responses, their probe mapping, replicas/image/rolling strategy, Service selector, Ingress host, certificate redirect, and HPA settings. Keep each file focused on the listed fields. |
| 6:10–7:55 | Terminal: CPU metrics, HPA events/count, actual Ready application Pods | Show an actual change from the saved baseline of two to three or four. Show the controller's scaling event and healthy added Pods. The load Job is not an app replica. |
| 7:55–8:40 | GitHub `pdb.yaml`, live PDB, Deployment strategy | At most one unavailable Pod during voluntary eviction; rollout uses separate `maxUnavailable: 0`, `maxSurge: 1`. Direct deletion bypasses PDB and demonstrates replacement. |
| 8:40–9:15 | Half-page PDF | Without PDB, overlapping evictions may leave no Ready backend, producing intermittent 503s; interrupted connections can also produce 502s. Explain our mitigation and its limits without inventing an observed outage. |
| 9:15–9:35 | Analysis PDF | Explain the earlier eviction test and limits of the evidence. Do not spend recording time touring the submission folder. |
| 9:35–9:45 | Slide 1 or website | Close with the observed results: healthy replicas, automatic replacement, real autoscaling, valid HTTPS, redirect, separate health checks, and committed manifests. |

The remaining 15 seconds are a buffer. Avoid reading command syntax aloud. The
three-presenter role split is above; presenter names can be assigned later.

### HTTPS proof: 1:40–2:35

```bash
curl --connect-timeout 10 --max-time 15 -sS -o /dev/null -D - "http://${HUSH_HOSTNAME}/" \
  | tee "$HUSH_EVIDENCE_DIR/http-redirect.txt"
```

Point to **301** and **Location: https://hush.34.36.104.111.nip.io/**. Also type the
explicit `http://` URL in the browser and show it ending at HTTPS. The terminal
proves server redirection even when the browser independently upgrades HTTP.
Do not use `-L` for this proof or bypass certificate checks.

### Live deletion and replacement: 2:35–4:15

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-before.txt"
```

Paste the following block as-is. It selects one healthy pod automatically,
prints the selected name, and refuses deletion unless two healthy candidates
exist. No pod name needs typing:

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

Keep the command and new Pod visible until the replacement is Ready. Exit the
watch with Ctrl-C, then save the result before starting load:

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-after.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
```

The old Pod can remain Terminating during its drain interval (grace is 210
seconds). Two Ready Pods plus one old Terminating Pod is replacement, not HPA
scale-up. Save another snapshot after the old Pod disappears if necessary.
Do not use forced deletion or manually create the replacement.

### Start load: 4:15–4:30

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

The Job runs four workers for 180 seconds, with a 240-second active deadline.
It is separate from normal application deployment and obtains credentials
privately. Do not show secret values or token retrieval on camera.

### Probes: 4:30–6:10

```bash
curl --connect-timeout 10 --max-time 15 -fsS "https://${HUSH_HOSTNAME}/health"
printf '\n'
curl --connect-timeout 10 --max-time 15 -fsS "https://${HUSH_HOSTNAME}/ready"
printf '\n'
```

Show actual results: `/health` confirms API life; `/ready` checks database,
storage, loaded credentials, and the warmed model. Point to the two probe paths
in `deployment.yaml`. Do not disrupt the shared database during the recording.

### Autoscaling proof: 6:10–7:55

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush top pods -l app=hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush describe hpa hush \
  | tee "$HUSH_EVIDENCE_DIR/hpa-events.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide
```

If the count is still changing, run the watch and exit with Ctrl-C when done:

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush --watch \
  | tee "$HUSH_EVIDENCE_DIR/hpa-watch.txt"
```

Then capture the actual final state:

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush \
  | tee "$HUSH_EVIDENCE_DIR/hpa-after.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-after-scaling.txt"
```

Say the observed values, not a promised maximum. A successful change to three is
enough; do not claim four unless four actually exist. Configuration alone, high
CPU alone, Pending Pods alone, or a manual scale command is not the required
autoscaling demonstration. The return to two can happen after the recording.

### PDB: 7:55–8:40

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pdb hush
```

With two healthy replicas, `maxUnavailable: 1` permits one voluntary eviction and
protects the other. It is not a guarantee against direct deletion, abrupt node
loss, database outages, or interrupted streaming sessions. The earlier eviction
test and its report are supporting historical evidence, not today's deletion.

## Files to explain; keep the rest closed

| File | Fields and message | When |
| --- | --- | --- |
| `infra/milestone5/deployment.yaml` | `replicas: 2`, pinned image, `/health` versus `/ready`, startup probe; later `maxUnavailable: 0`, `maxSurge: 1`, drain/grace. | 4:30–6:10 and 7:55–8:40 |
| `infra/milestone5/service.yaml` | `app: hush` selects the replicas; Service port 80 maps to the app's HTTP port; NEG integrates Pod endpoints with the GKE load balancer. | 4:30–6:10 |
| `infra/milestone5/ingress.yaml` | Public hostname, `/` routing to Service `hush`, certificate and FrontendConfig references. | 4:30–6:10 |
| `infra/milestone5/certificate.yaml` | ManagedCertificate hostname and `redirectToHttps.enabled: true` in FrontendConfig. | 4:30–6:10 |
| `infra/milestone5/hpa.yaml` | CPU target 60%, minimum 2, maximum 4; controller changes replicas under load. | 4:30–6:10, followed by live proof |
| `infra/milestone5/pdb.yaml` | `maxUnavailable: 1`, selector `app: hush`, voluntary eviction scope. | 7:55–8:40 |

The five rubric-required manifest types are Deployment, Service, Ingress, HPA,
and PDB. The certificate file explains the separate HTTPS/redirect requirement.
Do not tour Dockerfiles, Cloud Build, full Python source, migrations, old VM
setup, or permission settings. Keep the load Job ready as a command, not a long
code explanation. If asked how readiness checks the DB, the handlers are in
`voiceflow/web/api_server.py`; the normal recording does not need a source tour.

## After recording

1. Review the video: the deletion command and Ready replacement must be live;
   HPA must actually change replica count; HTTPS, redirect, both health checks,
   and committed manifests must be visible. Keep the total at or below 10:00.
2. Replace the submission folder's `pods-before.txt` and `pods-after.txt` with the
   recording's fresh outputs. Keep HPA evidence with the committed working
   artifacts. Retain the Active certificate screenshot, or refresh it if needed.
3. Keep the existing submission folder focused on required artifacts. This run
   sheet and the expanded guide are presenter notes, not additional submissions.
4. Once the access window is over, pause again from the repository root:

```bash
cd '/Users/ashrithvadde/Documents/EDSAI/Sem 3/Cloud Computing/Project/Hush'
kubectl config use-context gke_hush-milestone-2-20260922_us-central1_hush-m5
bash infra/milestone5/pause-demo.sh
```

Do not pause during the recording or an agreed instructor access window.
