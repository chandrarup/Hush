# Hush Milestone 6: 50-point execution plan

**Progress status (November 4, 2026):** Structured logging, live observability resources, and a manual logging release were validated in earlier phases. Terraform manages 18 imported existing resources and a live refreshed plan returned exit 0/no changes; its exceptions are documented in `infra/milestone6/terraform/README.md`. The Cloud Build pipeline and automatic rollback script now exist locally and pass local tests, but the build account permissions, branch trigger, successful/failed live runs, and final submission evidence remain pending. The supplied assignment text is the controlling Module 6 brief; no separate Module 6 file was found in this checkout.

## 1. Baseline and decisions

- Project: `hush-milestone-2-20260922`; region: `us-central1`; GKE Autopilot cluster: `hush-m5`; namespace and Deployment: `hush`.
- Expected HTTPS host: `https://hush.34.36.104.111.nip.io`; the team token is private. Check `/ready` and an authenticated user flow after resuming the deployment. The Milestone 5 report says application replicas were paused at zero after its demo; do not assume the URL is currently live.
- Existing dependencies: `hush-vpc`/`hush-subnet`, reserved IP `hush-m5-ip`, GKE Ingress/managed certificate, Artifact Registry `hush-containers`, Cloud SQL `hush-postgres-m4`, private upload bucket, Secret Manager, IAM/workload identity. Inventory exact names and settings from Console and `gcloud` before import.
- Use **Cloud Build connected to GitHub** with `infra/milestone6/cloudbuild.yaml` as the pipeline workflow file. Set one designated branch, proposed `milestone6-deploy`, after coordinating with the repository owner. Do not repoint the existing `origin` or push until the team agrees on the branch.
- Treat Terraform as owner of stable cloud resources and, if the team chooses, Kubernetes stable objects. Keep the application image digest and HPA-controlled replica count outside Terraform to avoid every deployment or autoscale action creating plan drift. Record every exception in `infra/milestone6/terraform/README.md` and the analysis.

## 2. Implementation sequence and acceptance gates

### A. Baseline, access, and safety

1. In **Google Cloud Console → project selector**, select `hush-milestone-2-20260922`. In **Kubernetes Engine → Clusters/Workloads**, record cluster status, `hush` Deployment replicas, image digest, Service and Ingress. In **Cloud SQL, Cloud Storage, Secret Manager, Artifact Registry, VPC network, IAM**, inventory the actual resource identifiers and settings. Confirm billing and grading-period availability with the team.
2. Record current `kubectl -n hush get deployment hush -o yaml`, current image digest, prior healthy revision, and `kubectl -n hush rollout history deployment/hush`. Take a private backup/export or verify existing Cloud SQL backup before infrastructure imports. Never put credentials, team token, database password, or Terraform state in Git.
3. Establish a dedicated deployment service account with only necessary Cloud Build, Artifact Registry, GKE and Logging permissions; grant access to the source staging bucket. Keep Terraform apply credentials separate from routine deployment credentials. Validate the trigger's GitHub repository and branch before enabling it.

### B. Structured HTTP logging and controlled error (7 points)

4. Add one FastAPI request/exception logging middleware in `voiceflow/web/api_server.py`. Emit **one JSON object per completed HTTP request** to stdout with UTC timestamp, severity, event name, method, route template/path, numeric `status_code`, duration milliseconds, request ID, and release SHA. On exceptions, emit a JSON error record with `status_code: 500` and a safe exception class; preserve the HTTP 500 response. Exclude authorization headers, tokens, transcript text, audio, and personal data. The current Uvicorn command uses `--no-access-log`, so the middleware must cover 5xx responses and raised exceptions itself.
5. Add a tightly gated demo endpoint, such as `GET /internal/demo-error`, enabled only by a short-lived demo flag and requiring the team token. It should intentionally return 503, log exactly one JSON request record, and never affect `/health` or `/ready`. Turn the flag off after evidence capture. Test locally that normal 200, handled 503, and unhandled 500 paths each log their actual status, and that no sensitive values appear.
6. In **Logging → Logs Explorer**, filter the GKE container for `resource.labels.cluster_name="hush-m5"`, `resource.labels.namespace_name="hush"`, `jsonPayload.event="http_request"`, and `jsonPayload.status_code>=500`. Confirm Cloud Logging parses stdout JSON into `jsonPayload` rather than leaving it solely in `textPayload`. Save the controlled request's timestamp, request ID and screenshot.
7. In **Logging → Log-based metrics → Create metric**, create a **counter** named `hush_http_5xx_count`. Use the same resource/app filter plus `jsonPayload.status_code>=500 AND jsonPayload.status_code<600`. Scope it to Hush request records only so health probe logs, load balancer logs, and duplicate exception records cannot inflate the count. Add a `route` label only if cardinality is bounded by route templates. Capture the metric definition and a before/after chart; allow for Cloud Monitoring ingestion delay.

