# Hush Terraform live inventory — November 4, 2026

Read-only `gcloud` descriptions were taken from project
`hush-milestone-2-20260922`. This records resource names and material settings
for import mapping. The 18 resources in the Terraform module were subsequently
imported and passed a live refreshed no-change plan; see `README.md`.

| Resource | Live identifier and key settings | Terraform disposition |
| --- | --- | --- |
| GKE Autopilot cluster | `hush-m5`, `us-central1`, RUNNING; private nodes; `REGULAR` release channel; `hush-vpc` / `hush-subnet`; Pod and service ranges `hush-m5-pods` / `hush-m5-services`; Workload Identity pool `hush-milestone-2-20260922.svc.id.goog` | Import, after comparing all provider defaults against live configuration. Keep HPA replicas and release image outside Terraform. |
| VPC | `hush-vpc`; custom subnet mode; regional routing | Import. |
| Subnet | `hush-subnet`, `us-central1`, `10.10.0.0/24`; Private Google Access; secondary ranges `hush-m5-pods=10.30.0.0/16`, `hush-m5-services=10.31.0.0/20` | Import without replacing either range. |
| Global reserved IP | `hush-m5-ip`, `34.36.104.111`, in use by the GKE Ingress forwarding rules | Import; never replace during the grading window. |
| Artifact Registry | `hush-containers`, Docker, `us-central1`, standard repository | Import. |
| Cloud SQL | `hush-postgres-m4`, PostgreSQL 15, `db-f1-micro`, zonal `us-central1-a`; private IP only; 10 GB SSD; backup and point-in-time recovery enabled | Import instance. Examine provider plan carefully because deletion protection is currently false. |
| SQL database | `hush` (plus system `postgres`) | Import application database only. |
| SQL user | `hush_app` (plus system `postgres`) | Inventory only. Avoid Terraform ownership until password/state handling is agreed; no password value was read. |
| Upload bucket | `hush-milestone-2-20260922-uploads`, `US-CENTRAL1`; uniform access and public access prevention; `uploads/` objects expire after 30 days | Import and preserve lifecycle rule. |
| Build-source bucket | `hush-milestone-2-20260922-build-source`, `US-CENTRAL1` | Import after full settings readback. |
| Cloud Build default bucket | `hush-milestone-2-20260922_cloudbuild`, `US` | Service-managed bucket; document as an exception unless team ownership is required. |
| Service accounts | `hush-gke-node`, `hush-build`, `hush-runtime` | Import the three team-created accounts. Leave the Compute Engine default account outside this module. |
| Secret containers | `hush-db-password`, `hush-team-token` | Import containers only; never import or expose secret version values. |
| Monitoring resources | 5xx metric, dashboard, email channel, alert policy | Definitions and import blocks staged in this directory; no import performed. |

Project-level IAM, bucket IAM for application buckets, private services access,
and enabled APIs still need an ownership decision and inventory before Terraform
can claim infrastructure coverage. Broad project IAM bindings should not be
recreated or replaced wholesale. GKE-created load-balancer forwarding rules,
backends, health checks, and Kubernetes application objects remain controller
owned.

## Terraform state bootstrap

Created `gs://hush-milestone-2-20260922-tfstate` in `US-CENTRAL1` with uniform
bucket-level access, enforced public access prevention, seven-day soft delete,
and Object Versioning. Direct bucket IAM convenience grants for project viewers
and editors were removed; the direct policy retains project-owner legacy roles.
The project IAM readback showed only one project-wide Owner principal (the
active operator) and no project-wide Viewer, Editor, or Storage Admin binding.
This supports the current access boundary, though future IAM changes must be
rechecked. The bucket is currently empty.

The initial `terraform init` attempt failed because local Application Default
Credentials were absent. ADC was then established through the standard login
flow; backend initialization, import-only apply, and no-change verification
succeeded. The saved plan was checked as 18 import actions with no create,
update, or destroy action before it was applied.
