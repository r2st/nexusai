# =============================================================================
# NexusAI Infrastructure - Variables
# =============================================================================

# =============================================================================
# General Configuration
# =============================================================================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "cloud_provider" {
  description = "Cloud provider to use (azure, aws, gcp)"
  type        = string
  default     = "azure"

  validation {
    condition     = contains(["azure", "aws", "gcp"], var.cloud_provider)
    error_message = "Cloud provider must be one of: azure, aws, gcp."
  }
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
  default     = "platform-team"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "engineering"
}

# =============================================================================
# Azure Configuration
# =============================================================================

variable "azure_location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = ""
}

# =============================================================================
# AWS Configuration
# =============================================================================

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
  default     = ""
}

# =============================================================================
# GCP Configuration
# =============================================================================

variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
  default     = ""
}

variable "gcp_region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

# =============================================================================
# Networking Configuration
# =============================================================================

variable "vnet_cidr" {
  description = "CIDR block for the virtual network"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidrs" {
  description = "CIDR blocks for subnets"
  type = object({
    app              = string
    database         = string
    bastion          = string
    private_endpoints = string
  })
  default = {
    app              = "10.0.1.0/24"
    database         = "10.0.2.0/24"
    bastion          = "10.0.3.0/24"
    private_endpoints = "10.0.4.0/24"
  }
}

# =============================================================================
# Database Configuration
# =============================================================================

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "nexusai"
}

variable "db_username" {
  description = "Database administrator username"
  type        = string
  default     = "nexusai_admin"
}

variable "db_storage_mb" {
  description = "Database storage in MB"
  type        = number
  default     = 32768  # 32 GB
}

variable "db_backup_retention" {
  description = "Database backup retention in days"
  type        = number
  default     = 7
}

# =============================================================================
# Storage Configuration
# =============================================================================

variable "storage_retention_days" {
  description = "Storage retention in days"
  type        = number
  default     = 90
}

# =============================================================================
# Compute Configuration
# =============================================================================

variable "deployment_type" {
  description = "Type of deployment (kubernetes or vm)"
  type        = string
  default     = "kubernetes"

  validation {
    condition     = contains(["kubernetes", "vm"], var.deployment_type)
    error_message = "Deployment type must be one of: kubernetes, vm."
  }
}

variable "admin_username" {
  description = "Administrator username for VMs"
  type        = string
  default     = "nexusai_admin"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
  default     = ""
}

# =============================================================================
# Security Configuration
# =============================================================================

variable "admin_object_ids" {
  description = "Object IDs of administrators for Key Vault access"
  type        = list(string)
  default     = []
}

# =============================================================================
# Monitoring Configuration
# =============================================================================

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

# =============================================================================
# Feature Flags
# =============================================================================

variable "enable_private_endpoints" {
  description = "Enable private endpoints for databases"
  type        = bool
  default     = true
}

variable "enable_cmk_encryption" {
  description = "Enable customer-managed key encryption"
  type        = bool
  default     = true
}

variable "enable_defender" {
  description = "Enable security defender"
  type        = bool
  default     = true
}
