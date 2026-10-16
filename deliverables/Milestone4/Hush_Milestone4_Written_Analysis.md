# If the Hush VM were deleted right now

Deleting the VM would cause immediate downtime, but it would not delete Hush's
durable application state. The API, dashboard, Whisper inference, and optional
Ollama cleanup run in containers on `hush-vm`, so clients could not
record, upload, transcribe, view history, or change settings until replacement
compute was deployed. Any request that was in flight at the moment of deletion
could fail. Disposable model caches on the VM would also disappear and would
need to download again, increasing the first transcription's startup time.

The application data would survive. Cloud SQL for PostgreSQL stores history,
upload metadata, snippets, settings, and the migration ledger. The instance is
reachable only through its private IP on `hush-vpc`; public IP connectivity is
disabled. Automated backups and point-in-time recovery are enabled. Cloud
Storage stores uploaded WAV files and the frozen SQLite backup created during
the migration. The bucket blocks public access and uses uniform bucket-level
access. Secret Manager stores the database password and team token, so deleting
the VM does not delete or expose either secret. Artifact Registry retains the
exact `v2.0.2` image and digest used by the deployment. IAM bindings, the VPC,
subnet, reserved private-service range, firewall rules, and static public IP
reservation are separate Google Cloud resources and would also survive.

Recovery would require creating or reusing a VM on `hush-subnet`, attaching the
`hush-runtime` service account with the cloud-platform scope, installing Docker
and Compose, and deploying the same `v2.0.2` image. The service account already
has Cloud SQL Client, Artifact Registry Reader, and Logs Writer at the project
level. It has Secret Accessor on only the two Hush secrets and Storage Object
User on only the upload bucket. The application would reconnect to Cloud SQL,
apply any unapplied committed migrations, read its secrets through Application
Default Credentials, and reuse all surviving database rows and bucket objects.

One limitation remains: the deployment is recoverable but not self-healing.
The repository contains repeatable provisioning and IAM scripts, but it does
not yet contain a complete Terraform definition or an auto-scaling managed
compute service. A human still has to recreate and bootstrap the VM, reattach
the reserved public IP for restricted SSH administration, redeploy Compose, and
re-establish the encrypted tunnel. The application port remains bound to VM
loopback, so its shared bearer token is not sent over plaintext public HTTP.
Model downloads and the VM's current disk capacity remain compute concerns
rather than durable state. A future step would move the service to managed
instance groups or Cloud Run where compatible, add trusted TLS for direct
public access, and define the entire environment as infrastructure as code.

Therefore, VM deletion would cost Hush availability and warm caches, but not
history, uploads, settings, snippets, secrets, the deployable image, or the
managed network and IAM configuration. That is the milestone's intended
boundary: compute can be replaced without reconstructing application state.
