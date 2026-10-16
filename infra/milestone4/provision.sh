#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-hush-milestone-2-20260922}"
REGION="${HUSH_REGION:-us-central1}"
ZONE="${HUSH_ZONE:-us-central1-a}"
NETWORK="${HUSH_NETWORK:-hush-vpc}"
SUBNET="${HUSH_SUBNET:-hush-subnet}"
INSTANCE="${HUSH_SQL_INSTANCE:-hush-postgres-m4}"
DATABASE="${HUSH_DB_NAME:-hush}"
DATABASE_USER="${HUSH_DB_USER:-hush_app}"
SERVICE_ACCOUNT_NAME="${HUSH_SERVICE_ACCOUNT:-hush-runtime}"
BUCKET="${HUSH_UPLOAD_BUCKET:-${PROJECT_ID}-uploads}"
VM="${HUSH_VM:-hush-vm}"
PSA_RANGE="google-managed-services-hush-vpc"

gcloud config set project "${PROJECT_ID}"
gcloud services enable \
  sqladmin.googleapis.com \
  servicenetworking.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com

if ! gcloud compute addresses describe "${PSA_RANGE}" --global >/dev/null 2>&1; then
  gcloud compute addresses create "${PSA_RANGE}" \
    --global \
    --purpose=VPC_PEERING \
    --addresses=10.20.0.0 \
    --prefix-length=24 \
    --network="${NETWORK}"
fi

if ! gcloud services vpc-peerings list \
  --network="${NETWORK}" \
  --service=servicenetworking.googleapis.com \
  --format='value(network)' | grep -q .; then
  gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges="${PSA_RANGE}" \
    --network="${NETWORK}"
fi

if ! gcloud iam service-accounts describe \
  "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="Hush managed runtime"
fi

if ! gcloud sql instances describe "${INSTANCE}" >/dev/null 2>&1; then
  gcloud sql instances create "${INSTANCE}" \
    --database-version=POSTGRES_15 \
    --region="${REGION}" \
    --tier=db-f1-micro \
    --storage-type=SSD \
    --storage-size=10 \
    --network="projects/${PROJECT_ID}/global/networks/${NETWORK}" \
    --no-assign-ip \
    --availability-type=zonal \
    --backup-start-time=08:00 \
    --enable-point-in-time-recovery
fi

# Converge an existing instance as well as a newly created one. A reused or
# drifted instance must not retain a public IPv4 endpoint.
gcloud sql instances patch "${INSTANCE}" \
  --network="projects/${PROJECT_ID}/global/networks/${NETWORK}" \
  --no-assign-ip \
  --quiet

PUBLIC_IP_ENABLED="$(gcloud sql instances describe "${INSTANCE}" \
  --format='value(settings.ipConfiguration.ipv4Enabled)')"
if [[ "${PUBLIC_IP_ENABLED,,}" != "false" ]]; then
  echo "Cloud SQL public IPv4 is still enabled; refusing to continue." >&2
  exit 1
fi

gcloud sql databases describe "${DATABASE}" --instance="${INSTANCE}" >/dev/null 2>&1 \
  || gcloud sql databases create "${DATABASE}" --instance="${INSTANCE}"

for secret in hush-db-password hush-team-token; do
  if ! gcloud secrets describe "${secret}" >/dev/null 2>&1; then
    gcloud secrets create "${secret}" --replication-policy=automatic
  fi
done

if ! gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET}" \
    --location="${REGION}" \
    --uniform-bucket-level-access \
    --public-access-prevention
fi
gcloud storage buckets update "gs://${BUCKET}" \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --lifecycle-file="$(dirname "$0")/gcs-lifecycle.json"

gcloud compute networks subnets update "${SUBNET}" \
  --region="${REGION}" \
  --enable-private-ip-google-access

echo "Infrastructure shell is ready. Add versions to both Hush secrets and set"
echo "the Cloud SQL user's password through a secure operator session, then run"
echo "infra/milestone4/bind-iam.sh. No secret value belongs in this repository."
echo "Target VM: ${VM} (${ZONE})"
