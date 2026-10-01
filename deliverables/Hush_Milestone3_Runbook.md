# Hush Milestone 3 Runbook

Use this runbook while collecting evidence. Keep the real team token off screen.

## Fixed deployment values

```text
Project:  hush-milestone-2-20260922
Region:   us-central1
Zone:     us-central1-a
VM:       hush-vm
Registry: hush-containers
Image:    us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush:v1
Port:     57327
```

## 1. Local setup and proof

Start Docker Desktop, then create the ignored runtime file:

```bash
cp .env.example .env
```

Replace only the placeholder `HUSH_TEAM_TOKEN`. Do not show `.env` in the video.

```bash
docker compose config --quiet
docker compose build hush
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:57327/status
docker image inspect "$HUSH_IMAGE" \
  --format 'ID={{.Id}} SIZE={{.Size}} ARCH={{.Architecture}} USER={{.Config.User}}'
```

Open `http://localhost:57327`, record a short browser transcription, and show the
saved history entry. Recreate Hush and confirm that the entry remains:

```bash
docker compose stop hush
docker compose up -d hush
docker compose ps
```

Do not run `docker compose down --volumes`; that deletes the evidence data and
downloaded models.

## 2. Secret verification

The following checks must return no project token, private key, or `.env` file:

```bash
docker image inspect "$HUSH_IMAGE" --format '{{json .Config.Env}}'
docker history --no-trunc "$HUSH_IMAGE"
docker run --rm --entrypoint /bin/sh "$HUSH_IMAGE" -c \
  'find /app -maxdepth 3 -type f -print | sort'
```

Take the screenshot after the commands finish. Do not put the actual token in a
search command because terminal history would retain it.

## 3. Artifact Registry

Run these commands only after confirming the correct billed project in the GCP
Console.

```bash
gcloud config set project hush-milestone-2-20260922
gcloud services enable artifactregistry.googleapis.com
gcloud artifacts repositories describe hush-containers \
  --location=us-central1 >/dev/null 2>&1 || \
gcloud artifacts repositories create hush-containers \
  --repository-format=docker \
  --location=us-central1 \
  --description='Versioned Hush application images'
gcloud auth configure-docker us-central1-docker.pkg.dev
docker push us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush:v1
```

Record the immutable registry digest:

```bash
gcloud artifacts docker images describe \
  us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush:v1 \
  --format='value(image_summary.digest)'
docker buildx imagetools inspect \
  us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush:v1
```

Capture the Artifact Registry page with the image name, `v1` tag, and digest.

## 4. Budget and network evidence

Before starting the VM, show the $50 monthly budget, current spending, project
coverage, and the selected 20%, 50%, and 100% actual-spend alerts. The dollar
thresholds are $10, $25, and $50.

Confirm `hush-team-ingress` allows TCP `57327` only from current team `/32`
addresses. Never use `0.0.0.0/0` for the demo.

## 5. VM migration

Start `hush-vm`, note its current external IP, and connect with direct SSH. Back
up the old service data before freeing port `57327`:

```bash
sudo systemctl status hush --no-pager
sudo systemctl stop hush
sudo systemctl disable hush
sudo ss -ltnp | grep 57327 || true
```

Install Docker and its Compose plugin only if `docker --version` or
`docker compose version` is missing. Grant the VM service account Artifact
Registry Reader access; do not create or copy a long-lived service-account key.

Copy only these files to `~/hush-container/`:

```text
docker-compose.yml
.env
```

On the VM, set `HUSH_ALLOWED_HOSTS` in `.env` to include the current external IP.
Then pull and run the published artifact:

```bash
cd ~/hush-container
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
docker compose pull
docker compose up -d --no-build
docker compose ps
curl -fsS http://127.0.0.1:57327/status
docker image inspect \
  us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush:v1 \
  --format 'ID={{.Id}} REPO_DIGESTS={{json .RepoDigests}} ARCH={{.Architecture}}'
```

Open `http://VM_PUBLIC_IP:57327`, run the same transcription test, and capture
the browser plus terminal output. Compare the registry digest with the VM
`RepoDigests` value on screen.

## 6. Cost closeout

After recording and evidence collection:

```bash
gcloud compute instances stop hush-vm \
  --zone=us-central1-a \
  --project=hush-milestone-2-20260922
```

Capture the stopped VM status if the instructor expects cost-control evidence.
