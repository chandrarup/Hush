# Milestone 6 phase 4 live validation — November 3, 2026

## Result

The structured-logging release was built and deployed to the existing Hush GKE Autopilot cluster. The controlled public HTTPS request returned HTTP 503 with request ID `ae050c6691244b85ad43fbe8b17e4644`. Cloud Logging contained a parsed `jsonPayload` request record with the same ID, route `/internal/demo-error`, status 503, severity ERROR and release ID `cloudbuild-c81b64f0`. Cloud Monitoring showed a nonzero `hush_http_5xx_count` time series. The user confirmed receiving the Google Cloud Monitoring alert email. A screenshot of the received email still needs to be saved for submission.

## Build and deployment

- Cloud Build ID: `c81b64f0-ab31-4874-969e-a523e3b76069` — SUCCESS. [Build run](https://console.cloud.google.com/cloud-build/builds/c81b64f0-ab31-4874-969e-a523e3b76069?project=278368955479)
- Immutable image: `us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush@sha256:1e511adbfac33597c0d48c4ed94a7cd86abfd65bd1c75e38aaaa9e63b687edea`.
- Previous configured digest before rollout: `sha256:946ba2c9d177aeade0a8980db8559692abc9a0e42ba773054eca00c83c30650d`.
- The Deployment was at zero replicas before rollout. It was resumed to two. `kubectl rollout status` succeeded. The demo flag was enabled for one test and then removed, causing a second successful rollout.
- Final readback: desired replicas 2, ready replicas 2, new image digest, `HUSH_ENABLE_DEMO_ERROR` absent. The `HUSH_RELEASE_SHA` field currently contains the Cloud Build ID prefix because this image was built from an uncommitted working tree; it is **not** a Git commit SHA. The later CI/CD phase must supply a real commit SHA.
- Final public `https://hush.34.36.104.111.nip.io/ready` returned 200 with managed database, storage, secrets and model checks true. A bounded authenticated transcription produced one HTTP 200 response.

## Metric correction and observed availability issue

Immediately after the flag-removal rollout, one public `/ready` check returned **502** even though Kubernetes reported two ready Pods. A later public check returned 200. The cause of that individual load-balancer response has not been fully diagnosed; it occurred while old Pods were terminating. Keep it visible as a deployment-health risk for the CI/CD phase.

The first metric filter also counted many `/ready` 503 records emitted by draining Pods. Those were genuine readiness responses but obscured application request errors. The metric was updated and read back with exclusions for `/ready` and `/health`; `infra/milestone6/observability/hush-http-5xx.filter` is the current definition. Log-based metric changes do not retroactively remove historical points, so the dashboard may show this earlier probe noise until the selected time window moves past it. The next controlled test should verify that one application 503 adds one count under the corrected filter, and the deploy pipeline should explicitly wait for stable external HTTPS health after a rollout.

## What remains for this milestone

- Capture the received alert email screenshot, dashboard screenshot and policy screenshot for the submission.
- Verify a fresh controlled 503 against the corrected metric after enabling the endpoint for a planned demo; retain the request ID and count evidence.
- Import the live metric, dashboard, policy and notification channel into Terraform state, alongside application cloud infrastructure. Do not recreate these resources.
- Implement the branch-triggered build/deploy/health-check/automatic-rollback pipeline. This manual Cloud Build run is **not** evidence that every branch push deploys or rolls back.
- Commit the reviewed release and publish it only to the team's confirmed deployment branch. No Git commit or push was made in this phase.

**Current compute state:** application left running with two ready replicas. Do not run the Milestone 5 pause script during the announced grading window. Check the exact Canvas dates before relying on availability for grading.
