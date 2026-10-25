# Hush Milestone 5: 10-minute recording guide

**Recording preparation, updated October 25.** Use [the current run sheet](DEMO_RUN_SHEET.md)
for the tab order, revised 9:45 schedule, commands, and release-alignment checks.
The current local manifests select `v3.0.2`; its changes still need publication
at preparation time. `LIVE_DEPLOYMENT.md` and the earlier rehearsal evidence
describe `v3.0.1`. The video itself still needs live deletion and scaling.
Presenter assignments are intentionally open; assign these sections later.

## Timing and recording rules

Target a natural **9:45 recording**, leaving 15 seconds under the inherited
10-minute ceiling. Rehearse with actual cloud timing. The narration below is a
starting script; use the remaining time for visible results and explanations,
not silent waiting or reading command syntax aloud.

| Time | Screen/action | Proof |
| --- | --- | --- |
| 0:00–0:20 | Introduction | Hush and the Milestone 4 → 5 change |
| 0:20–1:10 | Slide 1 | Orchestration topology |
| 1:10–1:55 | Slide 2 | Different liveness/readiness decisions |
| 1:55–2:55 | Browser + terminal | Trusted HTTPS, real HTTP redirect, short upload |
| 2:55–4:50 | One terminal | Two healthy replicas; live deletion and automatic replacement |
| 4:50–5:05 | Start bounded load Job | Establish real application load |
| 5:05–6:00 | Probe responses + configuration | App alive versus dependencies ready |
| 6:00–6:35 | Dashboard + saved pod output | History survives replacement; final replacement snapshot |
| 6:35–8:00 | HPA/metrics/watch | Autoscaler changes count; added Pods become Ready |
| 8:00–8:45 | GitHub manifests + PDB | Submitted configuration is committed |
| 8:45–9:30 | Analysis or Slide 1 | Missing-PDB failure mechanism and limits |
| 9:30–9:45 | Application/closing | Connect the completed evidence to the objective |

The required deletion sequence must be visible live: the selected existing Pod,
the deletion command, and the new automatically created Pod. Never substitute
a screenshot, a previously recorded replacement, or a manual rollout. Aim to
show scaling live too. Save historical scaling evidence as backup documentation,
not as a substitute for visibly showing the replica count change.

## Before recording: complete every item

1. Complete the implementation plan's acceptance tests. Leave two Ready replicas
   after rehearsal; wait for HPA to return them to two automatically. If compute
   was paused, resume it 30–60 minutes before recording and verify a successful
   warm-up transcription. The two-replica minimum applies while the demo is live.
2. Provision HTTPS at least a day earlier. The certificate must already say
   **Active**, and the exact final hostname must work on the recording network.
3. Freeze one published deployed commit, `v3.0.2` image tag and actual digest. Prepare a
   release card containing project, cluster, region, namespace, hostname, commit,
   image tag/digest, and evidence date. No credentials belong on this card.
4. Authenticate the browser privately. Confirm history loads, the token is gone
   from the visible URL, and the dashboard is served at the free public HTTPS
   hostname. Set cleanup to None before recording.
5. Prepare a short WAV: mono, 16-bit PCM, 16 kHz, with an identifiable
   Milestone sentence. The verified rehearsal sample is about eight seconds.
   Verify an upload in rehearsal. Use a separate filename
   for the recording's fresh request.
6. Load Job readiness: its image is already available, its sample is in private
   storage, token retrieval is silent, its concurrency/duration are bounded, and
   it has proved a 2 → 3/4 scaling event in rehearsal. Its manifest must not be
   part of the normal always-on deployment apply set.
7. Confirm the selected `kubectl` context is the intended Hush cluster. Do not
   run a destructive demo against whichever cluster happens to be current.
8. Remove the completed rehearsal load Job before the timer starts. Preserve
   its useful logs elsewhere. Confirm no load generator remains running.
9. Open windows in this order: the two-slide Chrome slides tab; authenticated HTTPS
   dashboard; browser certificate details; GKE certificate status; one terminal;
   GitHub submitted commit/manifests; half-page analysis. Close secret/billing
   pages. Keep cameras visible during each speaker's portion under the inherited
   course workflow. Assign camera and screen-share handoffs in rehearsal.
10. In the one visible terminal, define the following values privately from the
    release card. The hostname below is the actual selected deployment address:

