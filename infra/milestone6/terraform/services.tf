# Adopted from the live Hush project; do not replace existing resources.

resource "google_project_service" "pubsub" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "pubsub.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "secretmanager" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "servicemanagement" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "servicemanagement.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "containerregistry" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "containerregistry.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "containerfilesystem" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "containerfilesystem.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "bigquerydatatransfer" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "bigquerydatatransfer.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "cloudapis" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "cloudapis.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "cloudbuild" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "storage" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "storage.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "oslogin" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "oslogin.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "servicenetworking" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "servicenetworking.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "file" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "file.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "dataplex" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "dataplex.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "bigquerystorage" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "bigquerystorage.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "bigqueryconnection" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "bigqueryconnection.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "cloudtrace" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "cloudtrace.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "bigqueryreservation" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "bigqueryreservation.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "serviceusage" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "serviceusage.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "bigquerydatapolicy" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "bigquerydatapolicy.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "bigquery" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "container" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "container.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "iamcredentials" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "iamcredentials.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "analyticshub" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "analyticshub.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "dns" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "dns.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "billingbudgets" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "billingbudgets.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "sql_component" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "sql-component.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "storage_api" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "storage-api.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "sqladmin" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "storage_component" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "storage-component.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "iam" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "iam.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "artifactregistry" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "bigquerymigration" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "bigquerymigration.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "telemetry" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "telemetry.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "compute" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "compute.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "monitoring" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "monitoring.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "logging" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "logging.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "gkebackup" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "gkebackup.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "networkconnectivity" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "networkconnectivity.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "autoscaling" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "autoscaling.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "datastore" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "datastore.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "dataform" {
  deletion_policy    = "DELETE"
  project            = var.project_id
  service            = "dataform.googleapis.com"
  disable_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}