### C. Dashboard and received alert (7 points)

8. In **Monitoring → Dashboards → Create dashboard**, make `Hush Milestone 6` with: 5xx metric count (sum, 1-minute or 5-minute alignment), GKE container CPU usage/utilization, GKE container memory used/utilization, and optionally ready replicas/restarts. Pin filters to project, cluster, namespace and workload. Save dashboard JSON through Terraform where supported. Capture a screenshot showing the controlled 5xx increase alongside CPU and memory.
9. In **Monitoring → Alerting → Edit notification channels**, create a team email channel (or another channel the team actively monitors) and finish verification. In **Alerting → Create policy**, select `logging.googleapis.com/user/hush_http_5xx_count`, sum across Hush series, and trigger when count is **at least 1 in a 5-minute window** for the demo. Document the alignment/threshold, incident behavior, notification channel and any auto-close setting. Use an alert with a short evaluation duration suitable for a controlled demo, then adjust threshold for normal operation if the team wants less noise.
10. Trigger the demo error once, wait for metric and incident, and obtain a real received email/notification screenshot with timestamp and policy name. Save screenshots of the policy and channel (redact private address if needed). A configured channel or test notification alone does **not** meet the “actually received alert” requirement.

### D. Terraform coverage and zero-change plan (9 points)

11. Create `infra/milestone6/terraform/` with pinned Terraform/provider versions, `providers.tf`, variables, separate resource files, outputs, import blocks or documented import commands, and README. Use a protected remote GCS state bucket with versioning and restricted IAM; bootstrap that bucket separately and list it as a documented exception. Do not commit `.tfstate`, plans containing secrets, `.terraform/`, or variable files with secrets.
12. Import existing resources **without recreating them**: GKE cluster; VPC/subnet and secondary ranges; reserved global IP; Artifact Registry repository; Cloud SQL instance/database/user as appropriate; upload/source buckets; service accounts and IAM bindings; Secret Manager secret *containers* (not secret version values); project APIs if owned; Monitoring metric, dashboard, alert policy and notification channel. Inventory first and inspect every generated plan before any apply. Use narrowly scoped resources for IAM to avoid overwriting unrelated team permissions.
13. Decide Kubernetes ownership explicitly. Preferred: keep `Deployment`, HPA, Service, Ingress, managed certificate, BackendConfig, FrontendConfig, PDB, ConfigMap and namespace in versioned manifests deployed by the pipeline; Terraform manages the Google Cloud infrastructure around them. This is a clear, justified exception. If rubric interpretation requires Kubernetes objects in Terraform, import stable objects but keep application image/replicas under the pipeline/HPA and prove that Terraform still plans cleanly. Avoid two controllers managing the same field.
14. Run `terraform fmt -check`, `terraform validate`, then **live** `terraform plan -refresh=true -detailed-exitcode -no-color` against the deployed project. Exit **0** with `No changes. Your infrastructure matches the configuration.` is the acceptance gate; exit 2 means drift, exit 1 means error. Resolve drift through accurate configuration/imports, never by hiding material differences. Save full dated output and a screen recording that shows refresh enabled and no changes. Repeat after observability resources and pipeline trigger are in place.

