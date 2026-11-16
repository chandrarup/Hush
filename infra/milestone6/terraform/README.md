# Hush Terraform

This module manages **81 existing resources** in the Hush project. On November
16, 2026, it adopted 63 dependencies missing from the original 18-resource
Milestone 6 configuration. Adoption imported existing objects; it did not
recreate infrastructure or change access, credentials, budgets, or deployment.

| Coverage | Resources | Configuration |
|---|---:|---|
| Original infrastructure and observability | 18 | `network.tf`, `platform.tf`, `data.tf`, `observability.tf` |
| Enabled project APIs | 41 | `services.tf` |
| Application IAM grants | 14 | `iam.tf` |
| Private-service range and connection; SQL application user | 3 | `dependencies.tf` |
| Existing monthly and milestone-period budgets | 2 | `billing.tf` |
| GitHub connection, repository, and deployment trigger | 3 | `build.tf` |

Import IDs are retained in `imports.tf`, `infrastructure_imports.tf`, and
`coverage_imports.tf`. The enabled-service inventory includes pre-existing
Google/project defaults as well as application APIs; adoption does not imply
that Hush uses BigQuery or every other enabled service. API resources use
`disable_on_destroy = false`, and all new resources have `prevent_destroy`.
Application IAM uses additive member resources, never authoritative policies.

## Credentials and state

Use operator Application Default Credentials with access to the project,
remote state, and billing budgets. The `google.billing` provider alias explicitly
uses Hush as its quota project because the Billing Budgets API requires it for
user ADC. No credentials or private variable files belong in Git.

```bash
cd infra/milestone6/terraform
export TF_VAR_alert_email='<existing monitoring-channel recipient>'
terraform init -backend-config='bucket=hush-milestone-2-20260922-tfstate' \
  -backend-config='prefix=milestone6/terraform'
terraform fmt -check
terraform validate
terraform plan -refresh=true -detailed-exitcode -no-color
```

Terraform 1.5+ and the pinned Google provider 8.4.0 are required. Review saved
plans before applying; do not use an old plan after changing configuration.
A no-change plan proves agreement only for the declared scope. Use the
[coverage and validation record](COVERAGE.md) to assess completeness.

## Ownership boundaries

- **This module:** the 81 resources above, including application runtime/build/
  node project grants, bucket/registry/secret grants, and Workload Identity.
- **Credentials:** SQL `hush_app` identity is managed, but its existing password
  is not read, reset, or stored in configuration. Password rotation and secret
  versions remain a coordinated operator procedure in Secret Manager. The
  GitHub OAuth credential is referenced by secret-version resource name only;
  the GitHub owner controls authorization and installation consent.
- **Google-managed identities:** Google service-agent and legacy convenience
  grants remain owned by Google/platform administration. Human project roles
  remain operator-managed; this module does not adopt Owner or elevate access.
- **Kubernetes:** versioned manifests under `infra/milestone5` and
  `infra/milestone6/deployer-rbac.yaml` own workloads and namespace RBAC.
  Controllers own generated load-balancer objects; the pipeline owns release
  digest/SHA, and the HPA owns scaling. Do not manage the same objects twice.
- **Bootstrap:** the protected remote-state bucket is separately bootstrapped.
  Google-created default build buckets, backend bucket grants, and unrelated
  legacy/retained VM resources are outside this dependency-adoption change.

The $50 monthly budget excludes credits and retains 20%, 50%, and 100% spend
alerts with project-level recipients. The separate $100 October 22–December 6
milestone budget retains its existing thresholds and credit treatment. Alerts
warn about spend; neither budget stops compute or imposes a spending cap.

The build trigger intentionally continues to match `^milestone6-deploy$` and
uses `infra/milestone6/cloudbuild.yaml`. Merging Terraform changes to `main`
does not deploy application code or change the trigger branch.

Remote state contains private monitoring-channel and infrastructure metadata.
Do not publish state, plan JSON, `.terraform`, raw audit inventories, or secret
payloads. Sanitized validation summaries are sufficient for review.