```bash
export GOOGLE_CLOUD_PROJECT=hush-milestone-2-20260922
export HUSH_HOSTNAME='hush.34.36.104.111.nip.io'
export HUSH_EVIDENCE_DIR="$PWD/deliverables/Milestone5/evidence/final-recording"
mkdir -p "$HUSH_EVIDENCE_DIR"
kubectl config current-context
```

11. Prepare a background, unauthenticated public `/health` request monitor before
    recording. It should save timestamps, HTTP status and transport failures
    throughout deletion/scaling. Review the results afterward; do not claim
    uninterrupted service without measured evidence.
12. Rehearse with a timer. If normal replacement/scaling does not fit, fix startup
    and scheduling or rebalance the talk before the final recording. Do not
    discover these waits on camera.

## 0:00–0:20 — Introduction

**Show:** Slide 1.

**Say:**

“Hush is our push-to-talk transcription application. In Milestone 4, we moved
its durable state into managed services, but a person still had to recover the
VM. Milestone 5 gives compute management to GKE. We will demonstrate healthy
replicas, automatic replacement, scaling under real load, and a public HTTPS
endpoint.”

## 0:20–1:10 — Slide 1: topology

**Point:** Client → HTTPS load balancer; Ingress/Service; the two Pod replicas;
Cloud SQL and Cloud Storage. Then indicate the HPA and PDB annotations.

**Say:**

“The browser and native client now use this public hostname. The load balancer
terminates trusted HTTPS, and HTTP requests redirect to HTTPS. Our Ingress
defines routing, and the Service selects the Hush replicas. The load balancer
uses those selected Pod endpoints; Ingress is configuration, rather than an
extra application container.

“Each Pod runs the same versioned Hush API and Whisper image. Both use the
existing private Cloud SQL database and private Cloud Storage bucket. Secrets
remain in Secret Manager, accessed through workload identity. We keep at least
two replicas, and the autoscaler can add replicas under CPU load. The disruption
budget limits simultaneous maintenance evictions.”

## 1:10–1:55 — Slide 2: health probes

**Point:** The liveness column, the readiness column, then their failure actions.

**Say:**

“Liveness asks whether the app can respond. Our `/health` endpoint does not
query the database. Repeated liveness failures allow Kubernetes to restart the
container.

“Readiness asks whether this replica can serve a request successfully. Our
`/ready` endpoint checks the database with a small query, verifies storage
access, confirms the token is loaded, and checks model initialization. A
readiness failure removes the Pod from serving traffic while it recovers.

“A database outage should therefore make readiness fail without causing every
healthy application process to restart. A startup probe protects initialization,
and readiness also becomes false when a Pod starts draining.”

## 1:55–2:55 — HTTPS, actual redirect, and application request

**Show:** The authenticated browser at `https://<final-hostname>/`.

**Do:** Open the browser's site security indicator and certificate details.
Show a secure connection, the certificate's matching hostname, issuer, and
valid dates. Modern browsers may use a site-controls icon instead of a literal
padlock. Also show the GKE ManagedCertificate page with **Active**, not merely
the provider's own website certificate.

**Say:**

“This is Hush at our public HTTPS hostname. We used free DNS and a managed
certificate, so we did not purchase a domain. The browser trusts this
certificate, and GKE reports the application's certificate as Active.”

**Run in the prepared terminal:**

```bash
curl --connect-timeout 10 --max-time 15 -sS -o /dev/null -D - "http://${HUSH_HOSTNAME}/" \
  | tee "$HUSH_EVIDENCE_DIR/http-redirect.txt"
```

**Expected:** HTTP response 301; `Location` starts with the same hostname over
HTTPS; HTTPS `/health` returns `{"status":"ok"}`. There is no `-L` in the first
command and no certificate-check bypass in either command.

**Do:** Type the explicit `http://` address in the browser and show the final
HTTPS address. The terminal response proves a server redirect even if the
browser independently upgrades insecure navigation.

**Say:**

“The HTTP response itself redirects to the secure address. This is separate
from the browser choosing to upgrade a URL.”

**Do:** Upload the short recording through Diagnostic audio upload. Show its
fresh transcript/history entry. Keep the demo short; the full native hotkey/WSS
workflow is a preflight acceptance test and an optional addition only if timing
permits. Never describe a file upload as live microphone capture.

## 2:55–4:50 — Two replicas and live self-healing

