variable "project_id" {
  type    = string
  default = "hush-milestone-2-20260922"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "alert_email" {
  description = "Existing email channel recipient. Supply via TF_VAR_alert_email; do not commit a tfvars file."
  type        = string
  sensitive   = true
}
