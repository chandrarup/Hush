resource "google_sql_database_instance" "hush" {
  project             = var.project_id
  region              = var.region
  name                = "hush-postgres-m4"
  database_version    = "POSTGRES_15"
  deletion_protection = true

  settings {
    tier                        = "db-f1-micro"
    availability_type           = "ZONAL"
    disk_size                   = 10
    disk_type                   = "PD_SSD"
    disk_autoresize             = true
    enable_dataplex_integration = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "08:00"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = "projects/hush-milestone-2-20260922/global/networks/hush-vpc"
      ssl_mode        = "ALLOW_UNENCRYPTED_AND_ENCRYPTED"
    }

    location_preference {
      zone = "us-central1-a"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_sql_database" "hush" {
  project   = var.project_id
  instance  = "hush-postgres-m4"
  name      = "hush"
  charset   = "UTF8"
  collation = "en_US.UTF8"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket" "uploads" {
  project                     = var.project_id
  name                        = "hush-milestone-2-20260922-uploads"
  location                    = "US-CENTRAL1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 30
      matches_prefix = ["uploads/"]
    }
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket" "build_source" {
  project                     = var.project_id
  name                        = "hush-milestone-2-20260922-build-source"
  location                    = "US-CENTRAL1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret" "db_password" {
  project   = var.project_id
  secret_id = "hush-db-password"

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret" "team_token" {
  project   = var.project_id
  secret_id = "hush-team-token"

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}
