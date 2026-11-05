# Milestone 6 corrected metric live validation — November 5, 2026

The 30-minute `hush_http_5xx_count` query returned no points before this test.
The existing manual release was temporarily rolled out with
`HUSH_ENABLE_DEMO_ERROR=1`, and public HTTPS `/ready` returned 200 with all
managed checks true. One authenticated request to `/internal/demo-error`
returned **503** at **18:15:14 UTC** with request ID
`6adba3e44a2d421393b63f73eecc06e1`.

Cloud Logging returned one parsed `http_request` record for that request ID:
route `/internal/demo-error`, numeric status `503`, and release
`cloudbuild-c81b64f0`. Cloud Monitoring subsequently returned a single point
with value **1** for that Pod in the minute ending **18:16:09 UTC**. This
validates the corrected filter's one-error/one-count behavior for this test.

The demo flag was removed immediately afterward. The final rollout completed
at revision **11** with two desired and two ready replicas on digest
`sha256:1e511adbfac33597c0d48c4ed94a7cd86abfd65bd1c75e38aaaa9e63b687edea`.
Public HTTPS `/ready` returned 200 with database, storage, secrets, and model
checks true. The route is disabled again.

The release SHA in this record is the earlier manual Cloud Build label, not a
Git commit. Live branch-triggered deployment and rollback remain separate
Milestone 6 gates.