### E. Build, deploy, health check, automatic rollback (9 points)

15. Expand `infra/milestone6/cloudbuild.yaml` to: identify `$COMMIT_SHA`; run tests; build the container; push an immutable SHA tag to Artifact Registry; resolve and deploy its **digest** to `deployment/hush`; wait for `kubectl rollout status` with a bounded timeout; check `https://hush.34.36.104.111.nip.io/ready` with strict TLS; then run one authenticated read-only or sample transcription smoke check. Emit step names, SHA, image digest, rollout revision, health result and rollback result in Cloud Build logs, without printing the team token.
16. Before changing the Deployment, capture the known-good image digest and revision in the build. If rollout or external health/smoke check fails, a trap/finalizer must run `kubectl rollout undo deployment/hush` (or restore the captured known-good digest), wait for the restored rollout, recheck public HTTPS `/ready` **and** the authenticated smoke path, compare the serving image to the saved digest, then exit the build **failed**. If recovery verification fails, leave an explicit failed state and notify the team. Ensure the finalizer also handles command errors/timeouts rather than only a successful deploy step. Retain revision history and immutable images long enough for rollback.
17. In **Cloud Build → Triggers → Create trigger**, connect the designated GitHub repository, choose push events on the exact deployment branch, point to `infra/milestone6/cloudbuild.yaml`, select the dedicated service account, and configure substitutions. Check that every push triggers exactly one run. Add branch protection/review if teammates share the branch. The existing `infra/milestone5/cloudbuild.yaml` only builds an image; it is not Milestone 6 CI/CD evidence.
18. Demonstrate one harmless good commit and one **controlled bad health check** commit on the designated branch. The bad release should start safely but fail its readiness/smoke condition, allowing old healthy Pods to remain under `maxUnavailable: 0`; do not break Cloud SQL or delete infrastructure. Watch the pipeline fail, print rollback steps, restore the saved digest, and verify HTTPS traffic on the previous version. Restore the branch to a healthy commit and show the subsequent successful run. Save both Cloud Build run links/logs, commit SHAs, image digests, `kubectl` revision output and public response evidence.

### F. Submission and availability (18 remaining points: analysis 8, demo 6, live app 4)

19. Write a **one-page analysis** covering the JSON schema and 5xx filter, dashboard panels, alert threshold/channel and received incident, Terraform-managed resources plus every exception, pipeline sequence/health check/rollback, and actual result with run links. Keep claims tied to captured evidence.
20. Make a short PowerPoint: (1) current Hush request/data architecture; (2) logging → metric → dashboard → alert; (3) Terraform ownership and exceptions; (4) commit → build → deploy → checks → rollback. Use readable diagrams and exact resource names. Screenshots should be legible, timestamped, and free of secrets.
21. Record an approximately **15-minute** live demo in the order below. Confirm the upload/authenticated flow and test-account handoff privately through Canvas if needed. Agree on grading-period dates from Canvas and leave at least two healthy replicas serving throughout that period; the Milestone 5 `pause-demo.sh` makes the application unavailable and must not run before the announced window ends. Arrange any access restrictions with the instructional team.

## 3. Suggested 15-minute screen order

| Time | Screen and exact proof |
| --- | --- |
| 0:00–1:30 | Title/architecture slide, live HTTPS browser, `/ready`, authenticated Hush workflow. |
| 1:30–4:00 | Trigger authorized demo 503; show JSON entry in Logs Explorer and matching request ID; show metric definition and rising chart. |
| 4:00–5:30 | Dashboard 5xx, CPU and memory; alert policy and actual received notification. Pre-trigger alert during a rehearsal if delivery latency would exceed recording time, then explain timestamps accurately. |
| 5:30–7:30 | Terraform resource map; run `terraform plan -refresh=true -detailed-exitcode -no-color` live and show exit 0/no changes. |
| 7:30–10:30 | Push a reviewed good commit; Cloud Build trigger, tests, image build, deployment, rollout and external HTTPS health/smoke logs. |
| 10:30–13:30 | Push the controlled bad release; show failed check, automatic rollback, prior digest restored and public HTTPS still serving. |
| 13:30–15:00 | Final architecture/pipeline slide, repository branch and SHAs, remaining availability commitment and artifact index. |

