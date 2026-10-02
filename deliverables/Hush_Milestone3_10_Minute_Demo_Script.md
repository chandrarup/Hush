# Hush Milestone 3 Demo Script — 10 Minutes

Every presenter keeps their camera visible during their portion. Paste commands;
do not read commands aloud. Keep the team token hidden.

## Speaker 1 — 0:00 to 2:15 — Architecture and local startup

**Screen:** Slide 1, then terminal.

“Hush now separates the native Mac client from a repeatable Linux cloud stack.
The client still handles the microphone, hotkey, and text insertion. Docker
Compose starts the versioned Hush API. Hush history and the Whisper cache
persist in named volumes. This VM uses the Hush-only profile, so it returns the
raw Whisper transcript without an Ollama cleanup service.”

Paste:

```bash
docker compose up -d
docker compose ps
```

“All services come from declared images and configuration. We no longer install
Python packages or configure the application manually on each machine.”

## Speaker 2 — 2:15 to 4:15 — Local application and immutable image

**Screen:** `http://localhost:57327`, then terminal.

Record or upload a short audio sample. Show the transcript and history.

“This is the full cloud side of Hush running locally on port 57327. The history
survives container recreation because it lives in the Hush data volume.”

Paste:

```bash
docker image inspect "$HUSH_IMAGE" \
  --format 'ID={{.Id}} SIZE={{.Size}} ARCH={{.Architecture}} USER={{.Config.User}}'
```

“We built one Linux AMD64 artifact so the Apple Silicon laptop and the AMD64 VM
can use the same image digest. The Hush process runs as a non-root user.”

## Speaker 3 — 4:15 to 6:25 — Registry, budget, and security

**Screen:** Artifact Registry, budget page, and firewall rule.

“Artifact Registry shows the explicit `v1` tag and immutable digest. We compare
this digest again on the VM rather than trusting the tag alone.”

“Our $50 monthly budget covers the Hush project. Actual-spend alerts remain at
20%, 50%, and 100%, equal to $10, $25, and $50. The firewall still restricts
port 57327 to current team `/32` addresses.”

“The image does not contain our team token. `.dockerignore` blocks environment
files, credentials, local databases, deliverables, and development output. We
also inspected the image environment, history, and filesystem before pushing.”

## Speaker 4 — 6:25 to 9:25 — VM pull, run, and before/after

**Screen:** SSH terminal.

Paste:

```bash
docker compose pull hush
docker compose up -d --no-build --no-deps hush
docker compose ps
curl -fsS http://127.0.0.1:57327/status
docker image inspect "$HUSH_IMAGE" \
  --format 'ID={{.Id}} REPO_DIGESTS={{json .RepoDigests}} ARCH={{.Architecture}}'
```

“The VM pulled `v1` instead of rebuilding it. The digest matches Artifact
Registry and the local artifact. Compose reports Hush healthy on the same port
used in Milestone 2.”

**Screen:** `http://VM_PUBLIC_IP:57327`, complete one transcription, then Slide 2.

“In Milestone 2 we copied source code, created a virtual environment, installed
dependencies, configured systemd, and diagnosed Linux-specific startup issues.
Now the VM needs Docker, a small runtime configuration, and one pull-and-run
command. Containerization solved environment drift for our team.”

## Closing — 9:25 to 10:00

**Screen:** Slide 2 or final checklist.

“We demonstrated Docker Compose locally, the `v1` registry artifact, identical
digests, the same Hush application on the VM URL, runtime-only secrets,
persistent data, and active budget controls. Our repository includes the Dockerfile,
Compose file, and `.dockerignore`. After recording, we stop the VM to control
cost.”
