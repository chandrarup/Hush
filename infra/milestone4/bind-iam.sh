#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-hush-milestone-2-20260922}"
REGION="${HUSH_REGION:-us-central1}"
SERVICE_ACCOUNT_NAME="${HUSH_SERVICE_ACCOUNT:-hush-runtime}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
BUCKET="${HUSH_UPLOAD_BUCKET:-${PROJECT_ID}-uploads}"
VM="${HUSH_VM:-hush-vm}"
ZONE="${HUSH_ZONE:-us-central1-a}"

for role in roles/artifactregistry.reader roles/cloudsql.client roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="${role}" \
    --condition=None
done

for secret in hush-team-token hush-db-password; do
  gcloud secrets add-iam-policy-binding "${secret}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role=roles/secretmanager.secretAccessor \
    --condition=None
done

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role=roles/storage.objectUser

gcloud compute instances set-service-account "${VM}" \
  --zone="${ZONE}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --scopes=cloud-platform
