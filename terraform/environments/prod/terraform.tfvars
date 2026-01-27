# =============================================================================
# NexusAI Production Environment Configuration
# =============================================================================

environment    = "prod"
cloud_provider = "azure"

# Azure Configuration
azure_location = "eastus"

# AWS Configuration
aws_region = "us-east-1"

# GCP Configuration
gcp_project_id = ""
gcp_region     = "us-central1"

# Resource Ownership
owner       = "platform-team"
cost_center = "engineering-prod"

# Networking
vnet_cidr = "10.2.0.0/16"
subnet_cidrs = {
  app               = "10.2.1.0/24"
  database          = "10.2.2.0/24"
  bastion           = "10.2.3.0/24"
  private_endpoints = "10.2.4.0/24"
}

# Database
db_name             = "nexusai"
db_username         = "nexusai_admin"
db_storage_mb       = 131072  # 128 GB
db_backup_retention = 35      # 5 weeks for compliance

# Storage
storage_retention_days = 90

# Compute
deployment_type = "kubernetes"
admin_username  = "nexusai_admin"

# Security
admin_object_ids = []

# Monitoring
log_retention_days = 90
enable_alerts      = true
alert_email        = ""

# Feature flags - ALL ENABLED for production
enable_private_endpoints = true
enable_cmk_encryption    = true
enable_defender          = true
