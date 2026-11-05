# Milestone 6 observability — live resource record

Created in project `hush-milestone-2-20260922` on November 3, 2026. The subsequent manual release produced a parsed application 503 log, and the team confirmed receiving an alert email. See `deliverables/Milestone6/PHASE4_LIVE_VALIDATION_2026-11-03.md` for the dated validation and its limits.

| Resource | Cloud identifier | Source definition |
| --- | --- | --- |
| Log-based counter metric | `hush_http_5xx_count` | `hush-http-5xx.filter` |
| Monitoring dashboard | `projects/278368955479/dashboards/38d27e5c-dda9-416a-9e83-15def61fafbb` | `dashboard.json` |

The metric is a `DELTA` counter. It counts Hush `k8s_container` JSON request records whose numeric `status_code` is 500–599, excluding `/ready` and `/health` probes. The dashboard sums counts per 60 seconds, charts average CPU limit utilization, and sums memory used across Hush containers. Resource definitions were read back successfully after creation.

## Console checks

1. Open **Logging → Log-based metrics → User-defined metrics → `hush_http_5xx_count`**. Compare its filter to `hush-http-5xx.filter`.
2. Open **Monitoring → Dashboards → Hush Milestone 6**. Confirm the 5xx, CPU and memory panels exist.
3. For fresh submission evidence, trigger one authorized 503 from `/internal/demo-error` only after temporarily enabling its flag, inspect its parsed `jsonPayload`, and verify the corrected metric rises by one. Disable the flag afterward. Allow for metric ingestion delay.

## Terraform handoff

These resources were created before the Terraform phase. The four observability resources were imported into the protected state alongside fourteen other infrastructure resources on November 4, 2026. A subsequent live refreshed plan returned exit 0/no changes. See `infra/milestone6/terraform/README.md` and the dated plan output for the exact scope and exceptions.

## Phase 3 alert checkpoint (November 3, 2026)

Created an enabled email notification channel at `projects/hush-milestone-2-20260922/notificationChannels/13870997164893634747` for the address supplied by the team. Created and read back an enabled policy at `projects/hush-milestone-2-20260922/alertPolicies/7379217993723165183`. Its source definition is `alert-policy.json`. The policy sums the 5xx counter over 15 minutes across Hush containers and opens an incident when that sum is greater than zero, with no additional retest delay. The 15-minute alignment allows for documented log-metric ingestion delay. The policy references the team email channel. The API did not return a `verificationStatus` field, so this readback confirms configuration and enabled state, not mailbox delivery.

The manual release produced an authenticated 503 and matching parsed log; the team confirmed receipt of the email. Screenshots of the incident, policy, dashboard, metric, and received message remain required for submission. The corrected filter's one-error/one-count behavior still needs a fresh before/after check because the original metric counted probe traffic during Pod draining.

Terraform must import the channel and policy by their resource IDs above, alongside the metric and dashboard. Keep the recipient address out of public screenshots if privacy is desired.
