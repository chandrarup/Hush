# Hush Milestone 4 submission package

This folder contains the submission-ready Milestone 4 artifacts. The visible
demo is cloud-only; local tests are internal verification and are not part of
the recorded presentation.

## Submit

- `Hush_Milestone4_Architecture.pptx` — exactly two slides.
- `Hush_Milestone4_Written_Analysis.pdf` — polished one-page deletion analysis.
- `Hush_Milestone4_Written_Analysis.md` — editable source for the analysis.
- `Hush_Milestone4_Demo_Runbook.md` — the 10-minute, cloud-only recording plan.
- `Hush_Milestone4_Final_Checklist.md` — last-pass submission and OneDrive checks.
- `evidence/` — live configuration, migration, row-count, IAM, secret-name,
  container, image-digest, upload, and readiness evidence.
- Repository file `migrations/001_initial_schema.sql` — executable migration
  with real `CREATE TABLE` statements.

## One artifact version

Every submission surface must show only this version:

```text
Tag:    v2.0.2
Digest: sha256:7eade4c5f18aab20a74814f703ba627d4b8ff952d1f575b67d3b56b66c40bbfc
```

Do not show older `v1`, `v1.1`, `v1.2`, `v2.0.0`, or `v2.0.1` tags in the
Milestone 4 video or screenshots.

## Verified cloud outcome

- Cloud SQL `hush-postgres-m4` is runnable on private IP `172.18.170.3`;
  public IP connectivity is disabled.
- The SQLite migration preserved all 18 pre-migration history rows: `18 = 18`.
- A post-migration spoken upload produced history row 19 and a private Cloud
  Storage object, proving the running app uses the managed services.
- The live managed database now contains 19 history rows and 2 completed upload
  records. The migration comparison remains `18 = 18` because it was captured
  before the two post-migration smoke tests.
- The VM runs `v2.0.2` as user `hush` with a read-only root filesystem.
- Docker publishes the application only on VM loopback; the demo reaches it
  through an encrypted SSH tunnel on local port `57328`.
- No `.env` file exists in the VM deployment directory or running container.
- Secret values never appear in this package.

## Recording rule

Every presenter must keep their camera visible during their portion. Upload the
full recording to OneDrive, grant view or edit access to the three required
course addresses, and submit only the shareable OneDrive link in Canvas.
