# Hush Milestone 4: 10-minute cloud-only demo

## Before recording

- Keep every presenter's camera visible during their portion.
- Close tabs that show personal email, billing information, secret versions, or
  earlier Hush image tags.
- Use only `v2.0.2` throughout the video.
- Start the encrypted tunnel and keep that terminal open:

  ```bash
  gcloud compute ssh hush-vm --zone=us-central1-a -- \
    -N -L 57328:127.0.0.1:57327
  ```

- Open the cloud dashboard once with the team token in the URL fragment. Hush
  stores it in session storage and immediately removes it from the address bar.
  Use `http://127.0.0.1:57328` through the tunnel. Do this before screen
  recording starts; never reveal the token.
- Prepare a short, real spoken WAV file under 10 MB.
- Open the Google Cloud Console pages for Cloud SQL Connections, the upload
  bucket, IAM, Secret Manager, and Artifact Registry.
- Open the two-slide deck and the committed migration file.

## 0:00–0:45 — Goal and architecture

Presenter 1: Show slide 1. Explain that Milestone 3 kept history, uploads, and
configuration on the VM. In Milestone 4, Cloud SQL, Cloud Storage, and Secret
Manager own the durable state. State clearly that the video demonstrates the
cloud deployment, not a local Compose stack.

## 0:45–2:15 — Cloud application end to end

Presenter 1: Briefly show the open `gcloud compute ssh` tunnel terminal and the
VM's running Hush container, then open `http://127.0.0.1:57328`. State clearly
that this address is the encrypted local end of the tunnel to the application
running on `hush-vm`, not a local application. Upload the prepared spoken WAV.
Wait for the transcript and history entry. Refresh the History page and point
to the newly created row. If the upload fails, stop and fix it before
continuing; do not use a pre-recorded local result as a substitute.

## 2:15–3:10 — Object storage proof

Presenter 2: Open Cloud Storage bucket
`hush-milestone-2-20260922-uploads`, navigate to the newest object under
`uploads/YYYY/MM/DD/`, and show its timestamp, WAV content type, and private
access. Explain that the application generated the object name and used the
VM's service account; no JSON key file exists.

## 3:10–4:35 — Managed database and migration proof

Presenter 2: Show Cloud SQL instance `hush-postgres-m4`. On Connections, keep
these two rows visible together:

- Private IP connectivity: Enabled
- Public IP connectivity: Disabled

Then show `migrations/001_initial_schema.sql` in the repository and briefly point
to the real `CREATE TABLE` statements for `entries`, `uploads`, `snippets`, and
`app_settings`. Show the row-count evidence: old SQLite `18`, Cloud SQL `18`,
and `counts_match: true`. Explain that later demo uploads can legitimately make
the current Cloud SQL count larger than 18.

## 4:35–5:45 — Identity and IAM

Presenter 3: Show slide 2, then the IAM page filtered to
`hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com`. Show these
project roles: Artifact Registry Reader, Cloud SQL Client, and Logs Writer.
State that Secret Accessor is bound directly on the two secrets and Storage
Object User is bound directly on the bucket. Show the VM configuration with
this service account attached.

## 5:45–6:35 — Secret Manager and no `.env`

Presenter 3: Show the Secret Manager list with only the names visible:
`hush-db-password` and `hush-team-token`. Do not open a secret version. In the
VM terminal, run the prepared checks that show the deployment directory has no
`.env` and the running container has no `/app/.env` or `/.env`. Also show only
environment variable names, not values.

## 6:35–7:30 — Same immutable artifact

Presenter 3: Show Artifact Registry tag `v2.0.2` and digest
`sha256:7eade4c5f18aab20a74814f703ba627d4b8ff952d1f575b67d3b56b66c40bbfc`.
Then show the running container image digest and confirm it matches. Do not show
older tags.

## 7:30–8:25 — Health and container boundaries

Presenter 4: Show `docker compose ps` with Hush healthy and the tunneled
`http://127.0.0.1:57328/ready` response reporting database, storage, and
secrets as `true`. Show that Docker publishes `57327` only on VM loopback, the
container user is `hush`, the root filesystem is read-only, and the only named
mount is the disposable model cache. Explain that `/app/data` and `/tmp` are
temporary memory filesystems.

## 8:25–9:30 — VM deletion analysis

Presenter 4: Summarize the written analysis. Deleting the VM causes downtime
and loses only running processes plus downloaded model caches. Cloud SQL rows,
Cloud Storage objects, secrets, image, IAM, VPC, subnet, and static IP
reservation survive. Be honest that recovery is scripted but not automatic;
a person must recreate and bootstrap compute.

## 9:30–10:00 — Closing proof

Presenter 4: Return to the new history row and uploaded bucket object. State
that the same cloud request wrote both managed services using the VM identity.
End before 10:00.

## Submission

Upload the full video to OneDrive. Grant view or edit access to:

- `sdesini@cougarnet.uh.edu`
- `krajan@cougarnet.uh.edu`
- `skolanu@cougarnet.uh.edu`

Open the shareable link in a private browser window to verify access. Submit the
OneDrive link in Canvas, not the video file.
