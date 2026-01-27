# =============================================================================
# NexusAI Infrastructure - Main Terraform Configuration
# =============================================================================
# This is the root module that orchestrates all infrastructure components.
# Supports Azure, AWS, and GCP deployments.
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.10"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Backend configuration - uncomment and configure for your environment
  # backend "azurerm" {
  #   resource_group_name  = "nexusai-terraform-state"
  #   storage_account_name = "nexusaitfstate"
  #   container_name       = "tfstate"
  #   key                  = "nexusai.tfstate"
  # }

  # backend "s3" {
  #   bucket         = "nexusai-terraform-state"
  #   key            = "nexusai.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "nexusai-terraform-locks"
  #   encrypt        = true
  # }

  # backend "gcs" {
  #   bucket = "nexusai-terraform-state"
  #   prefix = "terraform/state"
  # }
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  skip_provider_registration = true
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# =============================================================================
# Local Values
# =============================================================================

locals {
  common_tags = {
    Project     = "NexusAI"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = var.owner
    CostCenter  = var.cost_center
  }

  name_prefix = "nexusai-${var.environment}"

  # Environment-specific sizing
  sizing = {
    dev = {
      vm_size           = "Standard_B2s"
      db_sku            = "B_Gen5_1"
      redis_capacity    = 0
      node_count        = 1
      min_node_count    = 1
      max_node_count    = 3
    }
    staging = {
      vm_size           = "Standard_D2s_v3"
      db_sku            = "GP_Gen5_2"
      redis_capacity    = 1
      node_count        = 2
      min_node_count    = 2
      max_node_count    = 5
    }
    prod = {
      vm_size           = "Standard_D4s_v3"
      db_sku            = "GP_Gen5_4"
      redis_capacity    = 2
      node_count        = 3
      min_node_count    = 3
      max_node_count    = 20
    }
  }

  current_sizing = local.sizing[var.environment]
}

# =============================================================================
# Resource Group (Azure)
# =============================================================================

resource "azurerm_resource_group" "main" {
  count    = var.cloud_provider == "azure" ? 1 : 0
  name     = "${local.name_prefix}-rg"
  location = var.azure_location
  tags     = local.common_tags
}

# =============================================================================
# Networking Module
# =============================================================================

module "networking" {
  source = "./modules/networking"

  cloud_provider    = var.cloud_provider
  environment       = var.environment
  name_prefix       = local.name_prefix
  tags              = local.common_tags

  # Azure
  azure_location    = var.azure_location
  resource_group_name = var.cloud_provider == "azure" ? azurerm_resource_group.main[0].name : ""

  # AWS
  aws_region        = var.aws_region

  # GCP
  gcp_project_id    = var.gcp_project_id
  gcp_region        = var.gcp_region

  # Network configuration
  vnet_cidr         = var.vnet_cidr
  subnet_cidrs      = var.subnet_cidrs
}

# =============================================================================
# Key Vault / Secrets Module
# =============================================================================

module "keyvault" {
  source = "./modules/keyvault"

  cloud_provider      = var.cloud_provider
  environment         = var.environment
  name_prefix         = local.name_prefix
  tags                = local.common_tags

  # Azure
  azure_location      = var.azure_location
  resource_group_name = var.cloud_provider == "azure" ? azurerm_resource_group.main[0].name : ""

  # AWS
  aws_region          = var.aws_region

  # GCP
  gcp_project_id      = var.gcp_project_id

  # Access configuration
  admin_object_ids    = var.admin_object_ids
}

# =============================================================================
# Database Module
# =============================================================================

module "database" {
  source = "./modules/database"

  cloud_provider      = var.cloud_provider
  environment         = var.environment
  name_prefix         = local.name_prefix
  tags                = local.common_tags

  # Azure
  azure_location      = var.azure_location
  resource_group_name = var.cloud_provider == "azure" ? azurerm_resource_group.main[0].name : ""

  # AWS
  aws_region          = var.aws_region

  # GCP
  gcp_project_id      = var.gcp_project_id
  gcp_region          = var.gcp_region

  # Database configuration
  db_name             = var.db_name
  db_username         = var.db_username
  db_sku              = local.current_sizing.db_sku
  db_storage_mb       = var.db_storage_mb
  db_backup_retention = var.db_backup_retention

  # Networking
  subnet_id           = module.networking.database_subnet_id
  private_dns_zone_id = module.networking.private_dns_zone_id

  # Encryption
  key_vault_key_id    = module.keyvault.database_encryption_key_id

