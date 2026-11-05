# Milestone 6 live branch trigger and rollback — November 5, 2026

## Release source and trigger

- Team repository: `https://github.com/chandrarup/Hush`, branch `milestone6-deploy`.
- Cloud Build repository: `hush-team`, GitHub connection `hush-github-owner`, region `us-central1`.
- Push trigger: `hush-milestone6-deploy` (`868940d9-816c-454a-bd76-475c26a8dcad`), exact regex `^milestone6-deploy$`, config `infra/milestone6/cloudbuild.yaml`, service account `hush-build`.
- The build account received cluster-viewer access and Secret Manager access only to `hush-team-token`; namespace Role/RoleBinding allow the release changes. The temporary Cloud Build connection-admin grant was removed after linking.

## Live runs

| Purpose | Git commit | Cloud Build run | Result and serving revision |
| --- | --- | --- | --- |
| First healthy release | `5353d184e8731d6692b3dcf9ba45f13e5d36d6c1` | `e7641788-29eb-4435-9220-6373942cc469` | Success; revision 12; digest `sha256:30007c7bb19f5ddc23436ab3154e5101b0f73608c3aef9f7eddc11808330026b`. |
| Controlled failed gate | `46c485742faaee80de8fcf5906bc434d8d47bbd0` | `b495f066-91ae-4c97-b60b-765a364ad09a` | 45 tests passed and the new digest `sha256:406767139c4d032ce42d7eb7b81c09832746e921a02c29048a6531bb113ecea1` reached revision 13. `_FORCE_HEALTH_FAILURE=1` then caused an expected build failure; the script ran `kubectl rollout undo` and verified revision 14 restored the previous digest `sha256:30007c7bb19f5ddc23436ab3154e5101b0f73608c3aef9f7eddc11808330026b`. |
| Healthy restore | `a8c1677d2e2d093ff903822ad8243a08c9c41e47` | `b25f6d42-fad4-4777-9ef1-84d9d59931ac` | Success; revision 15; digest `sha256:b0f3b5b72a0f6c66cebc6a88c48154cf3e3b54726ef524cfe3dd2dd4620356cc`. |

Every triggered run passed the bounded 45-test cloud gate. The two successful
releases passed four consecutive external HTTPS `/ready` checks of the expected
commit SHA and an authenticated `/history?limit=1` check. The failed run
remained failed after the script verified the prior digest, four external
HTTPS checks, and authenticated history. An independent post-run check found
two desired and two ready GKE replicas and public `/ready` HTTP 200 with the
expected release SHA and database, storage, secrets, and model checks true.

The failure switch is back to `_FORCE_HEALTH_FAILURE: '0'` on the branch.
It fails only after the newly deployed version passes health checks, so the
rollback demonstration did not damage Cloud SQL or infrastructure.

## Infrastructure reconciliation

`evidence/terraform-no-change-after-trigger-2026-11-05.txt` is the live
refreshed Terraform plan after the GitHub connection and trigger were created.
It exited 0 with `No changes. Your infrastructure matches the configuration.`
Its scope is the 18 resources in the module; the build trigger, its connection,
deployment IAM/RBAC, and versioned Kubernetes manifests are documented
exceptions in `infra/milestone6/terraform/README.md`.

## Screenshot pages and capture order

These pages were opened in Chrome for the user. Capture the visible project,
resource name, timestamp or run ID, and status. Avoid showing tokens, secret
values, or a private email address.

1. [Final successful build](https://console.cloud.google.com/cloud-build/builds;region=us-central1/b25f6d42-fad4-4777-9ef1-84d9d59931ac?project=278368955479): status Success, test gate, deployed digest, health checks.
2. [Controlled failed build](https://console.cloud.google.com/cloud-build/builds;region=us-central1/b495f066-91ae-4c97-b60b-765a364ad09a?project=278368955479): failure and rollback verification lines in logs.
3. [Branch trigger](https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=278368955479): repository, branch regex, config path, service account.
4. [Hush dashboard](https://console.cloud.google.com/monitoring/dashboards/builder/38d27e5c-dda9-416a-9e83-15def61fafbb?project=278368955479): 5xx, CPU, and memory panels; choose a time range including 18:15 UTC on November 5 to show the controlled metric point.
5. [Log based metrics](https://console.cloud.google.com/logs/metrics?project=278368955479): `hush_http_5xx_count` definition.
6. [Alert policy](https://console.cloud.google.com/monitoring/alerting/policies/7379217993723165183?project=278368955479): threshold and notification channel; redact recipient address.
7. [Logs Explorer](https://console.cloud.google.com/logs/query?project=278368955479): query `resource.type="k8s_container" AND jsonPayload.request_id="6adba3e44a2d421393b63f73eecc06e1"` to show the one parsed 503 JSON record. Set the time range to include November 5, 18:15 UTC.
8. The actual received alert email (previously confirmed on November 3) should be captured privately with the policy name and timestamp. Redact the address and other inbox content before sharing.

The screenshot files, slides, one-page analysis, and demo plan are not part of
this working-artifact handoff. The user will take screenshots, then those
presentation artifacts can be prepared with the captured images.
