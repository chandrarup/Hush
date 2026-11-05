# Milestone 6 Terraform — imported infrastructure

This directory defines and has imported **18 existing resources**: GKE, VPC,
subnet, reserved IP, Artifact Registry, Cloud SQL instance and application
database, two application buckets, three team service accounts, two Secret
Manager containers, and four observability resources. Their IDs are in
`imports.tf` and `infrastructure_imports.tf`. The observability definitions
refer to the saved live JSON/filter files in `../observability/`. The channel
recipient is supplied privately through `TF_VAR_alert_email`; Terraform state
still contains the address and Cloud SQL certificate metadata.

The import-only saved plan was inspected before applying: 18 imports, zero
creates, updates, or destroys. The import completed on November 4, 2026. A
fresh `terraform plan -refresh=true -detailed-exitcode -no-color` returned
exit 0 and `No changes. Your infrastructure matches the configuration.` The
full output is in `deliverables/Milestone6/evidence/terraform-no-change-2026-11-04.txt`.

## Ownership boundaries and exceptions

| Owner | Resources or fields |
| --- | --- |
| This Terraform module | The 18 resources listed above, with settings in `.tf` files. All have `prevent_destroy`. |
| Separate bootstrap | `hush-milestone-2-20260922-tfstate` bucket. State cannot safely manage its own backend bucket in this module. |
| Kubernetes and GKE controllers | Namespace, Deployment, HPA, Service, Ingress, certificates, BackendConfig, PDB, and GKE-created load-balancer objects. Versioned Kubernetes manifests remain under `infra/milestone5/`; the later pipeline will manage releases. |
| Application/pipeline | Image digest and release SHA; HPA controls application replica scaling. |
| Existing operators and services | SQL `hush_app` user/password, secret **versions**, project and resource IAM grants, private services access, enabled project APIs, and the Cloud Build default bucket. These are inventoried or pending inventory, not claimed as Terraform-managed. |

The GKE and `hush-team-token` labels are present in the API's effective labels
but were not returned as Terraform-owned labels at import. The module leaves
those labels outside its ownership to preserve the zero-change plan. Review
that choice if the rubric requires exact label ownership. IAM and private
services access are the next Terraform coverage decisions; use narrow IAM
member resources rather than authoritative project-wide policies.

## Safe validation

The backend block is intentionally partial so no bucket name or credential is
hardcoded into the module. The dedicated bucket
`hush-milestone-2-20260922-tfstate` now exists with versioning, soft delete,
uniform access, and public access prevention. Its direct viewer/editor
convenience grants were removed. The current project IAM readback shows only
the active operator as Owner, with no project Viewer/Editor grants. Local ADC
was established through the standard Google login flow. Do not commit ADC or
state files. Review every future plan before applying it.
Never commit state, plans, `.terraform/`, or a recipient tfvars file.

```bash
cd infra/milestone6/terraform
export TF_VAR_alert_email='<existing recipient, supplied privately>'
terraform fmt -check
terraform init -backend-config='bucket=hush-milestone-2-20260922-tfstate' \
  -backend-config='prefix=milestone6/terraform'
terraform validate
terraform plan -refresh=true -detailed-exitcode -no-color
```

The November 4 import plan showed 18 imports with no other actions. The
subsequent refreshed plan returned exit 0. Repeat this gate after future
Terraform changes and after the CI/CD trigger exists. `terraform init
-backend=false` is only for local schema validation, not live state work.

The Cloud Asset API is currently disabled in this project; use individual
read-only `gcloud ... describe/list` inventory calls unless the team decides
to enable that API. No API enablement is needed for this checkpoint.
