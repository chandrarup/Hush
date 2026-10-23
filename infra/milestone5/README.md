# Hush GKE demo deployment

This directory contains the Milestone 5 Kubernetes configuration. Runtime
credentials are fetched from Secret Manager using Workload Identity; no secret
values belong in these files. `release.env` contains public deployment metadata.

## Operator workflow

Run from the repository root, using an authorized Google account:

```bash
gcloud container clusters get-credentials hush-m5 --region=us-central1 --project=hush-milestone-2-20260922
bash infra/milestone5/resume-demo.sh
```

Start 30–60 minutes before recording. The helper waits for the Deployment and
trusted HTTPS readiness; perform a short authenticated upload or native
dictation before declaring the demo ready. The shared team token is supplied
privately through the existing client/dashboard authentication flow.

After the agreed demo/grading window:

```bash
bash infra/milestone5/pause-demo.sh
```

Allow a few minutes for the configured connection draining and termination grace
period. The helper confirms Pod removal and that the HPA is inactive at zero.

This intentionally makes the application unavailable. It retains the cluster,
Service, Ingress, certificate, reserved IP, database and uploaded objects. The
HPA remains configured with a two-replica minimum but suspends scaling while
the Deployment is deliberately at desired zero. Confirm it remains zero and
that temporary user workloads are gone. Cluster/load-balancer/database costs
are separate from application compute; budget alerts do not cap charges.

To deploy changed manifests intentionally, use `deploy.sh`. It resumes compute
and must not run automatically during standby. Deployment updates should avoid
overwriting an HPA-owned replica count; the explicit `replicas: 2` here is the
initial active-demo baseline.

## Rebuild and restore

`provision.sh` prepares the existing VPC/subnet's dedicated secondary ranges,
node identity, static IP and Autopilot cluster. The ranges in that script were
checked for this project; recheck them before adapting it elsewhere. It starts
cluster creation asynchronously. Once RUNNING, fetch credentials and deploy.

Image: see `release.env` and the digest pinned in `deployment.yaml`. The image
contains a fixed Whisper `tiny.en` snapshot and can initialize without public
model downloads. Private nodes use Private Google Access for Google APIs.

Use Cloud Build for this release: the existing local `.dockerignore` excludes
the new load script, so a direct local Docker build is not equivalent to this
deployment's allowlisted Cloud Build context.

Cloud Build uses `cloudbuild.yaml`, a dedicated `hush-build` service account,
and private bucket `hush-milestone-2-20260922-build-source`. The build account
needs Logging Writer on the project, Artifact Registry Writer on
`hush-containers`, and Object Viewer on that bucket. Submit only the reviewed
allowlist selected by `.gcloudignore`:

```bash
gcloud builds submit --project=hush-milestone-2-20260922 \
  --config=infra/milestone5/cloudbuild.yaml \
  --service-account=projects/hush-milestone-2-20260922/serviceAccounts/hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com \
  --gcs-source-staging-dir=gs://hush-milestone-2-20260922-build-source/source .
```

For a later release, change the image tag in build configuration and pin the
resulting digest in the Deployment and load Job together. Never change an
already submitted release's image while keeping its evidence unchanged.

## Rehearsal load

The private audio fixture is `milestone5-demo/load-sample.wav` in the existing
upload bucket. The load Job reads it and the team token using its workload
identity, sends actual transcription requests, and exits after a bounded run.
It does not match the application's `app=hush` label.

```bash
kubectl -n hush delete job hush-load --ignore-not-found
kubectl apply -f infra/milestone5/demo/load-job.yaml
kubectl -n hush get hpa hush --watch
```

Capture real metrics, HPA events and Ready application Pods. Wait for normal
scale-down to two before pausing. Do not count a terminating replacement or
the load generator as proof that the HPA scaled the application.

## Recovery

Rollback an application release with `kubectl -n hush rollout undo deployment
hush` when a previous revision exists, then check readiness and HTTPS. The old
Milestone 4 VM/image is a separate rollback path; start the VM, use its existing
encrypted tunnel and verify managed state before using it. Never run the
SQLite migration again. Do not delete Cloud SQL, its backups, or the upload
bucket during compute troubleshooting.

Missing readiness, repeated container restarts, failed fresh transcription,
untrusted HTTPS, or persistent 5xx are rollout failures. Preserve logs, correct
the issue or roll back, and do not claim the deployment succeeded until the
affected user flow works.
