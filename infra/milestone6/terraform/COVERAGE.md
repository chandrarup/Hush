# Terraform dependency coverage — verified November 16, 2026

The original no-change plan covered 18 resources and omitted dependencies.
The reviewed saved plan imported **63 resources with zero creates, updates,
or destroys**. A fresh post-import plan exited **0**, reporting **No changes**
for 81 resources. Format and validation passed with Google provider 8.4.0.

| Feedback item | Adopted coverage | Verification |
|---|---|---|
| IAM grants | 6 project, 2 bucket, 2 registry, 3 secret, 1 Workload Identity | Existing application memberships imported individually; no authoritative policy replacement. |
| Private service access | Reserved range and Service Networking connection | Existing range/connection retained; SQL explicitly depends on connection. |
| SQL user | Existing hush_app PostgreSQL identity | Password neither retrieved nor reset; SQL remains RUNNABLE. |
| Project APIs | All 41 enabled services at inventory time | API-name set matched against final state; configuration sets disable_on_destroy=false. |
| Budget | $50 monthly plus existing $100 milestone-period budget | Amounts, dates, filters, recipients, thresholds preserved. |
| Cloud Build | GitHub connection, repository, deployment trigger | Existing IDs, branch filter, service account, config path preserved. |

HTTPS `/ready` returned 200 after adoption, with database, storage, secrets,
and model checks true. The serving release remained
`81c8f558e3cbad80f5d7b89ab4e323a1dad004b3`. No compute was started/stopped,
application redeployed, or new build/rollback demonstration run.

See [sanitized validation summary](validation-summary.json). Raw inventories,
state backups, private variables, saved plans/JSON, and full logs stay outside
Git. This record proves live adoption and scoped reconciliation, not a tested
from-scratch rebuild of the whole project.

## Explicit ownership boundaries

Secret payloads/password rotation and GitHub installation consent remain
operator-owned. Human roles, Google-managed service-agent/default convenience
grants, separately bootstrapped state storage, unrelated legacy VM resources,
and Kubernetes/controller-owned resources remain under their respective owners.
See [README](README.md). These exceptions do not include the application IAM,
private-service access, SQL user, API, budget, or trigger gaps in the feedback.

## Review safeguards

All 63 adopted resources have prevent-destroy protection. API configuration
retains services on destroy. No password is present in the SQL user config or
imported state. The billing provider alias limits explicit quota-project use
to budgets. No authoritative IAM policies, new principals, project-owner grants,
or credential-payload data sources were added.

Do not apply an older checkout against the shared state: its missing definitions
would propose deleting adopted objects. Use this configuration and review all
plans. A state rollback is not an infrastructure rollback; never overwrite later
legitimate changes with an old state backup without reconciling ownership,
serial, and lineage.
