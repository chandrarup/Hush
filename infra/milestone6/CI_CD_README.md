# Milestone 6 Cloud Build release pipeline — live validation

The `milestone6-deploy` branch in `chandrarup/Hush` has an active Cloud Build
push trigger (`hush-milestone6-deploy`, ID
`868940d9-816c-454a-bd76-475c26a8dcad`) connected through the repository
owner's `hush-github-owner` connection. It reads this YAML and runs as
`hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com`. On November 5,
2026, a normal push succeeded, a controlled failure invoked and verified
automatic rollback, and a healthy follow-up push succeeded. Exact run IDs,
digests, and revisions are in
`../../deliverables/Milestone6/PHASE7_TRIGGER_ROLLBACK_2026-11-05.md`.

## What the pipeline does

1. Rejects a missing/non-Git commit SHA, wrong project, or wrong deployment
   branch before tests and build.
2. Runs 45 headless cloud, container, and pipeline tests using the locked
   Python dependencies, with a four-minute timeout. The full desktop-inclusive
   suite remains a separate local gate.
3. Builds and pushes `hush:<full commit SHA>` to the existing Artifact Registry
   repository, then resolves the pushed tag to an immutable digest.
4. Records the current Deployment revision and image digest. One strategic
   Deployment patch updates the image digest and `HUSH_RELEASE_SHA` together.
5. Waits for GKE rollout, then requires four consecutive trusted HTTPS `/ready`
   responses that report the **new** release SHA and healthy managed checks.
   It also checks authenticated `/history?limit=1` without logging the token or
   response body.
6. On any failure after Deployment mutation, restores the saved revision,
   waits for rollout, compares the Deployment image to the saved digest, and
   rechecks public HTTPS and authenticated history. The build remains failed
   even if recovery succeeds. A recovery failure is logged explicitly.

`_FORCE_HEALTH_FAILURE: '1'` is a controlled demonstration switch. It fails
the gate **after** the new release passes health checks, so the automatic
rollback path can be shown without intentionally shipping a broken app. Restore
the substitution to `'0'` in a subsequent healthy commit.

## Live setup and evidence

The build account has project `roles/container.clusterViewer`, Artifact
Registry Writer on the Hush repository, and Logging Writer. Its Secret Manager
Accessor grant is scoped to `hush-team-token`. The applied namespace Role and
RoleBinding grant deployment mutation for `deployment/hush` and read access to
ReplicaSets for undo. Effective `kubectl auth can-i` checks passed. The trigger
matches only `^milestone6-deploy$`; avoid overlapping release pushes because
two deployments could race.

The Cloud Build gate passed 45 headless tests in each of the three live runs.
The full local suite passed 129 tests. The successful and failed builds,
rollback verification, final external HTTPS readiness, and immutable image
digests are recorded in the Phase 7 evidence file above.

## Cloud Build trigger reference

The trigger matches `^milestone6-deploy$`, uses the team GitHub connection, and runs under
`hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com`. Cloud Build
sets `$COMMIT_SHA` and `$BRANCH_NAME` for push triggers. A manual source upload
without those substitutions fails preflight by design. Review the trigger's
source repository, branch regex, config path, and service account before later
releases.
