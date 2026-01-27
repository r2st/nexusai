# =============================================================================
# Compute Module - Variables
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

# Compute configuration
variable "deployment_type" {
  description = "Deployment type (kubernetes or vm)"
  type        = string
  default     = "kubernetes"
}

variable "vm_size" {
  description = "VM size/instance type"
  type        = string
}

variable "node_count" {
  description = "Initial node count"
  type        = number
}

variable "min_node_count" {
  description = "Minimum node count for autoscaling"
  type        = number
}

variable "max_node_count" {
  description = "Maximum node count for autoscaling"
  type        = number
}

# Networking
variable "subnet_id" {
  description = "Subnet ID for compute resources"
  type        = string
}

variable "bastion_subnet_id" {
  description = "Subnet ID for bastion host"
  type        = string
  default     = null
}

# SSH
variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
  default     = ""
}

variable "admin_username" {
  description = "Administrator username"
  type        = string
  default     = "nexusai_admin"
}

# Monitoring
variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID (Azure)"
  type        = string
  default     = null
}
