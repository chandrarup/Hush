# Adopted from the live Hush project; do not replace existing resources.

resource "google_project_iam_member" "hush_runtime_cloudsql_client" {
  member  = "serviceAccount:hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project = var.project_id
  role    = "roles/cloudsql.client"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "hush_runtime_artifactregistry_reader" {
  member  = "serviceAccount:hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "hush_team_token_hush_runtime" {
  member    = "serviceAccount:hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  secret_id = "projects/hush-milestone-2-20260922/secrets/hush-team-token"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "hush_team_token_hush_build" {
  member    = "serviceAccount:hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  secret_id = "projects/hush-milestone-2-20260922/secrets/hush-team-token"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "hush_db_password_hush_runtime" {
  member    = "serviceAccount:hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  secret_id = "projects/hush-milestone-2-20260922/secrets/hush-db-password"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "bucket_uploads_hush_runtime" {
  bucket = "b/hush-milestone-2-20260922-uploads"
  member = "serviceAccount:hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com"
  role   = "roles/storage.objectUser"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_artifact_registry_repository_iam_member" "repo_iam_hush_build" {
  location   = "us-central1"
  member     = "serviceAccount:hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project    = var.project_id
  repository = "projects/hush-milestone-2-20260922/locations/us-central1/repositories/hush-containers"
  role       = "roles/artifactregistry.writer"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "hush_runtime_logging_logWriter" {
  member  = "serviceAccount:hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project = var.project_id
  role    = "roles/logging.logWriter"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "bucket_build_source_hush_build" {
  bucket = "b/hush-milestone-2-20260922-build-source"
  member = "serviceAccount:hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com"
  role   = "roles/storage.objectViewer"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "hush_build_container_clusterViewer" {
  member  = "serviceAccount:hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project = var.project_id
  role    = "roles/container.clusterViewer"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_artifact_registry_repository_iam_member" "repo_iam_hush_gke_node" {
  location   = "us-central1"
  member     = "serviceAccount:hush-gke-node@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project    = var.project_id
  repository = "projects/hush-milestone-2-20260922/locations/us-central1/repositories/hush-containers"
  role       = "roles/artifactregistry.reader"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "sa_hush_runtime_hush_milestone_2_20260922" {
  member             = "serviceAccount:hush-milestone-2-20260922.svc.id.goog[hush/hush-runtime]"
  role               = "roles/iam.workloadIdentityUser"
  service_account_id = "projects/hush-milestone-2-20260922/serviceAccounts/hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "hush_gke_node_container_defaultNodeServiceAccount" {
  member  = "serviceAccount:hush-gke-node@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project = var.project_id
  role    = "roles/container.defaultNodeServiceAccount"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "hush_build_logging_logWriter" {
  member  = "serviceAccount:hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com"
  project = var.project_id
  role    = "roles/logging.logWriter"
  lifecycle {
    prevent_destroy = true
  }
}
