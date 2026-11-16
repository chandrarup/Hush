resource "google_container_cluster" "hush" {
  project             = var.project_id
  location            = var.region
  name                = "hush-m5"
  enable_autopilot    = true
  deletion_protection = true
  network             = "projects/hush-milestone-2-20260922/global/networks/hush-vpc"
  subnetwork          = "projects/hush-milestone-2-20260922/regions/us-central1/subnetworks/hush-subnet"

  ip_allocation_policy {
    cluster_secondary_range_name  = "hush-m5-pods"
    services_secondary_range_name = "hush-m5-services"
  }

  private_cluster_config {
    enable_private_nodes   = true
    master_ipv4_cidr_block = "172.18.171.0/28"
  }

  release_channel {
    channel = "REGULAR"
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_artifact_registry_repository" "hush" {
  project                = var.project_id
  location               = var.region
  repository_id          = "hush-containers"
  format                 = "DOCKER"
  description            = "Versioned Hush Milestone 3 container images"
  cleanup_policy_dry_run = true

  docker_config {
    immutable_tags = false
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "hush-runtime"
  display_name = "Hush managed runtime"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "build" {
  project      = var.project_id
  account_id   = "hush-build"
  display_name = "Hush image builds"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "gke_node" {
  project      = var.project_id
  account_id   = "hush-gke-node"
  display_name = "Hush GKE nodes"

  lifecycle {
    prevent_destroy = true
  }
}
