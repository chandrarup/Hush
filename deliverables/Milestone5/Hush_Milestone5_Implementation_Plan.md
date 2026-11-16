# Hush Milestone 5 implementation plan

Status: implemented; see [the deployment report](LIVE_DEPLOYMENT.md) for measured
acceptance and remaining submission work. The final hostname is
`hush.34.36.104.111.nip.io`. The initial sslip.io hostname obtained an Active
certificate but was blocked by the current network; nip.io was verified
reachable and selected instead. See the deployment status report for actual
acceptance results; the steps below are not themselves completion evidence.

## 1. Starting point and target

The starting checkout was `main` at `0cbf06e`; implementation uses
`codex/milestone5-gke`. Earlier deliverable changes are local;
preserve them and commit only the intended Milestone 5 work. The owning source
is `voiceflow/web/api_server.py` and `voiceflow/cloud/managed_state.py`.

Historical pre-deployment facts (not the current resource inventory):

- Project: `hush-milestone-2-20260922`; region: `us-central1`.
- Cloud SQL `hush-postgres-m4`: RUNNABLE, PostgreSQL 15, `db-f1-micro`, zonal,
  private VPC connectivity, public IPv4 disabled.
- `hush-subnet`: `10.10.0.0/24`, on `hush-vpc`, Private Google Access enabled;
  no secondary Pod/Service ranges appeared in the subnet inspection.
- Kubernetes Engine API is disabled. Cloud DNS API is also disabled and is not
  needed for the selected free hostname.
- `/health` responds without a database query. `/ready` checks database access,
  Cloud Storage access, and whether the team token has been loaded.
- The existing image and Compose deployment belong to Milestone 4. Its
  `v2.0.2` identity is a historical baseline, not the future Milestone 5 release.

Use a **GKE Autopilot cluster**, `hush-m5`, on the existing VPC/subnet, with a
`hush` namespace. Start with two Hush replicas; HPA may increase this to four.
Reuse Cloud SQL, the private upload bucket, Secret Manager, and Artifact
Registry. Do not create another database or re-run the old SQLite migration.

Logical topology:

`Browser/native client → HTTPS load balancer → Ingress routing → Service → Hush pods → Cloud SQL + Cloud Storage`

Ingress configures the Google load balancer; it is not another proxy container.
With container-native load balancing, the load balancer reaches Pod endpoints
through NEGs. Show the Service as the logical selection/routing boundary.

## 2. Free hostname and $100–150 total demo-period budget

