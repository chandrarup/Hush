# Adopted from the live Hush project; do not replace existing resources.

resource "google_billing_budget" "monthly" {
  provider        = google.billing
  billing_account = "01B327-C0874B-CFCAC1"
  deletion_policy = "DELETE"
  display_name    = "Hush Budget"
  ownership_scope = "BILLING_ACCOUNT"
  all_updates_rule {
    disable_default_iam_recipients   = false
    enable_project_level_recipients  = true
    monitoring_notification_channels = []
    schema_version                   = "1.0"
  }
  amount {
    specified_amount {
      currency_code = "USD"
      nanos         = 0
      units         = "50"
    }
  }
  budget_filter {
    calendar_period        = "MONTH"
    credit_types           = []
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
    labels                 = {}
    projects               = ["projects/278368955479"]
    resource_ancestors     = []
    services               = []
    subaccounts            = []
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 0.2
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 0.5
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 1
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_billing_budget" "milestone5" {
  provider        = google.billing
  billing_account = "01B327-C0874B-CFCAC1"
  deletion_policy = "DELETE"
  display_name    = "Hush Milestone 5 - 45 day USD100 target"
  amount {
    specified_amount {
      currency_code = "USD"
      nanos         = 0
      units         = "100"
    }
  }
  budget_filter {
    credit_types           = ["FREE_TIER"]
    credit_types_treatment = "INCLUDE_SPECIFIED_CREDITS"
    labels                 = {}
    projects               = ["projects/278368955479"]
    resource_ancestors     = []
    services               = []
    subaccounts            = []
    custom_period {
      end_date {
        day   = 6
        month = 12
        year  = 2026
      }
      start_date {
        day   = 22
        month = 10
        year  = 2026
      }
    }
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 0.5
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 0.75
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 0.9
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 1
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 1.25
  }
  threshold_rules {
    spend_basis       = "CURRENT_SPEND"
    threshold_percent = 1.5
  }
  lifecycle {
    prevent_destroy = true
  }
}
