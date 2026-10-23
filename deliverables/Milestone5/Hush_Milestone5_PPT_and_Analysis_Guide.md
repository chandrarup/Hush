# Hush Milestone 5: PowerPoint, analysis, and evidence guide

Planning specification. Produce the final PPTX/PDF only after the actual
deployment and test evidence establish the claims. Presenter assignments remain
open; the complete recording sequence is in the companion demo guide.

## Slide 1 — Hush orchestration topology

Exactly one editable architecture diagram on a 16:9 slide. Title: **Hush
orchestration topology**. Use the earlier Hush visual identity, readable labels,
and a small team/milestone footer. Do not add a cover slide.

Required diagram content, left to right:

1. Browser/native client, final free hostname, HTTPS 443.
2. Google external HTTPS load balancer; trusted managed certificate; HTTP 80
   redirects to HTTPS.
3. Ingress host/path routing and ClusterIP Service, port 80 → 57327.
4. GKE boundary containing at least two Hush API + Whisper Pods, same release
   image/digest. Label replica baseline **2**, HPA range **2–4**, target **60% CPU**.
5. Managed-service boundary: private-only Cloud SQL for relational state and
   private Cloud Storage for WAV objects. Draw separate arrows from the Pods.

Small supporting annotations: PDB `maxUnavailable: 1`; Workload Identity →
Secret Manager; Artifact Registry → image. Keep these secondary to the required
request/data path. Annotate Ingress as **configures load-balancer routing**;
do not imply an extra ingress proxy Pod or a database inside the cluster.

Suggested footer takeaway: **GKE replaces compute; Cloud SQL and Storage retain data**.
Do not claim regional database HA; the retained database is zonal/shared-core.

Speaker notes should contain:

- The 50-second explanation from the recording guide, with actual names and
  the final hostname substituted after deployment.
- One sentence distinguishing Ingress configuration, Service selection, and
  the load balancer's NEG-to-Pod forwarding path.
- The real release tag/digest and source commit for reference, without putting
  an unreadable full digest in the main diagram.
- Links to the official GKE/identity sources used. No tokens or private keys.
- Clarify in notes that the 2–4 replica range is the active demo configuration.
  Between agreed demo/grading windows, explicit maintenance mode may pause the
  application at zero to save money; it is then intentionally unavailable.

## Slide 2 — Liveness and readiness probes

Title: **Liveness and readiness probes**. Use a clear comparison with three
rows: question, check, and failure action. Keep the endpoints and consequences
large enough to read during a screen recording.

| | Liveness | Readiness |
| --- | --- | --- |
| Question | Can this application process respond? | Can this replica accept work now? |
| Endpoint | `GET /health` | `GET /ready` |
| Checks | App responds; no database call | `SELECT 1`, storage access, token loaded, model initialized; not draining |
| Failure action | Repeated failure restarts the container | Withdraws the Pod from serving traffic |

Below the comparison, use one sentence: **A database outage should stop routing
to an unready replica without restarting every healthy app process**.

Add a small startup-probe note, not a third comparison column: initialization
gets time to complete before liveness/readiness enforcement. Put exact probe
intervals, thresholds, timeouts, and termination defaults in speaker notes.
Explain that the load balancer has its own health check, explicitly configured
against readiness. Do not equate Docker HEALTHCHECK with Kubernetes probes.

Speaker notes should also distinguish cached token availability from a live
Secret Manager API check. The app's existing `/ready` response does not prove a
new Secret Manager call on every request.

## Written analysis — half a page

Aim for **220–260 words** on the upper half of one page, with a short title and
readable 11–12 point text. The assignment asks for half a page; do not repeat
Milestone 4's longer one-page analysis or reduce the font to hide extra text.
Export to PDF after the actual observed results are known, retain editable
Markdown, and visually inspect the exported page.

Use three connected paragraphs:

1. Explain a concrete no-PDB maintenance sequence: two healthy replicas;
   overlapping voluntary evictions; replacements not ready; no healthy backend;
   intermittent failures until readiness recovers. A 503 is a typical no-backend
   result. A 502 can occur when a connection is cut during termination. The
   specific observed code depends on the failure path and load balancer.
2. State what really happened in the team's test, using timestamps and request
   monitor results. If no relevant 5xx occurred, say so only for the tested window
   and explain the configuration: minimum two replicas, PDB maximum one
   unavailable, readiness, placement, rolling-update strategy and draining.
   State whether a PDB-respecting eviction test was actually performed. A single
   direct Pod deletion with no errors does not establish what would have
   happened during concurrent maintenance without a PDB.
3. Explain limits: PDB applies to eviction-based voluntary disruption. Direct
   `kubectl delete pod` bypasses it. Rolling updates and HPA scale-down use their
   own controls; abrupt node/database failures and interrupted WebSockets are
   not prevented by the budget. Avoid “PDB guarantees zero downtime.”

Do not intentionally remove the budget or disrupt both live replicas just to
produce an outage for the assignment. A truthful explanation of why the team's
configuration avoided the failure is explicitly allowed.

Technical references for the writer:
[Kubernetes disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/),
[GKE NEG termination and 5xx guidance](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/ingress-configuration#addressing_500_series_errors_with_negs_during_workload_scaling_in_gke).

## Evidence and rubric coverage

| Criterion | Points | Minimum convincing proof |
| --- | ---: | --- |
| At least two healthy replicas | 10 | Live `get deployment` + app-only `get pods`, with two Ready replicas |
| Different health checks | 8 | Handlers and deployed probes; liveness independent of DB, readiness queries DB |
| Replacement and autoscaling | 9 | Live named-Pod deletion/new UID; real HPA event, metrics and changed Ready count |
| HTTPS and redirect | 10 | Browser certificate details for actual host; certificate Active; HTTP 301 Location |
| Committed manifests | 8 | Remote submitted commit contains Deployment, Service, Ingress, HPA and PDB |
| Clear video and slides | 5 | Rehearsed near-10-minute video and exactly two readable slides |

Save evidence from one final release, under a dated folder:

- Certificate screenshot: resource name, actual hostname, **Active**, project.
- `pods-before.txt` and `pods-after.txt`: timestamps, cluster/namespace in the
  evidence index, Pod names/status/readiness; retain UID output/watch recording.
- HPA before/after output, scaling event/reason, CPU utilization, Ready replica
  output, load Job summary; later scale-down output is useful supporting proof.
- HTTP redirect headers and HTTPS success response; browser certificate frame.
- Public request monitor results during deletion/scaling, including failures.
- Repository URL, submitted commit, release tag/digest, manifest snapshot and
  concise evidence index explaining which file proves each requirement.

Screenshots cannot replace the live deletion demonstration. Do not use an
older milestone's image digest, old VM URL, or historical screenshot while
claiming it shows the new deployment. Match manifest snapshots to the committed
version. Keep original evidence and redact only genuinely sensitive material;
never alter output to appear successful.

## Final slide and package review

- Exactly two slides, no hidden/appendix/cover slides, editable diagram/table.
- Rendering checked visually for clipping, overlap, arrows, and readable text.
- Both required slide topics covered, with speaker notes that support the timed
  talk rather than duplicating dense paragraphs on the slide.
- Final analysis physically fits half a page and uses the actual measured result.
- Required manifests actually committed to the remote repository.
- Certificate and before/after outputs are real, current, and linked by release.
- Video captures the required live transitions and stays within the course limit.
- Current course recipients/sharing instructions rechecked; final link tested
  with the intended audience permissions.
- Final submission folder and teammate documentation ZIP contain one clear
  artifact set and no credentials or duplicated application source.
