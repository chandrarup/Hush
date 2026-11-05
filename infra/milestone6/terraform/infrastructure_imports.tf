import {
  to = google_compute_network.hush
  id = "projects/hush-milestone-2-20260922/global/networks/hush-vpc"
}

import {
  to = google_compute_subnetwork.hush
  id = "projects/hush-milestone-2-20260922/regions/us-central1/subnetworks/hush-subnet"
}

import {
  to = google_compute_global_address.hush_ingress
  id = "projects/hush-milestone-2-20260922/global/addresses/hush-m5-ip"
}

import {
  to = google_container_cluster.hush
  id = "projects/hush-milestone-2-20260922/locations/us-central1/clusters/hush-m5"
}

import {
  to = google_artifact_registry_repository.hush
  id = "projects/hush-milestone-2-20260922/locations/us-central1/repositories/hush-containers"
}

import {
  to = google_sql_database_instance.hush
  id = "projects/hush-milestone-2-20260922/instances/hush-postgres-m4"
}

import {
  to = google_sql_database.hush
  id = "projects/hush-milestone-2-20260922/instances/hush-postgres-m4/databases/hush"
}

import {
  to = google_storage_bucket.uploads
  id = "hush-milestone-2-20260922/hush-milestone-2-20260922-uploads"
}

import {
  to = google_storage_bucket.build_source
  id = "hush-milestone-2-20260922/hush-milestone-2-20260922-build-source"
}

import {
  to = google_service_account.runtime
  id = "projects/hush-milestone-2-20260922/serviceAccounts/hush-runtime@hush-milestone-2-20260922.iam.gserviceaccount.com"
}

import {
  to = google_service_account.build
  id = "projects/hush-milestone-2-20260922/serviceAccounts/hush-build@hush-milestone-2-20260922.iam.gserviceaccount.com"
}

import {
  to = google_service_account.gke_node
  id = "projects/hush-milestone-2-20260922/serviceAccounts/hush-gke-node@hush-milestone-2-20260922.iam.gserviceaccount.com"
}

import {
  to = google_secret_manager_secret.db_password
  id = "projects/hush-milestone-2-20260922/secrets/hush-db-password"
}

import {
  to = google_secret_manager_secret.team_token
  id = "projects/hush-milestone-2-20260922/secrets/hush-team-token"
}