**Run:**

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-before.txt"
```

**Expected:** At least two application Pods Running and Ready, with the
Deployment reporting two available replicas. The load Job must not match
`app=hush`; it must never be counted as an application replica.

**Say:**

“These are two healthy instances of the same application. Their different names
and UIDs identify separate Pods. I will now delete exactly one existing Pod.
The Deployment still requests two replicas, so its controller should create
a replacement automatically.”

**Paste the automatic selection/deletion block below in Cloud Shell. No pod name needs copying:**

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

**Do:** Leave the command and live watch visible. Point to the new name and its
transition to Running/Ready. The old Pod can remain Terminating during the
draining interval. Two Ready Pods plus an old Terminating Pod is not an HPA
scale-up; explain the difference. When the replacement is Ready, press Ctrl-C
to exit the watch and continue using the same terminal.

**Say while observing:**

“The deleted Pod is leaving service, and this new Pod has a different identity.
We did not create it or manually scale the Deployment. The remaining healthy
replica serves requests while the replacement initializes. The terminating
process stays alive briefly to let load-balancer connections drain.”

**Say once the replacement is Ready:**

“The desired replica count stayed at two. We restored two healthy replicas
through replacement, rather than an operator starting another container.”

If no replacement becomes Ready, stop and fix the issue. A perpetually Pending
or unready replacement does not complete this proof.

## 4:50–5:05 — Start real load

**Run the planned, previously tested Job manifest:**

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

“This temporary Job sends real audio transcription requests to the Service.
It runs for a bounded interval and retrieves its credentials privately. We
are not changing the replica count manually. We will return to the CPU metrics
and autoscaler after they have had time to respond.”

## 5:05–6:00 — Show the separate checks

**Run:**

```bash
curl --connect-timeout 10 --max-time 15 -fsS "https://${HUSH_HOSTNAME}/health"
printf '\n'
curl --connect-timeout 10 --max-time 15 -fsS "https://${HUSH_HOSTNAME}/ready"
printf '\n'
```

**Expected:** `/health` reports alive. `/ready` reports managed mode and healthy
database, storage, loaded token and model checks. The Deployment assigns
`/health` to liveness and `/ready` to readiness. Use actual responses from the
implemented release; do not paste a canned success response into evidence.

**Show:** The committed small handler definitions or probe YAML if useful.

**Say:**

“These are separate endpoints with separate failure decisions. The first
confirms that the app responds. The second has checked the database and the
other prerequisites needed to accept work. A failed readiness check withdraws
that replica from service; it should not trigger a restart storm during a
database outage. Our rehearsal tests verified that behavior after startup.
We are keeping the live database available during this recording.”

Only say the rehearsal sentence if the test has actually passed. Do not break
the shared Cloud SQL instance on camera just to manufacture a probe failure.

## 6:00–6:35 — Durable state and final replacement evidence

**Show:** Refresh History in the public dashboard. Point to the identifiable
transcription created earlier. Background load entries may also be present;
do not confuse one of them with the earlier request.

**Say:**

“The earlier transcription is still present after replacing compute. Its
history is stored in Cloud SQL and its uploaded audio is in Cloud Storage.
Neither depends on the deleted Pod's filesystem. Refreshing history also works
when the browser request reaches a different replica.”

**Run:**

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide \
  | tee "$HUSH_EVIDENCE_DIR/pods-after.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
```

**Point:** Identify the Ready replacement and check the original Pod's actual
state. Termination may take up to the configured 210-second grace period. If
the original still says Terminating, explain that and save another snapshot
after it disappears, before the closing section. If HPA has already added Pods,
state that the extra replicas belong to the scaling test started after the
deletion. Save the deletion-specific watch output as well so the two
demonstrations remain distinguishable.

## 6:35–8:00 — Actual autoscaling

