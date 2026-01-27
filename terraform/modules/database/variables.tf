# =============================================================================
# Database Module - Variables
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

# Database configuration
variable "db_name" {
  description = "Database name"
  type        = string
}

variable "db_username" {
  description = "Database administrator username"
  type        = string
}

variable "db_sku" {
  description = "Database SKU/instance type"
  type        = string
}

variable "db_storage_mb" {
  description = "Database storage in MB"
  type        = number
}

variable "db_backup_retention" {
  description = "Backup retention in days"
  type        = number
  default     = 7
}

# Networking
variable "subnet_id" {
  description = "Subnet ID for database"
  type        = string
}

variable "private_dns_zone_id" {
  description = "Private DNS zone ID (Azure)"
  type        = string
  default     = null
}

variable "security_group_id" {
  description = "Security group ID (AWS)"
  type        = string
  default     = null
}

variable "db_subnet_group_name" {
  description = "DB subnet group name (AWS)"
  type        = string
  default     = null
}

# Encryption
variable "key_vault_key_id" {
  description = "Key Vault key ID for CMK encryption"
  type        = string
  default     = null
}

# High availability
variable "enable_ha" {
  description = "Enable high availability"
  type        = bool
  default     = false
}

variable "enable_read_replica" {
  description = "Enable read replica"
  type        = bool
  default     = false
}
