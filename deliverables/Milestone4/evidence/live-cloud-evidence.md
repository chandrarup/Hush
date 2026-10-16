# Live Milestone 4 cloud evidence

Captured from project `hush-milestone-2-20260922` on 2026-10-15. Secret values
are intentionally excluded.

## Cloud SQL configuration

```text
Instance:              hush-postgres-m4
State:                 RUNNABLE
Database version:      PostgreSQL 15
Region / zone:         us-central1 / us-central1-a
Private IP:            172.18.170.3
Private connectivity:  Enabled
Public connectivity:   Disabled (ipv4Enabled=false)
VPC:                   hush-vpc
Backups:               Enabled
Point-in-time recovery: Enabled
```

The Google Cloud Console Connections page was also visually verified with
“Private IP connectivity: Enabled” and “Public IP connectivity: Disabled” on
the same screen.

## Runtime identity and IAM

```text
VM: hush-vm
Internal IP: 10.10.0.2
Static public IP: 104.198.149.120
Service account: hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com

Project roles:
  roles/artifactregistry.reader
  roles/cloudsql.client
  roles/logging.logWriter

Secret-level role on hush-db-password and hush-team-token:
  roles/secretmanager.secretAccessor

Bucket-level role on hush-milestone-2-20260922-uploads:
  roles/storage.objectUser
```

## Secret Manager names

```text
hush-db-password
hush-team-token
```

The Secret Manager list was visually verified with names visible and values
hidden. No secret value was captured.

## Cloud Storage

```text
Bucket: hush-milestone-2-20260922-uploads
Location: us-central1
Uniform bucket-level access: true
Public access prevention: enforced
Upload lifecycle: delete uploads/ objects after 30 days
```

End-to-end spoken upload through the live app:

```text
Original filename: milestone4-voice-proof.wav
Transcript: Milestone four stores durable state and managed cloud services.
Cloud SQL history_id: 19
Object: uploads/2026/10/15/99c6f744-52b5-44af-83cd-e0e55d0ed912.wav
Size: 120960 bytes
Status: completed
```

Final authenticated upload through the encrypted SSH tunnel after the
loopback-only deployment hardening:

```text
Original filename: m4-encrypted-tunnel-proof.wav
Transcript: milestone for encrypted tunnel proof.
Cloud SQL history_id: 20
Object: uploads/2026/10/16/05a96174-6b9c-4a15-83fd-d5840ec135eb.wav
Size: 80766 bytes
Status: completed
```

The object was independently listed from Cloud Storage, and the newest history
record was independently read from the application after the upload completed.

Current managed counts after the three post-migration upload tests:

```text
entries: 20
uploads: 3
completed_uploads: 3
schema_migrations: 1
```

## Image identity and container checks

```text
Tag: v2.0.2
Digest: sha256:7eade4c5f18aab20a74814f703ba627d4b8ff952d1f575b67d3b56b66c40bbfc
Container user: hush
Read-only root filesystem: true
Named mount: /var/cache/hush (disposable model cache)
Published application port: 127.0.0.1:57327->57327/tcp
Demo access: encrypted SSH tunnel on local port 57328
Direct public port 57327: closed (connection refused)
Host deployment .env: absent
Container /app/.env: absent
Container /.env: absent
```

Readiness response:

```json
{"status":"ready","mode":"managed","checks":{"database":true,"storage":true,"secrets":true}}
```

The optional Ollama profile was stopped after its model pull exhausted the small
VM disk. That cache is disposable and outside the Milestone 4 state boundary.
The required Hush service remains healthy and the verified upload transcription
uses Whisper in the `v2.0.2` Hush container.
