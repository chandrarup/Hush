# Hush final-product completion plan

Planning baseline: November 15, 2026. Based on repository configuration and saved evidence; live inventory and uptime have not been rechecked. Execute one phase at a time and report evidence before advancing.

## Phase 1 — Close Milestone 6 infrastructure gaps

A refreshed no-change plan proves agreement for declared resources only. It does not discover undeclared infrastructure. The existing module covers 18 resources; the November 5 trigger/rollback evidence explicitly excludes several dependencies.

| Gap | Required work | Completion evidence |
|---|---|---|
| Inventory | Compare live project, billing, IAM, network, SQL, build, secret, and storage inventories against Terraform state. Record every resource as managed, platform-created, retired, or explicitly external with owner and reason. | Reviewed coverage matrix with no unexplained application dependencies. |
| IAM grants | Declare/import project, bucket, secret, and service-account grants for runtime, nodes, builds, and Workload Identity. Use additive member resources where appropriate; avoid overwriting unrelated policy bindings. Keep namespace RBAC in versioned manifests with an explicit deployment owner. | Effective permissions match least-privilege intent; runtime and deployment still work. |
| Private service access | Declare/import the reserved peering range and Service Networking connection; make private SQL provisioning depend on them. | Private SQL connectivity and a plan with no unintended network replacement. |
| SQL user | Import/manage the application SQL user and document password ownership/rotation with Secret Manager. Choose provider-supported secret handling after checking the pinned provider; never embed passwords in committed configuration or plan evidence. Protect remote state because sensitive values may still enter it. | Existing user retained, login succeeds, rotation and recovery documented. |
| Project APIs | Inventory enabled services required by the app and pipeline; declare/import required project services and avoid disabling shared services on destroy. | Required API set reconciled with live inventory. |
| Budget | Locate the billing-account budget and import it; if absent, create the agreed project-scoped budget. Verify the historical $50 monthly amount, thresholds, recipients, and credits policy before adopting them. | Terraform resource plus billing-console readback; alert delivery configuration verified. Budget alerts do not cap spend. |
| Cloud Build | Import the regional trigger, repository connection/repository where supported, branch filter, service account, substitutions, and build config. Keep interactive GitHub authorization external with documented ownership if necessary. | Trigger settings match code and a real branch push deploys the expected SHA. |
| Other retained resources | Reconcile firewall/router/NAT/DNS/TLS, Kubernetes manifests, secret metadata, and any retained VM resources. Assign one owner per resource; distinguish provider-created GKE resources from manually created dependencies. | Inventory reconciled and obsolete-resource retirement proposed separately. |

Use declarative imports and review the saved plan before applying. Reject destructive replacements of SQL, storage, network, or cluster resources. Preserve backups and existing deletion protections. Use resource references rather than hard-coded project paths where practical. Store state remotely with restricted access and locking supported by the backend. Keep secret payloads out of evidence.

Acceptance: format/validate pass; imports are reviewed; a refreshed full-scope plan has no unexpected changes; a second plan after adoption is clean. Prove coverage with the inventory matrix, then rerun application readiness, private data access, a real triggered release, and controlled rollback. Save redacted plan output, run IDs, release SHA/digest, and inventory evidence. A clean plan alone is insufficient.

## Phase 2 — Make authentication understandable

Current behavior: desktop uses the configured bearer token; browser dashboard uses a token from the URL fragment and tab-scoped session storage. A bare cloud URL does not sign in. Cloud authentication must remain fail-closed.

For the controlled final demo, add an explicit Connect screen to desktop and browser: prefill the HTTPS server URL, accept a privately supplied team token, validate it against a protected endpoint, and show actionable missing/invalid-token and service-offline messages. Gate protected views until connected. Provide disconnect, retry, and token replacement. Store desktop credentials in macOS Keychain or the platform credential store; avoid plaintext config for the release. Keep browser credentials session-scoped, remove token links from the normal onboarding flow, and test HTTP and WebSocket authentication together. Do not ship a token in the app, README, or installer.

Acceptance: a teammate on a clean machine can install, connect, dictate, upload, and view history using only the README and privately issued demo credential. Test fresh browser tabs, reloads, incorrect/rotated credentials, WebSocket reconnects, and an offline backend. An invalid credential must never reveal history.

## Phase 3 — Establish the product's access model

