# Adopted from the live Hush project; do not replace existing resources.

resource "google_cloudbuildv2_repository" "hush" {
  annotations       = {}
  deletion_policy   = "DELETE"
  location          = "us-central1"
  name              = "hush-team"
  parent_connection = google_cloudbuildv2_connection.github.name
  project           = var.project_id
  remote_uri        = "https://github.com/chandrarup/Hush.git"
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_cloudbuildv2_connection" "github" {
  annotations     = {}
  deletion_policy = "DELETE"
  disabled        = false
  location        = "us-central1"
  name            = "hush-github-owner"
  project         = var.project_id
  github_config {
    app_installation_id = 179009593
    authorizer_credential {
      oauth_token_secret_version = "projects/hush-milestone-2-20260922/locations/us-central1/secrets/hush-github-owner-github-oauthtoken-f4966e/versions/latest"
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_cloudbuild_trigger" "deploy" {
  deletion_policy = "DELETE"
  description     = "Milestone 6 push deployment with verified rollback"
  disabled        = false
  filename        = "infra/milestone6/cloudbuild.yaml"
  ignored_files   = []
  included_files  = []
  location        = "us-central1"
  name            = "hush-milestone6-deploy"
  project         = var.project_id
  service_account = "projects/hush-milestone-2-20260922/serviceAccounts/hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com"
  substitutions   = {}
  tags            = []
  approval_config {
    approval_required = false
  }
  repository_event_config {
    repository = google_cloudbuildv2_repository.hush.id
    push {
      branch       = "^milestone6-deploy$"
      invert_regex = false
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}
