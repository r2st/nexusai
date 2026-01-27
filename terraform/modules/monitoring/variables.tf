# =============================================================================
# Monitoring Module - Variables
# =============================================================================

variable "cloud_provider" {
  description = "Cloud provider (azure, aws, gcp)"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Azure
variable "azure_location" {
  description = "Azure region"
  type        = string
  default     = ""
}

variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = ""
}

# AWS
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = ""
}

# GCP
variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
  default     = ""
}

# Monitoring configuration
variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

variable "enable_alerts" {
  description = "Enable monitoring alerts"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}

# Resources to monitor
variable "database_id" {
  description = "Database resource ID"
  type        = string
  default     = null
}

variable "storage_id" {
  description = "Storage resource ID"
  type        = string
  default     = null
}

variable "compute_id" {
  description = "Compute resource ID"
  type        = string
  default     = null
}
