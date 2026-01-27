# =============================================================================
# Key Vault / Secrets Module - Multi-Cloud
# =============================================================================
# Creates secret management infrastructure with:
# - Azure Key Vault / AWS Secrets Manager / GCP Secret Manager
# - Encryption keys for databases and storage
# - Access policies
# =============================================================================

terraform {
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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# Random suffix for globally unique names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# =============================================================================
# Azure Key Vault
# =============================================================================

data "azurerm_client_config" "current" {
  count = var.cloud_provider == "azure" ? 1 : 0
}

resource "azurerm_key_vault" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${replace(var.name_prefix, "-", "")}kv${random_string.suffix.result}"
  location            = var.azure_location
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current[0].tenant_id
  sku_name            = "premium"

  enabled_for_deployment          = true
  enabled_for_disk_encryption     = true
  enabled_for_template_deployment = true
  enable_rbac_authorization       = false
  purge_protection_enabled        = true
  soft_delete_retention_days      = 90

  network_acls {
    bypass         = "AzureServices"
    default_action = "Allow"  # Change to "Deny" with private endpoints
  }

  tags = var.tags
}

# Access policy for Terraform user
resource "azurerm_key_vault_access_policy" "terraform" {
  count        = var.cloud_provider == "azure" ? 1 : 0
  key_vault_id = azurerm_key_vault.main[0].id
  tenant_id    = data.azurerm_client_config.current[0].tenant_id
  object_id    = data.azurerm_client_config.current[0].object_id

  key_permissions = [
    "Create", "Delete", "Get", "GetRotationPolicy", "List", "Purge",
    "Recover", "SetRotationPolicy", "Update", "Verify", "WrapKey", "UnwrapKey",
  ]

  secret_permissions = [
    "Backup", "Delete", "Get", "List", "Purge", "Recover", "Restore", "Set",
  ]

  certificate_permissions = [
    "Create", "Delete", "Get", "List", "Purge", "Recover", "Update",
  ]
}

# Access policies for admins
resource "azurerm_key_vault_access_policy" "admins" {
  count        = var.cloud_provider == "azure" ? length(var.admin_object_ids) : 0
  key_vault_id = azurerm_key_vault.main[0].id
  tenant_id    = data.azurerm_client_config.current[0].tenant_id
  object_id    = var.admin_object_ids[count.index]

  key_permissions = [
    "Create", "Delete", "Get", "List", "Update", "Verify", "WrapKey", "UnwrapKey",
  ]

  secret_permissions = [
    "Delete", "Get", "List", "Set",
  ]

  certificate_permissions = [
    "Create", "Delete", "Get", "List", "Update",
  ]
}

# Database encryption key
resource "azurerm_key_vault_key" "database" {
  count        = var.cloud_provider == "azure" ? 1 : 0
  name         = "${var.name_prefix}-db-key"
  key_vault_id = azurerm_key_vault.main[0].id
  key_type     = "RSA"
  key_size     = 2048

  key_opts = [
    "decrypt", "encrypt", "sign", "unwrapKey", "verify", "wrapKey",
  ]

  rotation_policy {
    automatic {
      time_before_expiry = "P30D"
    }
    expire_after         = "P90D"
    notify_before_expiry = "P29D"
  }

  depends_on = [azurerm_key_vault_access_policy.terraform]
}

# Storage encryption key
resource "azurerm_key_vault_key" "storage" {
  count        = var.cloud_provider == "azure" ? 1 : 0
  name         = "${var.name_prefix}-storage-key"
  key_vault_id = azurerm_key_vault.main[0].id
  key_type     = "RSA"
  key_size     = 2048

  key_opts = [
    "decrypt", "encrypt", "sign", "unwrapKey", "verify", "wrapKey",
  ]

  rotation_policy {
    automatic {
      time_before_expiry = "P30D"
    }
    expire_after         = "P90D"
    notify_before_expiry = "P29D"
  }

  depends_on = [azurerm_key_vault_access_policy.terraform]
}

# =============================================================================
# AWS Secrets Manager & KMS
# =============================================================================

# KMS Key for database encryption
resource "aws_kms_key" "database" {
  count                   = var.cloud_provider == "aws" ? 1 : 0
  description             = "${var.name_prefix} Database Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = false

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current[0].account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow RDS Service"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_kms_alias" "database" {
  count         = var.cloud_provider == "aws" ? 1 : 0
  name          = "alias/${var.name_prefix}-db-key"
  target_key_id = aws_kms_key.database[0].key_id
}

# KMS Key for storage encryption
resource "aws_kms_key" "storage" {
  count                   = var.cloud_provider == "aws" ? 1 : 0
  description             = "${var.name_prefix} Storage Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = false

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current[0].account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow S3 Service"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_kms_alias" "storage" {
  count         = var.cloud_provider == "aws" ? 1 : 0
  name          = "alias/${var.name_prefix}-storage-key"
  target_key_id = aws_kms_key.storage[0].key_id
}

# Secrets Manager for application secrets
resource "aws_secretsmanager_secret" "app" {
  count                   = var.cloud_provider == "aws" ? 1 : 0
  name                    = "${var.name_prefix}/app-secrets"
  description             = "Application secrets for ${var.name_prefix}"
  recovery_window_in_days = 30
  kms_key_id              = aws_kms_key.database[0].arn

  tags = var.tags
}

data "aws_caller_identity" "current" {
  count = var.cloud_provider == "aws" ? 1 : 0
}

# =============================================================================
# GCP Secret Manager & KMS
# =============================================================================

# KMS Keyring
resource "google_kms_key_ring" "main" {
  count    = var.cloud_provider == "gcp" ? 1 : 0
  name     = "${var.name_prefix}-keyring"
  project  = var.gcp_project_id
  location = "global"
}

# Database encryption key
resource "google_kms_crypto_key" "database" {
  count           = var.cloud_provider == "gcp" ? 1 : 0
  name            = "${var.name_prefix}-db-key"
  key_ring        = google_kms_key_ring.main[0].id
  rotation_period = "7776000s"  # 90 days
  purpose         = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }
}

# Storage encryption key
resource "google_kms_crypto_key" "storage" {
  count           = var.cloud_provider == "gcp" ? 1 : 0
  name            = "${var.name_prefix}-storage-key"
  key_ring        = google_kms_key_ring.main[0].id
  rotation_period = "7776000s"  # 90 days
  purpose         = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }
}

# Secret Manager secret for application
resource "google_secret_manager_secret" "app" {
  count     = var.cloud_provider == "gcp" ? 1 : 0
  secret_id = "${var.name_prefix}-app-secrets"
  project   = var.gcp_project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
  }
}
