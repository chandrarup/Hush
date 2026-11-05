resource "google_compute_network" "hush" {
  project                 = var.project_id
  name                    = "hush-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_subnetwork" "hush" {
  project                  = var.project_id
  region                   = var.region
  name                     = "hush-subnet"
  network                  = "https://www.googleapis.com/compute/v1/projects/hush-milestone-2-20260922/global/networks/hush-vpc"
  ip_cidr_range            = "10.10.0.0/24"
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "hush-m5-services"
    ip_cidr_range = "10.31.0.0/20"
  }

  secondary_ip_range {
    range_name    = "hush-m5-pods"
    ip_cidr_range = "10.30.0.0/16"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_global_address" "hush_ingress" {
  project      = var.project_id
  name         = "hush-m5-ip"
  address      = "34.36.104.111"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"

  lifecycle {
    prevent_destroy = true
  }
}
