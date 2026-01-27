# =============================================================================
# Terraform State Backend Configuration - Development
# =============================================================================
# Uncomment the appropriate section for your cloud provider

# Azure Storage Backend
# resource_group_name  = "nexusai-terraform-state"
# storage_account_name = "nexusaitfstatedev"
# container_name       = "tfstate"
# key                  = "dev/nexusai.tfstate"

# AWS S3 Backend
# bucket         = "nexusai-terraform-state-dev"
# key            = "dev/nexusai.tfstate"
# region         = "us-east-1"
# dynamodb_table = "nexusai-terraform-locks-dev"
# encrypt        = true

# GCP GCS Backend
# bucket = "nexusai-terraform-state-dev"
# prefix = "terraform/dev"
