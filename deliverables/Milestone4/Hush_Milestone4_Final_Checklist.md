# Milestone 4 final checklist

## Rubric evidence

- [ ] Cloud SQL Connections screenshot shows private IP enabled and public IP
      disabled on the same screen.
- [ ] `migrations/001_initial_schema.sql` is committed and visibly contains real
      `CREATE TABLE` statements.
- [ ] Row-count evidence shows old SQLite `18`, new Cloud SQL `18`, and
      `counts_match: true` before new demo rows.
- [ ] The cloud dashboard accepts a real WAV upload, returns a transcript, and
      creates a history row.
- [ ] The same upload appears as a private Cloud Storage object.
- [ ] IAM screenshot names the `hush-runtime` service account and its roles.
- [ ] Secret Manager screenshot shows secret names while values stay hidden.
- [ ] VM and container checks show that no `.env` file exists.
- [ ] Artifact Registry and the running VM both show `v2.0.2` and the same
      digest.
- [ ] Docker shows `127.0.0.1:57327->57327/tcp`, and the dashboard is reached
      through the encrypted SSH tunnel on local port `57328`.

## Required submission files

- [ ] Video is 10 minutes or less and demonstrates only the cloud deployment.
- [ ] Every presenting team member's camera is visible during their portion.
- [ ] PowerPoint contains exactly two slides.
- [ ] Written analysis fits one page in the final submitted format.
- [ ] Working artifacts include configuration, migration, row counts, IAM, and
      Secret Manager evidence.

## OneDrive and Canvas

- [ ] Full video uploaded to OneDrive.
- [ ] View or edit access granted to `sdesini@cougarnet.uh.edu`,
      `krajan@cougarnet.uh.edu`, and `skolanu@cougarnet.uh.edu`.
- [ ] Share link tested in a private browser window.
- [ ] Only the shareable OneDrive link submitted in Canvas.

## Privacy and consistency

- [ ] No secret value, token, database password, personal email, or billing
      detail appears in screenshots or video.
- [ ] No local Compose or laptop deployment is presented as Milestone 4 proof.
- [ ] Presenter explains that `127.0.0.1:57328` is a tunnel to `hush-vm`, not a
      locally running Hush service.
- [ ] No tag other than `v2.0.2` appears in the submission.