The existing shared token and shared history are suitable only for a trusted team demo. Before inviting independent public users, implement managed OIDC sign-in, short-lived server-validated sessions, secure HttpOnly/Secure/SameSite browser cookies with CSRF protection, and desktop authorization-code flow with PKCE and secure credential storage. Use an established identity provider rather than building password storage.

Add user ownership and authorization to history, recordings, snippets, settings, and live sessions, including database migration and storage access enforcement. Test cross-user denial, logout, expiry, revoked sessions, and account removal. Agree retention/deletion behavior and explain where recordings are processed. Public signup is complete only after isolation and abuse/rate limits are verified; adding a login page alone is insufficient.

## Phase 4 — Finish the demonstrable release

- Verify every advertised feature: hotkey recording, partial and final transcription, insertion into another application, cleanup fallback, vocabulary, snippets, upload, history, and settings. Fix or clearly label unsupported platform behavior.
- Test a fresh DMG/source installation on a second machine, including macOS permissions, denied-permission recovery, signed/notarized release distribution as applicable, and uninstall/reinstall behavior.
- Measure cold/warm transcription latency and concurrent-client behavior. Warm the model, verify HTTPS certificate/readiness, and resume replicas before the demo. Show clear progress/error states for long requests.
- Verify persistence after pod restart and restore a backup into an isolated test target. Test upload limits, temporary-file cleanup, and recording deletion.
- Rehearse a short demo: install/connect → dictate into a text editor → upload → history/snippets → monitoring → triggered deployment and rollback evidence. Use non-sensitive sample audio and redact credentials.
- Produce a tagged release, verified download, final README, exact operator start/stop commands, known limitations, and a demo run sheet. Confirm the deployed digest matches the release and repeat the clean-user walkthrough.

Final acceptance: another person can follow the documented path without operator improvisation; all advertised demo features pass; infrastructure ownership is reconciled; deployment and rollback are evidenced; credentials are never public. Record test results and remaining limitations honestly. Public multi-user readiness additionally requires Phase 3.

## Decisions confirmed during the product interview

These decisions supersede conflicting alternatives earlier in this planning document.

- Invite-only Google sign-in in browser and macOS desktop; validate Google Identity Platform/Firebase Authentication with an isolated compatibility prototype before adopting it.
- Five invited accounts initially. No server-busy reservation/queue system and no enforced daily quota in this release. A suggested 60-minute daily allowance is informational only.
- Operators manually start/stop cloud compute as needed. The app must explain an offline backend and offer retry without silently queueing audio. Hosting may change after cost and rollback review; target no more than $50/month, not a guaranteed charge cap.
- Both desktop and browser sessions expire after 24 hours and require sign-in again. Warn before expiry; do not start a recording that cannot finish within the remaining session. Removal from the invite list revokes HTTP and live-session access.
- Private user-owned history, recordings, snippets, vocabulary, and cloud preferences. Device hotkeys, microphone, and permissions remain local. Latest saved cloud changes win.
- Initial operators: ashrith.vadde@gmail.com and chandrarupdaka@gmail.com, with equal administration rights but no application interface for browsing other users' content. Existing shared data belongs to Ashrith's verified account.
- Cloud recordings retained seven days; users may delete audio separately while retaining text, or delete both. Desktop audio stays temporary and is discarded after delivery or failure. Transcripts remain until individually deleted.
- No account-deletion feature or request workflow in the demo release; document this limitation. No transactional-email dependency.
- Guided setup: cloud connection, Google login, microphone/hotkey/insertion permissions, and test dictation. Verify on a second clean Mac, including cross-user access denial.
- Back up and pause writes for migration. Rollback restores the prior trusted-team release privately; new users must not receive shared-token access.
- Preserve a reconciled pre-authentication GitHub baseline without milestone deliverables before implementation. Next: isolated identity feasibility prototype and hosting estimate; reconcile infrastructure before production authentication changes.

Compatibility acceptance: an invited Google account can authenticate in browser and return securely to the desktop; an uninvited account cannot obtain application access; server sessions enforce the 24-hour boundary and revocation. Use scratch data, never migrate production data during the prototype.

## Terraform feedback completed — November 16, 2026

Phase 1 dependency adoption is complete for the reported gaps: 63 existing resources imported, 81 managed total, no infrastructure mutations, and a refreshed no-change plan. See [verified coverage](../infra/milestone6/terraform/COVERAGE.md). This supersedes earlier statements that application IAM, private service access, SQL user, APIs, budgets, or the build trigger are unmanaged. Authentication and other product work remain pending.
