# =============================================================================
# Terraform State Backend Configuration - Production
# =============================================================================
# Uncomment the appropriate section for your cloud provider

# Azure Storage Backend
# resource_group_name  = "nexusai-terraform-state"
# storage_account_name = "nexusaitfstateprod"
# container_name       = "tfstate"
# key                  = "prod/nexusai.tfstate"

# AWS S3 Backend
# bucket         = "nexusai-terraform-state-prod"
# key            = "prod/nexusai.tfstate"
# region         = "us-east-1"
# dynamodb_table = "nexusai-terraform-locks-prod"
# encrypt        = true

# GCP GCS Backend
# bucket = "nexusai-terraform-state-prod"
# prefix = "terraform/prod"
