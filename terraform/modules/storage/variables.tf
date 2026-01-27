# =============================================================================
# Storage Module - Variables
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

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = ""
}

# Storage configuration
variable "enable_versioning" {
  description = "Enable object versioning"
  type        = bool
  default     = true
}

variable "enable_immutability" {
  description = "Enable immutability for compliance"
  type        = bool
  default     = false
}

variable "retention_days" {
  description = "Retention period in days"
  type        = number
  default     = 90
}

# Encryption
variable "key_vault_key_id" {
  description = "Key Vault key ID for CMK encryption"
  type        = string
  default     = null
}