Reserve one global static load-balancer IP, `hush-m5-ip`. Derive the hostname
as `hush.<actual-reserved-IPv4>.nip.io`. This is a hostname template, not a
currently deployed URL. The IP must remain reserved while the service is live.
The provider maps an embedded IP to its DNS address without registration or a
DNS account. It also documents certificate issuance for these hostnames.
[Provider documentation](https://nip.io/).

Use a GKE `ManagedCertificate` for that exact hostname. Treat successful
issuance as a deployment acceptance gate: shared free DNS can have service or
CA validation failures. If public DNS/issuance fails, diagnose it before trying
the equivalent `sslip.io` hostname on a network where it is reachable. Do not switch providers during the recording,
purchase a domain, use a self-signed certificate, or bypass certificate checks.
If both free options fail validation, stop and report the specific blocker.

Use the same final hostname in the certificate, Ingress, allowed hosts, browser,
native client's HTTPS base URL, load tool headers, slides, and evidence. Keep
port 80 enabled to return a 301 redirect to HTTPS via `FrontendConfig`; disabling
HTTP would prevent demonstrating the required redirect.
[GKE certificate setup](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/secure-traffic-management),
[Ingress configuration](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/ingress-configuration).

Budget decisions:

- Revised user preference: pause compute between demonstrations during a
  45-day period. Target **$100 total**, with a proposed **$150 total contingency
  ceiling**. This replaces the earlier continuously running $100/month plan.
- Initial request/limit per Hush container: **1 CPU, 2 GiB memory**; request
  1 GiB ephemeral storage. Use CPU-only `tiny.en`, beam size 1, cleanup None.
  Spend on useful demo-time capacity rather than six weeks of idle replicas.
- Two such Pods cost approximately **$0.109/hour** for requested CPU/memory
  at the published general-purpose rates. Fifty to 100 active hours therefore
  costs roughly $5.50–11 before short scaling bursts, load Jobs, ephemeral
  storage and build charges. Confirm admitted requests and measured performance.
- Keep the load balancer, static IP, certificate and database between sessions
  for easy restarts. Budget approximately $27 for forwarding rules over 45 days,
  $12–20 for the existing SQL instance/storage/backups, $5–15 for intermittent
  application compute, and $15–30 for builds, storage, registry, logs, network
  traffic and retained old VM resources. **About $60–100 total** is a provisional
  low-traffic planning estimate; $150 leaves contingency rather than requiring
  intentionally small demo replicas. Inventory actual retained resources.
- Verify the billing account's GKE monthly management-fee credit before creating
  the cluster. It is shared across that billing account. Without available
  credit, an additional **$108 over 45 days** applies even while the application
  is paused. The retained-cluster approach would then miss the $100 target and
  can exceed $150. Stop provisioning and revise the lifecycle/cost plan rather
  than claiming pausing Pods eliminates the control-plane fee. Do not count
  temporary trial credits as ongoing savings.
- Inventory existing VM/disk/IP charges. After GKE passes acceptance, stop the
  old VM and its container workload as a controlled cutover, preserving rollback
  configuration and durable state. Budget retained resources explicitly; do not
  silently delete disks or release old addresses to make the estimate fit.
- Track the 45-day total separately because it spans monthly billing periods.
  Use a custom-period budget where supported, with alerts at $50, $75, $90,
  $100 and $125; $150 is the proposed contingency ceiling, not a promised bill.
  Alerts are notifications, not a spending cap. HPA maximum is four;
  load Jobs end automatically. No GPU, Spot Pods, Ollama service, extra database,
  paid DNS zone, or new always-on monitoring stack.

Sources: [GKE prices and management credit](https://cloud.google.com/kubernetes-engine/pricing),
[network prices](https://cloud.google.com/vpc/network-pricing).
Validate the actual billing estimate before deployment. No cloud cost changes
or shutdowns are performed merely by editing this planning package.

### Pause and resume workflow to implement

Provide guarded `pause-demo.sh` and `resume-demo.sh` helpers under the Milestone 5
infrastructure directory. Both verify project, cluster and namespace and print
a credential-free summary of their action. No cluster deletion is needed in the
default credited-cluster plan.

- Pause only outside an agreed demo/grading window. Stop the temporary load Job
  and any other Hush test generator, then explicitly set Deployment desired
  replicas to zero. Keep the CPU HPA's `minReplicas: 2` configuration intact.
  Kubernetes supports implicit maintenance-mode deactivation at desired zero;
  verify `ScalingActive=False` and that application Pods actually finish
  terminating. Test this on the deployed GKE version before relying on it.
- The PDB is not a reason to leave unwanted demo compute running: an intentional
  workload scale-to-zero is a maintenance action outside the live demonstration.
  Do not leave user-managed monitoring/test Pods running and assume all compute
  has stopped. Check actual workloads and billing after the first pause.
- Keep Ingress, Service, ManagedCertificate, global static IP and Cloud SQL.
  The app is intentionally unavailable while paused; the HTTPS load balancer can
  return a no-backend error. No requests automatically wake this CPU-HPA workload.
  Preserving the address and certificate avoids recreating HTTPS each session.
- Resume sets desired replicas to two, waits for application and load-balancer
  readiness, verifies HPA reactivation, runs a short warm-up transcription,
  and checks trusted HTTPS and the HTTP redirect. It must fail visibly if these
  checks do not pass. Never claim the app is ready merely because Pods exist.
- Start resuming **30–60 minutes before each demo**, allowing node provisioning,
  image pulls and checks. Rehearse the full pause/resume cycle once. Give any
  grader or teammate an agreed availability window, with compute restored in
  advance. Preserve captured evidence even while compute is paused afterward.
- Do not reapply a manifest with a nonzero replica count during standby unless
  intending to resume. Normal deployment automation must respect the maintenance
  state. Pausing application compute does not stop SQL/storage/load-balancer
  charges. Keep SQL running by default; its small cost avoids extra restart risk.

Sources: [HPA maintenance-mode behavior](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/#implicit-maintenance-mode-deactivation),
[Autopilot billing rules](https://cloud.google.com/kubernetes-engine/pricing).

## 3. Application and deployment changes

### Replicas, state, identity, and startup

- Build an AMD64 Milestone 5 release, `v3.0.1`, pin the Deployment to its actual
  immutable digest, and record both tag and digest in one release card. Update
  dependent documentation together; never invent the digest in advance.
- Bake a pinned `tiny.en` model snapshot into the image, make its path available
  to the existing model selector, and warm it during cloud startup. A new Pod
  must not need a public Hugging Face download before its first transcription.
  Keep the desktop's local behavior unchanged.
- Use private nodes with Private Google Access for Google APIs and Artifact
  Registry. No Cloud NAT is required for this Google-services-only runtime;
  prove image pulls, identity, and the model work without public egress. Build
  the image in a build environment with internet access. Do not enable optional
  external cleanup providers in this deployment.
- Add non-overlapping Pod/Service secondary ranges only after inspecting all
  existing VPC and private-service ranges. Use GKE IP allocation support with
  validated available ranges; never overwrite `10.10.0.0/24` or the Cloud SQL
  private-service allocation. Verify the actual Pod-to-private-SQL route.
- Bind Kubernetes service account `hush-runtime` in namespace `hush` to the
  existing Google `hush-runtime` identity through Workload Identity Federation.
  Retain existing bucket/secret-specific grants. Image pulling uses the node
  identity: give the dedicated node service account the GKE node permissions and
  repository-scoped Artifact Registry Reader separately. Do not use JSON keys.
- Retain the read-only root filesystem, non-root UID/GID 10001, dropped
  capabilities, and writable bounded `emptyDir` mounts for `/tmp`, `/app/data`,
  and disposable caches where needed. Persistent data remains in managed stores.
- Serialize schema migration application with a PostgreSQL transaction advisory
  lock acquired before checking/creating the migration ledger. Multiple Pods
  must start together without racing DDL or migration inserts.
- Add configurable database pool bounds; use pool size 2, overflow 0 per Pod
  here. Check Cloud SQL's actual connection limit and reserve capacity for a
  surge Pod, probes, and administration. Do not assume the old 7 connections
  per process are safe when multiplied by the maximum replica count.
- Refresh persisted settings from Cloud SQL on relevant cloud reads/actions,
  rather than serving another replica's stale startup copy. Refresh dashboard
  history/statistics periodically while visible, so an event on another Pod
  does not hide a committed history row. SSE/live-session indicators remain
  connection-local; do not promise a global live-session view or transparent
  migration of an active WebSocket. No Redis/Pub/Sub expansion is required.

### Health, routing, and termination

- Keep the public interfaces `/health` and `/ready`; add no load-test or CPU-burn
  endpoint. Liveness returns 200 when the process responds and never calls the
  database, storage, or Secret Manager.
- Readiness returns 200 only with usable managed dependencies and a warmed cloud
  model; return 503 on dependency failure or draining. Existing `checks.secrets`
  means the token is loaded, not that every probe re-fetches Secret Manager.
  Add a model check to the existing `checks` object. Local mode retains its
  existing response contract.
- Bound readiness I/O: pool acquisition 1 second, database connection/query
  readiness operations 2 seconds each, storage readiness request 2 seconds with
  no unbounded retries. Keep the total below the 10-second probe timeout and
  ensure the event loop remains responsive. Record actual timeout behavior in
  tests rather than relying on an async timeout that leaves threads accumulating.
- Hush currently validates every HTTP Host header. Permit only exact GET/HEAD
  probe paths `/health` and `/ready` before Host validation, because kubelet and
  Google probes can send Pod-IP Host headers. Keep hostname validation and
  authentication unchanged on the application routes; no wildcard allowed host.
- Startup probe: `/health`, every 5 seconds, timeout 2 seconds, failure threshold
  60. Liveness: `/health`, every 10 seconds, timeout 2 seconds, threshold 3.
  Readiness: `/ready`, every 15 seconds, timeout 10 seconds, threshold 2.
  Startup completion includes model warm-up; revisit only if measured cold
  startup exceeds the five-minute budget.
- `BackendConfig` explicitly checks `/ready` on 57327, interval 15 seconds,
  timeout 10 seconds, healthy/unhealthy thresholds 2. Configure request timeout
  180 seconds, connection draining 60 seconds, and sampled HTTP access logs.
- Use a `preStop` hook that marks `/tmp/hush-draining` and keeps the process
  alive for 120 seconds while endpoints are withdrawn. Readiness sees that
  marker; liveness remains 200. Set termination grace to 210 seconds and Uvicorn
  graceful shutdown timeout to 75 seconds. Close managed clients at shutdown.
  These timings are rehearsal defaults, not a guarantee for every connection.

### Kubernetes resources to commit

Implement under `infra/milestone5/`, keeping separate reviewable YAML files for
Deployment, ClusterIP Service, Ingress, HPA, and PDB. Include Namespace,
ServiceAccount, non-secret ConfigMap, ManagedCertificate, BackendConfig,
FrontendConfig, and repeatable provisioning/verification instructions.

- Deployment: initially two replicas, one Uvicorn process per container,
  `maxUnavailable: 0`, `maxSurge: 1`, and spreading across nodes. Prefer zone
  spreading when available without making the workload unschedulable.
- Service: port 80 to named container port 57327, matching labels, NEG annotation,
  and BackendConfig association. Create its NEG-enabled configuration before
  starting the Deployment so GKE can inject its load-balancer readiness gate.
- Ingress: GCE class annotation, global static-IP annotation, exact hostname,
  managed-certificate annotation, FrontendConfig association, `/` routing.
- HPA: `autoscaling/v2`, CPU average utilization 60%, minimum 2, maximum 4,
  zero scale-up stabilization, 120-second scale-down stabilization, at most one
  Pod removed per minute. After HPA owns scaling, ordinary deployment updates
  must not repeatedly reset `spec.replicas` to two.
- PDB: `policy/v1`, `maxUnavailable: 1`, selector matching exactly Hush Pods.
  Set `unhealthyPodEvictionPolicy: AlwaysAllow` on the supported cluster version.

PDB limits eviction-based maintenance. Direct Pod deletion bypasses it, and
Deployment rolling updates and HPA scale-down need their own availability and
draining settings. A PDB alone does not prevent every 5xx.
[Kubernetes disruption semantics](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/).

## 4. Build, validate, and freeze the release

Perform in this order:

1. Preserve earlier deliverables; create a `codex/` implementation branch. Confirm
   the billing estimate/credit and existing resource inventory before provisioning.
2. Implement application changes and focused tests; build and verify the image,
   including the bundled model. Publish its tag and actual digest.
3. Enable GKE API, allocate cluster networking, create Autopilot and identity
   bindings, reserve the global IP, and derive the final free hostname.
4. Apply supporting configuration, NEG-enabled Service, Deployment, HPA/PDB,
   certificate, redirect, and Ingress. Keep both public listener protocols enabled.
   Validate private database access; do not enable Cloud SQL public IP to fix it.
5. Wait for two application-ready and load-balancer-ready replicas, a healthy
   backend, certificate **Active**, trusted browser HTTPS, and a real HTTP 301.
   Provision the certificate at least a day before the intended recording.
6. Create a bounded load Job using the same release image with its server command
   overridden to a dedicated load script. Fetch the team token through Workload
   Identity/Secret Manager without displaying it. Read a short, team-approved WAV
   from the private bucket; do not bundle private voice recordings into the image
   or public repository. Call the internal Service's actual `/transcribe` route
   using the canonical Host and Origin headers. This is application traffic,
   not a synthetic busy loop. Limit to four concurrent requests for 180 seconds,
   with request timeouts and a 240-second Job deadline; do not log the token.
7. Rehearse ordinary Pod deletion and replacement while probing the public URL.
   Separately rehearse the Eviction API: after one eviction is admitted, a second
   must be rejected while the budget is exhausted. Do not bypass it with a direct
   second deletion. Keep this experiment off camera unless time permits.
8. Rehearse measured load causing 2 → 3 or 4 replicas; save metrics, HPA events,
   desired/current/ready counts, and later automatic return to two. If it cannot
   complete within the allocated recording time, improve cold start or shorten
   other sections before recording. Do not substitute manual scaling.
9. Verify the public native-client WSS path with a short dictation and verify a
   diagnostic upload, saved history, and private bucket object. Cut over from the
   old VM only after these pass. Keep rollback instructions and old managed data.
10. Commit manifests and code, verify the intended commit is on the submitted
    remote branch, and freeze that image/configuration for the final evidence.
    Capture evidence and finalize slides/analysis after the freeze.

Required test scenarios:

| Test | Acceptance |
| --- | --- |
| Database unavailable after startup | `/health` stays 200; `/ready` becomes 503; process is not restarted just because SQL is unavailable; recovery restores readiness |
| Storage failure/model not ready/draining | Readiness fails within its time bound; liveness remains independent |
| Host/auth checks | Pod-IP probe requests work; unrelated hosts and unauthorized application requests still fail |
| Concurrent startup | Multiple processes apply each migration once without DDL/ledger races |
| Multiple replicas | History/settings remain consistent across requests to different Pods; browser history refresh recovers missed cross-Pod events |
| HTTPS and redirect | Browser trusts the exact hostname; certificate Active; a plain HTTP request returns 301 with an HTTPS Location |
| Self-healing | One named Pod is deleted normally; a different Pod name/UID becomes Ready automatically; no manual create/scale |
| Autoscaling | Real transcription load raises measured CPU; HPA changes count above two; added replicas become Ready; count later returns to two |
| Maintenance/draining | PDB rejects excess evictions; rolling update preserves serving replicas; public request probe records actual status codes |
| Resource bounds | No OOM/restart loop, pending capacity problem, excessive connections, or workload-derived cost forecast above target |
| Pause/resume | Desired zero stays zero with HPA inactive and no test compute left running; restore two Ready replicas, HPA activity, trusted HTTPS and a successful transcription before a demo |

Run existing tests once with the changes, then the targeted cloud acceptance
checks. Record failures and limitations honestly. Cloud SQL remains a zonal
shared-core database; this milestone does not establish full regional HA.

## 5. Completion and submission gate

The 50-point mapping is: replicas 10, distinct probes 8, replacement/scaling 9,
HTTPS/redirect 10, committed manifests 8, clear video/slides 5. The written
analysis and required evidence are mandatory even where the rubric does not
assign them their own row.

Complete only when every row is supported by the submitted commit, real cloud
evidence, and a rehearsed video plan. Capture HPA's return to two after the test
and stop temporary load Jobs. Leave compute running for any agreed grading
window; otherwise use the verified pause workflow and retain configuration,
certificate and durable state. Recheck costs after the first active/paused day
and track cumulative spend across the 45-day period. No claim of deployment,
certificate issuance, passed tests,
recorded video, or submission follows from these planning documents alone.
