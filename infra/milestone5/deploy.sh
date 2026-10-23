#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
gcloud iam service-accounts add-iam-policy-binding "hush-runtime@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
  --project="$GOOGLE_CLOUD_PROJECT" \
  --member="serviceAccount:${GOOGLE_CLOUD_PROJECT}.svc.id.goog[hush/hush-runtime]" \
  --role=roles/iam.workloadIdentityUser --format=none
kubectl apply -f "$HUSH_INFRA_DIR/namespace.yaml"
for resource in backendconfigs.cloud.google.com frontendconfigs.networking.gke.io managedcertificates.networking.gke.io; do
  kubectl wait --for=create "crd/$resource" --timeout=180s
  kubectl wait --for=condition=Established "crd/$resource" --timeout=180s
done
kubectl api-resources --cached=false >/dev/null
kubectl apply -f "$HUSH_INFRA_DIR/backend-config.yaml" -f "$HUSH_INFRA_DIR/service.yaml" \
  -f "$HUSH_INFRA_DIR/certificate.yaml" -f "$HUSH_INFRA_DIR/ingress.yaml"
# Deliberately resumes the active deployment. Do not run during standby.
kubectl apply -f "$HUSH_INFRA_DIR/deployment.yaml" -f "$HUSH_INFRA_DIR/hpa.yaml" -f "$HUSH_INFRA_DIR/pdb.yaml"
kubectl -n "$HUSH_NAMESPACE" rollout status deployment hush --timeout=900s
