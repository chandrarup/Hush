locals {
  metric_filter = join(" AND ", compact(split("\n", trimspace(file("${path.module}/../observability/hush-http-5xx.filter")))))
  alert_policy  = jsondecode(file("${path.module}/../observability/alert-policy.json"))
}

resource "google_logging_metric" "hush_http_5xx" {
  project     = var.project_id
  name        = "hush_http_5xx_count"
  description = "Counts Hush application JSON HTTP 5xx request logs, excluding health and readiness probes."
  filter      = local.metric_filter

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_monitoring_dashboard" "hush_milestone6" {
  # The Monitoring API returns the numeric project in this dashboard's name.
  project        = "278368955479"
  dashboard_json = file("${path.module}/../observability/dashboard.json")

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_monitoring_notification_channel" "hush_team_email" {
  project      = var.project_id
  type         = "email"
  display_name = "Hush Milestone 6 team alert"
  description  = "Hush application HTTP 5xx alert recipient"
  enabled      = true
  labels = {
    # Email is private in source control, but the API does not mark this label
    # sensitive. Avoid a perpetual sensitivity-only update after import.
    email_address = nonsensitive(var.alert_email)
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_monitoring_alert_policy" "hush_http_5xx" {
  project               = var.project_id
  display_name          = local.alert_policy.displayName
  combiner              = local.alert_policy.combiner
  enabled               = local.alert_policy.enabled
  notification_channels = [google_monitoring_notification_channel.hush_team_email.name]

  conditions {
    display_name = local.alert_policy.conditions[0].displayName

    condition_threshold {
      filter          = local.alert_policy.conditions[0].conditionThreshold.filter
      comparison      = local.alert_policy.conditions[0].conditionThreshold.comparison
      threshold_value = local.alert_policy.conditions[0].conditionThreshold.thresholdValue
      duration        = local.alert_policy.conditions[0].conditionThreshold.duration

      aggregations {
        alignment_period     = local.alert_policy.conditions[0].conditionThreshold.aggregations[0].alignmentPeriod
        per_series_aligner   = local.alert_policy.conditions[0].conditionThreshold.aggregations[0].perSeriesAligner
        cross_series_reducer = local.alert_policy.conditions[0].conditionThreshold.aggregations[0].crossSeriesReducer
      }

      trigger {
        count = local.alert_policy.conditions[0].conditionThreshold.trigger.count
      }
    }
  }

  documentation {
    content   = local.alert_policy.documentation.content
    mime_type = local.alert_policy.documentation.mimeType
  }

  lifecycle {
    prevent_destroy = true
  }
}
