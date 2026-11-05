# Milestone 6 phase 5 — local CI/CD pipeline implementation

**Status:** Local implementation and simulation complete on November 4, 2026.
No Git push, Cloud Build trigger, pipeline run, Deployment update, or RBAC/IAM
grant occurred in this phase.

## Changed

- Added `infra/milestone6/cloudbuild.yaml` for branch/SHA preflight, 50
  cloud-focused tests, SHA-tagged image build and push, and digest-based deploy.
- Added `preflight.sh` and `deploy_release.sh`. The deploy step records the
  previous revision/digest, patches the new digest and release SHA together,
  checks GKE rollout plus repeated public HTTPS readiness and authenticated
  history, and restores/validates the prior release on failure.
- Added a namespace-scoped `deployer-rbac.yaml` for the existing `hush-build`
  service account. It is not applied yet.
- Added a safe release SHA to public `/ready` so the external check can prove
  the new version is serving. Added focused tests for that response and the
  deployment script's success, failure, recovery, and wrong-branch paths.
- Tightened `.gcloudignore` after its upload inventory initially included the
  local Terraform cache. The final upload inventory includes the pipeline and
  tests and excludes `.terraform/`, state, plans, and observability/definition
  files.

## Validation

- `bash -n` passed for both scripts; Cloud Build and RBAC YAML parsed.
- `uv run pytest -q`: **129 passed, 6 warnings**.
- `kubectl apply --dry-run=client -f infra/milestone6/deployer-rbac.yaml`
  accepted both RBAC objects without creating them.
- The three read-only `kubectl` JSONPath expressions in the rollback script
  returned the live image digest, revision `9`, and prior release label.
- Public HTTPS `/ready` returned 200 with database, storage, secrets, and model
  checks true. The currently serving release has not changed.

## Next live phase

Confirm the team's repository/branch, grant only the required GKE and
single-secret permissions to `hush-build`, apply the namespace RBAC, create
the exact push trigger, then demonstrate good, controlled-failure/rollback,
and restored-good runs. Capture build IDs, full commit SHAs, digests, rollout
revisions, and public results. `infra/milestone6/CI_CD_README.md` contains the
implementation and setup details.