**Timing risk:** full Docker builds, GKE rollouts, metric ingestion and email delivery may not finish within 15 minutes. Rehearse and optimize the pipeline; capture genuine run links and use concise time-lapse only if the instructor permits it. Do not imply a prior run happened live in the recording.

## 4. Evidence and final 50-point gate

| Rubric | Required evidence | Gate |
| --- | --- | --- |
| JSON logs + 5xx metric (7) | Controlled HTTPS 503; parsed JSON log; exact counter filter; before/after count | One error produces one count. |
| Dashboard + alert (7) | Dashboard with error, CPU and memory; policy; **received** team notification | Matching timestamp/policy. |
| Terraform (9) | Committed `.tf`; coverage/exceptions table; live refreshed plan output | Exit 0 and no changes. |
| CI/CD + rollback (9) | Trigger/branch; successful run; failed run; rollback and old digest serving | Both run links and public verification. |
| Written analysis (8) | One-page PDF/source | All four requested explanations, evidence-linked. |
| Demo/slides (6) | Approximately 15-minute recording and PowerPoint | Every proof visible and narrated. |
| HTTPS/availability (4) | Live URL, private test access, grading-window monitoring | Accessible through announced period. |

**Submission package:** live HTTPS URL; repository URL with exact branch and successful/failed commit SHAs; `infra/milestone6/terraform/` and `infra/milestone6/cloudbuild.yaml`; dashboard/policy/received-alert screenshots; log metric definition; dated no-change plan output; successful and failed/rollback run links/logs; PowerPoint; one-page analysis; demo recording/link; private Canvas test account if login is required. Record current grading-window dates from Canvas before final submission.

## 5. Google Cloud Console click path checklist

1. **Project selector → Hush project**: confirm project ID and billing.
2. **Kubernetes Engine → Clusters / Workloads / Services & Ingress**: inspect cluster, replicas, image, Ingress host and health.
3. **Logging → Logs Explorer**: inspect parsed `jsonPayload`; save 5xx filter and controlled error screenshot.
4. **Logging → Log-based metrics**: create/inspect `hush_http_5xx_count` counter and its filter.
5. **Monitoring → Dashboards**: create Hush dashboard and select log metric plus GKE CPU/memory metrics.
6. **Monitoring → Alerting → Notification channels**: verify a team channel; **Alerting → Policies**: create/inspect the metric-threshold policy; **Incidents**: inspect the fired incident.
7. **Cloud Build → Repositories / Triggers**: connect the real GitHub repository, set exact push branch/config path/service account; **History**: open good and bad runs and preserve links.
8. **Artifact Registry → Repositories**: verify immutable SHA image and digest; **IAM & Admin → Service Accounts**: check build/runtime identities.
9. **Cloud SQL / Cloud Storage / Secret Manager / VPC network / External IP addresses**: inventory infrastructure for Terraform imports and verify no secret values are exposed in captures.

## 6. Reference documentation and project files

- Project baseline: `infra/milestone5/README.md`, `infra/milestone5/deployment.yaml`, `infra/milestone5/cloudbuild.yaml`, `infra/milestone5/provision.sh`, `voiceflow/web/api_server.py`, `deliverables/Milestone5/LIVE_DEPLOYMENT.md`.
- Google Cloud: [import existing resources into Terraform](https://docs.cloud.google.com/docs/terraform/resource-management/import), [deploy to GKE with Cloud Build](https://docs.cloud.google.com/build/docs/deploying-builds/deploy-gke), [GKE system metrics](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/configure-metrics), [log metric alerting](https://docs.cloud.google.com/logging/docs/logs-based-metrics/charts-and-alerts), [log metric ingestion delay](https://docs.cloud.google.com/logging/docs/logs-based-metrics/troubleshooting), [Terraform alert policies](https://docs.cloud.google.com/monitoring/alerts/manage-alerts-terraform).
