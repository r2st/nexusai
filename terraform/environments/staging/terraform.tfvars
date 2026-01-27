# =============================================================================
# NexusAI Staging Environment Configuration
# =============================================================================

environment    = "staging"
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
cost_center = "engineering-staging"

# Networking
vnet_cidr = "10.1.0.0/16"
subnet_cidrs = {
  app               = "10.1.1.0/24"
  database          = "10.1.2.0/24"
  bastion           = "10.1.3.0/24"
  private_endpoints = "10.1.4.0/24"
}

# Database
db_name             = "nexusai"
db_username         = "nexusai_admin"
db_storage_mb       = 65536  # 64 GB
db_backup_retention = 14

# Storage
storage_retention_days = 60

# Compute
deployment_type = "kubernetes"
admin_username  = "nexusai_admin"

# Security
admin_object_ids = []

# Monitoring
log_retention_days = 30
enable_alerts      = true
alert_email        = ""

# Feature flags
enable_private_endpoints = true
enable_cmk_encryption    = true
enable_defender          = true
