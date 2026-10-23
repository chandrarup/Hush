#!/usr/bin/env bash
set -euo pipefail
PROJECT=hush-milestone-2-20260922
REGION=us-central1
NODE_SA="hush-gke-node@${PROJECT}.iam.gserviceaccount.com"
gcloud services enable container.googleapis.com cloudbuild.googleapis.com --project="$PROJECT" --quiet
if ! gcloud iam service-accounts describe "$NODE_SA" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud iam service-accounts create hush-gke-node --display-name='Hush GKE nodes' --project="$PROJECT" --quiet
fi
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$NODE_SA" --role=roles/container.defaultNodeServiceAccount --condition=None --format=none
gcloud artifacts repositories add-iam-policy-binding hush-containers --location="$REGION" --project="$PROJECT" --member="serviceAccount:$NODE_SA" --role=roles/artifactregistry.reader --format=none
if ! gcloud compute networks subnets describe hush-subnet --region="$REGION" --project="$PROJECT" --format='value(secondaryIpRanges.rangeName)' | tr ';' '\n' | grep -qx hush-m5-pods; then
  gcloud compute networks subnets update hush-subnet --region="$REGION" --project="$PROJECT" --add-secondary-ranges=hush-m5-pods=10.30.0.0/16,hush-m5-services=10.31.0.0/20 --quiet
fi
if ! gcloud compute addresses describe hush-m5-ip --global --project="$PROJECT" >/dev/null 2>&1; then
  gcloud compute addresses create hush-m5-ip --global --ip-version=IPV4 --project="$PROJECT" --quiet
fi
if ! gcloud container clusters describe hush-m5 --region="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud container clusters create-auto hush-m5 --region="$REGION" --project="$PROJECT" \
    --network=hush-vpc --subnetwork=hush-subnet \
    --cluster-secondary-range-name=hush-m5-pods --services-secondary-range-name=hush-m5-services \
    --enable-private-nodes --master-ipv4-cidr=172.18.171.0/28 --enable-dns-access \
    --service-account="$NODE_SA" --release-channel=regular \
    --logging=SYSTEM,WORKLOAD --monitoring=SYSTEM \
    --labels=app=hush,milestone=5 --async --quiet
fi
gcloud compute addresses describe hush-m5-ip --global --project="$PROJECT" --format='value(address)'
