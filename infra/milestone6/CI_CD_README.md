# Milestone 6 Cloud Build release pipeline — local implementation checkpoint

`cloudbuild.yaml` and `deploy_release.sh` are implemented locally, but **no
branch trigger, IAM grant, Kubernetes RBAC binding, or Cloud Build release has
been created or run for this pipeline**. The existing manual Milestone 6 image
release is separate evidence.

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

## Exact live setup still required

- Confirm that `https://github.com/chandrarup/Hush.git` is the team's intended
  deployment remote and approve an exact branch. `milestone6-deploy` in the
  YAML is a proposed branch; it did not exist on the remote when checked on
  November 4, 2026. The current local branch is `codex/milestone5-gke`.
- Grant the existing `hush-build` service account project-level
  `roles/container.clusterViewer` for `container.clusters.get`, and
  `roles/secretmanager.secretAccessor` on **only** `hush-team-token`.
  Artifact Registry Writer and Logging Writer are already present. Confirm
  access to the source bucket when configuring the trigger.
- Apply `deployer-rbac.yaml` to the `hush` namespace using an administrator
  identity. Its Role limits deployment changes to `deployment/hush` and grants
  read access to ReplicaSets for `rollout undo`. Verify the build account's
  effective permissions before enabling the trigger.
- Connect the confirmed GitHub repo to Cloud Build if needed, then create one
  push trigger for the exact branch with config path
  `infra/milestone6/cloudbuild.yaml` and the `hush-build` service account.
  Keep Cloud Logging as the build log destination. Avoid overlapping pushes
  during the demonstration because two concurrent releases could race.
- Save a successful build link, full commit SHA, image digest, rollout revision,
  and public readiness result. Then push one controlled health-gate failure
  commit, verify the failed build restores the old digest, and push a final
  healthy commit. Keep Cloud SQL and infrastructure untouched in this test.

The code has only been tested locally. Docker Desktop was unavailable, so no
local container build or Cloud Build execution has been claimed. Local checks:
`bash -n` passed for both scripts; YAML parsed; `uv run pytest -q` passed
129 tests (6 pre-existing deprecation warnings). Four tests exercise the real
deployment script against fake `gcloud`, `kubectl`, and `curl` commands for
successful release, controlled failure, public readiness failure, and wrong
branch rejection. `gcloud meta list-files-for-upload .` confirmed that the
Cloud Build source includes the scripts and tests but excludes Terraform
state/cache and observability definitions. A client-side Kubernetes dry run
accepted `deployer-rbac.yaml`. The live Deployment's image, revision, and
`HUSH_RELEASE_SHA` JSONPath expressions returned the expected values, and the
public HTTPS `/ready` returned 200 with all managed checks true. These are
read-only/local checks, not a Cloud Build rollout or rollback demonstration.

## Cloud Build trigger reference

After the repository and branch are confirmed, the trigger should match the
exact branch (`^milestone6-deploy$` if the proposed name is accepted), use the
team GitHub connection, and run under
`hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com`. Cloud Build
sets `$COMMIT_SHA` and `$BRANCH_NAME` for push triggers. A manual source upload
without those substitutions fails preflight by design. Review the trigger's
source repository, branch regex, config path, and service account before the
first push.
