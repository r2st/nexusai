# =============================================================================
# NexusAI Development Environment Configuration
# =============================================================================

environment    = "dev"
cloud_provider = "azure"  # Change to "aws" or "gcp" as needed

# Azure Configuration
azure_location = "eastus"

# AWS Configuration
aws_region = "us-east-1"

# GCP Configuration
gcp_project_id = ""
gcp_region     = "us-central1"

# Resource Ownership
owner       = "development-team"
cost_center = "engineering-dev"

# Networking
vnet_cidr = "10.0.0.0/16"
subnet_cidrs = {
  app               = "10.0.1.0/24"
  database          = "10.0.2.0/24"
  bastion           = "10.0.3.0/24"
  private_endpoints = "10.0.4.0/24"
}

# Database
db_name             = "nexusai"
db_username         = "nexusai_admin"
db_storage_mb       = 32768  # 32 GB
db_backup_retention = 7

# Storage
storage_retention_days = 30

# Compute
deployment_type = "kubernetes"
admin_username  = "nexusai_admin"

# Security (add your own object IDs)
admin_object_ids = []

# Monitoring
log_retention_days = 14
enable_alerts      = true
alert_email        = ""

# Feature flags
enable_private_endpoints = false  # Disabled for dev to reduce costs
enable_cmk_encryption    = false  # Disabled for dev
enable_defender          = false  # Disabled for dev
