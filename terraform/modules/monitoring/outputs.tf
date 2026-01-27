# =============================================================================
# Monitoring Module - Outputs
# =============================================================================

output "workspace_id" {
  description = "Log Analytics / CloudWatch workspace ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_log_analytics_workspace.main) > 0 ? azurerm_log_analytics_workspace.main[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_cloudwatch_log_group.main) > 0 ? aws_cloudwatch_log_group.main[0].arn : null
  ) : null
}

output "application_insights_connection_string" {
  description = "Application Insights connection string (Azure)"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_application_insights.main) > 0 ? azurerm_application_insights.main[0].connection_string : null
  ) : null
  sensitive = true
}

output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key (Azure)"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_application_insights.main) > 0 ? azurerm_application_insights.main[0].instrumentation_key : null
  ) : null
  sensitive = true
}

output "alert_topic_arn" {
  description = "SNS topic ARN for alerts (AWS)"
  value = var.cloud_provider == "aws" ? (
    length(aws_sns_topic.alerts) > 0 ? aws_sns_topic.alerts[0].arn : null
  ) : null
}