**Run:**

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush top pods -l app=hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get hpa hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush describe hpa hush \
  | tee "$HUSH_EVIDENCE_DIR/hpa-events.txt"
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get deployment hush
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pods -l app=hush -o wide
```

If scaling is still occurring, show `kubectl -n hush get hpa hush --watch`, then
exit with Ctrl-C and show the resulting Ready application Pods. Avoid repeatedly
switching windows during the transition.

**Say using the actual observed values:**

“Our baseline was two replicas. CPU utilization rose under transcription load,
and the HPA compared that utilization with its 60-percent target. This event
records the controller's scaling decision. The count is now [actual count],
and these [actual Ready count] Pods are healthy. The additional Pod has its own
name and UID. We did not run a manual scale command.”

**Then:**

“The maximum is four, which bounds compute growth. When the Job stops and load
drops, the stabilization window delays scale-down to prevent rapid changes.
The minimum remains two. We capture the eventual return to two after the
recording; it does not have to consume this ten-minute demonstration.”

**Capture:** Save final HPA and pod output, the load Job completion/log summary,
and a clean screenshot. A configured HPA, high CPU alone, a desired count with
only Pending Pods, or a manual `kubectl scale` is insufficient evidence.

## 8:00–8:45 — Committed artifacts and disruption budget

**Show:** GitHub at the submitted commit. Point to the five required manifest
files: Deployment, Service, Ingress, HPA, PDB. Open PDB and Deployment strategy.

**Run if terminal proof is clearer:**

```bash
kubectl --context=gke_hush-milestone-2-20260922_us-central1_hush-m5 -n hush get pdb hush
```

**Say:**

“These manifests are committed to the repository, rather than existing only in
our local folder. The disruption budget allows at most one unavailable Pod
during eviction-based maintenance. With two healthy replicas, this permits one
maintenance eviction while protecting the remaining one. During a rolling
application update, the Deployment's separate strategy allows no unavailable
replicas and one additional Pod.”

**Then:**

“The direct deletion shown earlier bypasses the disruption budget. That test
proved automatic replacement. The budget protects a different path: voluntary
evictions, such as a node drain.”

## 8:45–9:30 — Explain the half-page analysis

**Show:** The half-page PDF, or Slide 1 while discussing the failure path.

**Say:**

“Without a disruption budget, maintenance can evict both replicas before their
replacements become ready. During that interval, the load balancer has no
usable backend, so requests can receive intermittent 503 responses. Connections
cut off during termination can also produce 502 errors, depending on timing.

“Our design combines a one-Pod disruption allowance, two minimum replicas,
readiness-based traffic removal, and graceful connection draining. These
address overlapping causes of temporary unavailability. We report the actual
results from our tests in the written analysis; if we did not observe a 5xx,
we explain the configuration and test conditions rather than invent an outage.

“The budget cannot stop direct deletion, a database outage, or every abrupt
node failure. An active audio session also cannot move transparently between
Pods.”

## 9:30–9:45 — Close

**Show:** Public Hush dashboard or Slide 1.

**Say:**

“Hush now runs as managed replicas behind trusted HTTPS. We showed a live Pod
replacement, an actual autoscaler decision under application load, and the
committed configuration behind those behaviors. Managed data survives compute
replacement, and we retain two replicas when demand drops. Thank you.”

Stop the recording by 10:00. Use observed wording only after every stated proof
has actually occurred.

## Recovery and final review

- **Certificate still Provisioning or browser warning:** postpone recording;
  fix DNS, load-balancer attachment, CAA/validation, and certificate status.
- **HTTP silently upgrades in browser:** show the explicit terminal 301/Location
  output. Browser navigation by itself does not prove server redirection.
- **One Pod is Pending/unready:** investigate identity, resource admission,
  private SQL routing, startup logs, probe Host handling and NEG readiness.
- **Replacement takes too long:** rehearse again after fixing the cause; do not
  force-delete or manually create a replacement for the final proof.
- **HPA has `<unknown>` metrics:** fix requests/metrics before recording. If
  counts remain two, verify the Job is reaching transcription and CPU exceeds
  the target. Do not lower the threshold live to manufacture the claim.
- **Pod count already exceeds two before the deletion:** wait for normal HPA
  scale-down. Start from a clean baseline so replacement and scaling are clear.
- **Fresh request fails:** fix and re-record; do not call an old entry fresh.
- **A 5xx occurs:** preserve it and diagnose it. State the actual limitation;
  the analysis must not claim zero failures when the request monitor found one.
- **Required live proof missing or timer overruns:** re-record a complete take.
  Screenshots supplement the required live deletion, rather than replacing it.

After recording, verify Job completion, stop any residual generator, wait for
HPA to return to two, and capture scale-down evidence. Keep compute running for
an agreed grading window; otherwise use the tested pause helper to scale the
application to zero while retaining its hostname/certificate and managed data.
Restore and verify it before the next demo. Review the full video for legibility,
audio/cameras, continuity of deletion/scaling, and accidental credentials.
Check current course sharing requirements before adding the OneDrive link to
Canvas. Retain the same release identity across slides, evidence and repository.
