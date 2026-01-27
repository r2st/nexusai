# =============================================================================
# Key Vault Module - Variables
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

# Access configuration
variable "admin_object_ids" {
  description = "Object IDs of administrators"
  type        = list(string)
  default     = []
}
