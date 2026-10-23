# Hush Milestone 5 deployment report

Verified October 22–23, 2026. This report separates deployed behavior from the
slides and video that still need to be produced.

**Final state, October 23 at 04:40 UTC:** application compute is paused at zero
replicas, no application/load Pods remain, HPA is inactive at zero, and the old
VM is TERMINATED. The public application is intentionally unavailable until
`resume-demo.sh` is run. Cluster, certificate, load balancer and managed data
are retained. Final outputs are in `evidence/final-standby-status.txt`.

## Access and release

- Public address: <https://hush.34.36.104.111.nip.io>.
- GKE Autopilot: `hush-m5`, `us-central1`; namespace `hush`.
- Release `v3.0.1`, immutable image digest:
  `sha256:4181321233914f477451388a53ae5aa8af556221afb2b82cf979057345e6559d`.
- Cloud Build `f86a06c8-7e0e-44f7-9f7c-f30991b6bd23`: SUCCESS.
- The native client's saved cloud address now uses this HTTPS hostname.
  Its existing private team token was preserved.
- The old `hush-vm` is stopped; its disk and previous image remain for rollback.

## Verified behavior

| Check | Result and evidence |
| --- | --- |
| Two healthy replicas | `evidence/pods-before.txt` and `pods-after.txt` |
| Automatic replacement | Deleted `hush-79c8b8dd7f-6q5wg`, UID `a7de7994-3cde-4908-bfc9-213c1e39d848`; replacement `hush-79c8b8dd7f-zrq7h` became Ready. Actual watch saved in `pod-replacement-watch.txt`. |
| HPA | Actual CPU load changed desired replicas 2 → 3 → 4, then automatically back to 2. `hpa-watch.txt`, `hpa-events.txt` and `hpa-returned-to-two.json`. |
| PDB enforcement | First Eviction API call admitted; immediately evicting the other healthy replica was rejected with TooManyRequests because it would violate the disruption budget. `pdb-eviction-test.json`. Replacement then became Ready. |
| HTTPS | Strict certificate verification passed; matching ManagedCertificate `hush-cert-nip` is Active. Actual console screenshot `certificate-active.png`; YAML `certificate-active.yaml`. |
| HTTP redirect | HTTP 301 to the same HTTPS hostname, recorded in `public-end-to-end.txt`. |
| Real speech upload | The 8.1-second WAV produced a saved transcript in 1.59 seconds before stress load. |
| Native streaming protocol | WSS final transcript persisted; first partial 709 ms and release-to-final 1597 ms in the recorded test. |
| Managed state | Readiness checks database, private storage, loaded credentials and warmed model. History persists across replicas; unauthenticated history returns 401. |
| Health separation | Liveness checks the running API only. Database failure makes readiness return 503 without failing liveness; automated fault test passed. |
| Local verification | 101 tests passed; `evidence/local-tests.txt`. |
| Security review | Codex Security reviewed all 31 changed files in an isolated patch copy, plus supplemental publication docs; no reportable findings. Source review does not establish live cloud behavior. |

The final short-audio test used four workers for three minutes and recorded
**374 HTTP 200**, **82 HTTP 429 busy responses**, **zero transport errors** and
**zero HTTP 5xx**. HPA scaled from two to four healthy replicas during this run.
The application rejects excess work promptly rather than allowing an unbounded
queue. This is a bounded demo rehearsal, not an unlimited-load guarantee.
See `load-job-short-demo.txt` and `short-load-four-replicas.txt`.

Pause/resume was tested against the real cluster: all application Pods were
removed, HPA became inactive at desired zero, then two replicas were restored
and HPA reactivated. The helper's transcription check passed. A separate public
HTTPS upload after resume completed in 3.53 seconds, WSS returned a saved final
transcript, and HTTP still returned 301. `pause-resume.txt` and
`public-after-resume.txt` contain these results. Initialization/CPU-metric
collection makes restart take a few minutes; this is why preflight starts early.

The diagnostic public health monitor recorded 842 HTTP 200 responses and three
transport errors between 02:56 and 04:14 UTC. It recorded no HTTP 5xx. Transport
errors were not diagnosed, so this is not a zero-outage or all-request success
claim. Quiet-period speech timings are not measurements under saturation.

