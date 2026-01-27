# =============================================================================
# Monitoring Module - Multi-Cloud Observability
# =============================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.10"
    }
  }
}

# =============================================================================
# Azure Monitor
# =============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.name_prefix}-logs"
  location            = var.azure_location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = var.tags
}

resource "azurerm_application_insights" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.name_prefix}-appinsights"
  location            = var.azure_location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.main[0].id
  application_type    = "web"

  tags = var.tags
}

# Action Group for Alerts
resource "azurerm_monitor_action_group" "main" {
  count               = var.cloud_provider == "azure" && var.enable_alerts ? 1 : 0
  name                = "${var.name_prefix}-alerts"
  resource_group_name = var.resource_group_name
  short_name          = "nexusalert"

  dynamic "email_receiver" {
    for_each = var.alert_email != "" ? [1] : []
    content {
      name                    = "email-alerts"
      email_address           = var.alert_email
      use_common_alert_schema = true
    }
  }

  tags = var.tags
}

# CPU Alert
resource "azurerm_monitor_metric_alert" "cpu" {
  count               = var.cloud_provider == "azure" && var.enable_alerts && var.compute_id != null ? 1 : 0
  name                = "${var.name_prefix}-cpu-alert"
  resource_group_name = var.resource_group_name
  scopes              = [var.compute_id]
  description         = "Alert when CPU exceeds 80%"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "node_cpu_usage_percentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.main[0].id
  }

  tags = var.tags
}

# Memory Alert
resource "azurerm_monitor_metric_alert" "memory" {
  count               = var.cloud_provider == "azure" && var.enable_alerts && var.compute_id != null ? 1 : 0
  name                = "${var.name_prefix}-memory-alert"
  resource_group_name = var.resource_group_name
  scopes              = [var.compute_id]
  description         = "Alert when memory exceeds 85%"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "node_memory_working_set_percentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 85
  }

  action {
    action_group_id = azurerm_monitor_action_group.main[0].id
  }

  tags = var.tags
}

# Database Connection Alert
resource "azurerm_monitor_metric_alert" "database_connections" {
  count               = var.cloud_provider == "azure" && var.enable_alerts && var.database_id != null ? 1 : 0
  name                = "${var.name_prefix}-db-connections-alert"
  resource_group_name = var.resource_group_name
  scopes              = [var.database_id]
  description         = "Alert when database connections exceed 80%"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.DBforPostgreSQL/flexibleServers"
    metric_name      = "active_connections"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.main[0].id
  }

  tags = var.tags
}

# =============================================================================
# AWS CloudWatch
# =============================================================================

resource "aws_cloudwatch_log_group" "main" {
  count             = var.cloud_provider == "aws" ? 1 : 0
  name              = "/nexusai/${var.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_sns_topic" "alerts" {
  count = var.cloud_provider == "aws" && var.enable_alerts ? 1 : 0
  name  = "${var.name_prefix}-alerts"

  tags = var.tags
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.cloud_provider == "aws" && var.enable_alerts && var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# EKS CPU Alarm
resource "aws_cloudwatch_metric_alarm" "eks_cpu" {
  count               = var.cloud_provider == "aws" && var.enable_alerts && var.compute_id != null ? 1 : 0
  alarm_name          = "${var.name_prefix}-eks-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "node_cpu_utilization"
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EKS cluster CPU utilization is high"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ClusterName = var.compute_id
  }

  tags = var.tags
}

# RDS CPU Alarm
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  count               = var.cloud_provider == "aws" && var.enable_alerts && var.database_id != null ? 1 : 0
  alarm_name          = "${var.name_prefix}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization is high"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    DBInstanceIdentifier = var.database_id
  }

  tags = var.tags
}

# =============================================================================
# GCP Cloud Monitoring
# =============================================================================

resource "google_monitoring_notification_channel" "email" {
  count        = var.cloud_provider == "gcp" && var.enable_alerts && var.alert_email != "" ? 1 : 0
  display_name = "${var.name_prefix} Email Alerts"
  project      = var.gcp_project_id
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_alert_policy" "cpu" {
  count        = var.cloud_provider == "gcp" && var.enable_alerts ? 1 : 0
  display_name = "${var.name_prefix} High CPU"
  project      = var.gcp_project_id
  combiner     = "OR"

  conditions {
    display_name = "CPU Utilization > 80%"

    condition_threshold {
      filter          = "resource.type = \"k8s_node\" AND metric.type = \"kubernetes.io/node/cpu/allocatable_utilization\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.alert_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  documentation {
    content   = "CPU utilization exceeded 80% threshold"
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "memory" {
  count        = var.cloud_provider == "gcp" && var.enable_alerts ? 1 : 0
  display_name = "${var.name_prefix} High Memory"
  project      = var.gcp_project_id
  combiner     = "OR"

  conditions {
    display_name = "Memory Utilization > 85%"

    condition_threshold {
      filter          = "resource.type = \"k8s_node\" AND metric.type = \"kubernetes.io/node/memory/allocatable_utilization\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.alert_email != "" ? [google_monitoring_notification_channel.email[0].id] : []
}
