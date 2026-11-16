# Adopted from the live Hush project; do not replace existing resources.

resource "google_service_networking_connection" "private_services" {
  deletion_policy         = "DELETE"
  network                 = google_compute_network.hush.id
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
  service                 = "servicenetworking.googleapis.com"
  depends_on              = [google_project_service.servicenetworking]
  lifecycle {
    prevent_destroy = true
  }
}

# Password payload remains in Secret Manager; adoption never reads or resets it.
resource "google_sql_user" "application" {
  deletion_policy = "DELETE"
  instance        = google_sql_database_instance.hush.name
  name            = "hush_app"
  project         = var.project_id
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_global_address" "private_services" {
  address         = "172.18.170.0"
  address_type    = "INTERNAL"
  deletion_policy = "DELETE"
  labels          = {}
  name            = "google-managed-services-hush-vpc"
  network         = google_compute_network.hush.id
  prefix_length   = 24
  project         = var.project_id
  purpose         = "VPC_PEERING"
  lifecycle {
    prevent_destroy = true
  }
}