The final-release heavy test used four workers repeating a 48-second audio
fixture for three minutes. It recorded 5 HTTP 200, 109 HTTP 429 and 11 transport
errors/timeouts. No 5xx was recorded by that load client. A fresh short upload
afterwards completed in 1.66 seconds and WSS also succeeded
(`public-after-heavy-stress.txt`). These limits matter: scaling is demonstrated,
but the long-clip saturation test did not establish consistently successful
speech processing. The final recording fixture was restored to the actual
eight-second demo audio; preserve both tests' separate logs.

## Budget and operating schedule

Target **$100 total over 45 days**, with **$150 contingency**, under the
intermittent-demo usage plan. A custom-period budget covers October 22 through
December 6, with actual-spend alerts at $50, $75, $90, $100, $125 and $150.
The budget counts usage before promotional trial credits and after standard
free-tier credits. It sends alerts; it does not impose a hard spending cap.

At published us-central1 general-purpose prices, two 1-vCPU/2-GiB Pods cost
about $0.109 per active hour before ephemeral storage. Fifty to 100 active
hours is about $5.50–11 for baseline application CPU/memory. Short scale-ups,
load Jobs, builds, load balancer, SQL, storage, logs and retained VM disks/IPs
are additional. The planning estimate is about $60–100 for light demo usage;
$150 provides contingency, not a guaranteed upper bound.

GKE publishes a **$74.40 monthly credit per billing account** applicable to
Autopilot/zonal cluster management fees. It is distinct from temporary trial
credit and does not pay application compute, SQL or the load balancer. Other
eligible clusters can share this credit. The actual new cluster credit has
not yet been confirmed on a posted invoice; check the billing report after
usage appears. Without the credit, the retained cluster management fee alone
adds about $108 over 45 days. [GKE pricing](https://cloud.google.com/kubernetes-engine/pricing).

The account's remaining trial balance and expiry were checked privately in
Billing. Account-specific financial details are omitted from this repository.
Trial credit does not extend its expiry when compute is paused.
[Trial terms](https://docs.cloud.google.com/free/docs/free-cloud-features).

## Resume and pause

From the repository root, using the authorized Google account:

```bash
gcloud container clusters get-credentials hush-m5 --region=us-central1 --project=hush-milestone-2-20260922
bash infra/milestone5/resume-demo.sh
```

Allow 30–60 minutes before a recording or grading window. The helper restores
two replicas, waits for rollout and HPA activation, checks trusted public
readiness and HTTP redirect, and performs a real transcription check. Open the
dashboard and supply the existing team token privately. Verify native microphone
and text insertion on the actual presenter's computer; protocol testing alone
does not establish microphone permissions or insertion behavior.

After the agreed access window:

```bash
bash infra/milestone5/pause-demo.sh
```

This scales the application to zero and removes temporary load Jobs. GKE has
no VM-style stop/start control for its control plane. The retained cluster,
load balancer, certificate, IP and database support a simpler next demo; their
applicable charges continue. The public application is unavailable while paused.
Do not run `deploy.sh` during standby: applying the initial Deployment baseline
restores replicas.

## Limits and remaining submission work

Node spreading is a preference. Current replicas may occupy different nodes,
but the manifest does not guarantee node or zone isolation. Cloud SQL remains
the existing small zonal instance. This is a course demo configuration, not a
claim of production high availability or an unlimited-concurrency service.

The final release limits concurrent work per replica and returns 429 when busy.
Observed quiet speech-upload timing ranged from 1.59 to 3.53 seconds across
initial and resumed replicas; these samples are not a latency service guarantee.
Its Whisper CPU threads match the single requested CPU. Rehearsal of the earlier
v3.0.0 release exposed saturation delays; those older files are archived under
`evidence/rehearsal-v3.0.0/` and are not final-release evidence. The final runtime
includes the pinned model so private nodes do not need public model downloads;
this intentionally differs from the earlier VM's model-cache volume.

Still required: record the actual live deletion/replacement and autoscaling in
the 10-minute video; produce exactly two slides; export the half-page analysis;
assemble the submission folder. Guides are linked from `START_HERE.md`. A saved
watch or screenshot cannot substitute for the live deletion in the video.