  # High availability
  enable_ha           = var.environment == "prod"
  enable_read_replica = var.environment == "prod"

  depends_on = [module.networking, module.keyvault]
}

# =============================================================================
# Storage Module
# =============================================================================

module "storage" {
  source = "./modules/storage"

  cloud_provider      = var.cloud_provider
  environment         = var.environment
  name_prefix         = local.name_prefix
  tags                = local.common_tags

  # Azure
  azure_location      = var.azure_location
  resource_group_name = var.cloud_provider == "azure" ? azurerm_resource_group.main[0].name : ""

  # AWS
  aws_region          = var.aws_region

  # GCP
  gcp_project_id      = var.gcp_project_id
  gcp_region          = var.gcp_region

  # Storage configuration
  enable_versioning   = var.environment != "dev"
  enable_immutability = var.environment == "prod"
  retention_days      = var.storage_retention_days

  # Encryption
  key_vault_key_id    = module.keyvault.storage_encryption_key_id

  depends_on = [module.keyvault]
}

# =============================================================================
# Compute Module (Kubernetes/VMs)
# =============================================================================

module "compute" {
  source = "./modules/compute"

  cloud_provider      = var.cloud_provider
  environment         = var.environment
  name_prefix         = local.name_prefix
  tags                = local.common_tags

  # Azure
  azure_location      = var.azure_location
  resource_group_name = var.cloud_provider == "azure" ? azurerm_resource_group.main[0].name : ""

  # AWS
  aws_region          = var.aws_region

  # GCP
  gcp_project_id      = var.gcp_project_id
  gcp_region          = var.gcp_region

  # Compute configuration
  deployment_type     = var.deployment_type  # "kubernetes" or "vm"
  vm_size             = local.current_sizing.vm_size
  node_count          = local.current_sizing.node_count
  min_node_count      = local.current_sizing.min_node_count
  max_node_count      = local.current_sizing.max_node_count

  # Networking
  subnet_id           = module.networking.compute_subnet_id
  bastion_subnet_id   = module.networking.bastion_subnet_id

  # SSH access
  ssh_public_key      = var.ssh_public_key
  admin_username      = var.admin_username

  depends_on = [module.networking]
}

# =============================================================================
# Monitoring Module
# =============================================================================

module "monitoring" {
  source = "./modules/monitoring"

  cloud_provider      = var.cloud_provider
  environment         = var.environment
  name_prefix         = local.name_prefix
  tags                = local.common_tags

  # Azure
  azure_location      = var.azure_location
  resource_group_name = var.cloud_provider == "azure" ? azurerm_resource_group.main[0].name : ""

  # AWS
  aws_region          = var.aws_region

  # GCP
  gcp_project_id      = var.gcp_project_id

  # Monitoring configuration
  log_retention_days  = var.log_retention_days
  enable_alerts       = var.enable_alerts
  alert_email         = var.alert_email

  # Resources to monitor
  database_id         = module.database.database_id
  storage_id          = module.storage.storage_id
  compute_id          = module.compute.compute_id

  depends_on = [module.database, module.storage, module.compute]
}

# =============================================================================
# Outputs
# =============================================================================

output "resource_group_name" {
  description = "Name of the resource group"
  value       = var.cloud_provider == "azure" ? azurerm_resource_group.main[0].name : null
}

output "database_connection_string" {
  description = "Database connection string"
  value       = module.database.connection_string
  sensitive   = true
}

output "database_host" {
  description = "Database host"
  value       = module.database.host
}

output "storage_endpoint" {
  description = "Storage endpoint URL"
  value       = module.storage.endpoint
}

output "storage_bucket_name" {
  description = "Storage bucket/container name"
  value       = module.storage.bucket_name
}

output "keyvault_uri" {
  description = "Key Vault URI"
  value       = module.keyvault.vault_uri
}

output "kubernetes_cluster_name" {
  description = "Kubernetes cluster name"
  value       = var.deployment_type == "kubernetes" ? module.compute.kubernetes_cluster_name : null
}

output "kubernetes_config" {
  description = "Kubernetes config for kubectl"
  value       = var.deployment_type == "kubernetes" ? module.compute.kubernetes_config : null
  sensitive   = true
}

output "bastion_public_ip" {
  description = "Bastion host public IP"
  value       = module.compute.bastion_public_ip
}

output "monitoring_workspace_id" {
  description = "Monitoring workspace ID"
  value       = module.monitoring.workspace_id
}
