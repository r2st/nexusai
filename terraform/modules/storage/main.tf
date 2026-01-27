# =============================================================================
# Storage Module - Multi-Cloud Object Storage
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

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# =============================================================================
# Azure Blob Storage
# =============================================================================

resource "azurerm_storage_account" "main" {
  count                    = var.cloud_provider == "azure" ? 1 : 0
  name                     = "${replace(var.name_prefix, "-", "")}${random_string.suffix.result}"
  resource_group_name      = var.resource_group_name
  location                 = var.azure_location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"
  access_tier              = "Hot"

  min_tls_version                 = "TLS1_2"
  enable_https_traffic_only       = true
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = true

  blob_properties {
    versioning_enabled = var.enable_versioning

    dynamic "delete_retention_policy" {
      for_each = var.enable_versioning ? [1] : []
      content {
        days = var.retention_days
      }
    }

    dynamic "container_delete_retention_policy" {
      for_each = var.enable_versioning ? [1] : []
      content {
        days = var.retention_days
      }
    }
  }

  # Customer-managed key encryption
  dynamic "customer_managed_key" {
    for_each = var.key_vault_key_id != null && var.key_vault_key_id != "" ? [1] : []
    content {
      key_vault_key_id          = var.key_vault_key_id
      user_assigned_identity_id = azurerm_user_assigned_identity.storage[0].id
    }
  }

  dynamic "identity" {
    for_each = var.key_vault_key_id != null && var.key_vault_key_id != "" ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.storage[0].id]
    }
  }

  tags = var.tags
}

resource "azurerm_user_assigned_identity" "storage" {
  count               = var.cloud_provider == "azure" && var.key_vault_key_id != null && var.key_vault_key_id != "" ? 1 : 0
  name                = "${var.name_prefix}-storage-identity"
  resource_group_name = var.resource_group_name
  location            = var.azure_location
  tags                = var.tags
}

# Containers
resource "azurerm_storage_container" "uploads" {
  count                 = var.cloud_provider == "azure" ? 1 : 0
  name                  = "uploads"
  storage_account_name  = azurerm_storage_account.main[0].name
  container_access_type = "private"
}

resource "azurerm_storage_container" "exports" {
  count                 = var.cloud_provider == "azure" ? 1 : 0
  name                  = "exports"
  storage_account_name  = azurerm_storage_account.main[0].name
  container_access_type = "private"
}

resource "azurerm_storage_container" "backups" {
  count                 = var.cloud_provider == "azure" ? 1 : 0
  name                  = "backups"
  storage_account_name  = azurerm_storage_account.main[0].name
  container_access_type = "private"
}

# Immutability policy for compliance
resource "azurerm_storage_management_policy" "main" {
  count              = var.cloud_provider == "azure" ? 1 : 0
  storage_account_id = azurerm_storage_account.main[0].id

  rule {
    name    = "cleanup-old-versions"
    enabled = true

    filters {
      blob_types = ["blockBlob"]
    }

    actions {
      version {
        delete_after_days_since_creation = var.retention_days
      }
    }
  }
}

# =============================================================================
# AWS S3
# =============================================================================

resource "aws_s3_bucket" "main" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  bucket = "${var.name_prefix}-${random_string.suffix.result}"

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "main" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  bucket = aws_s3_bucket.main[0].id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  bucket = aws_s3_bucket.main[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.key_vault_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.key_vault_key_id
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "main" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  bucket = aws_s3_bucket.main[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "main" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  bucket = aws_s3_bucket.main[0].id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = var.retention_days
    }
  }

  rule {
    id     = "archive-old-files"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    filter {
      prefix = "backups/"
    }
  }
}

# Object Lock for immutability (production only)
resource "aws_s3_bucket_object_lock_configuration" "main" {
  count  = var.cloud_provider == "aws" && var.enable_immutability ? 1 : 0
  bucket = aws_s3_bucket.main[0].id

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = var.retention_days
    }
  }
}

# =============================================================================
# GCP Cloud Storage
# =============================================================================

resource "google_storage_bucket" "main" {
  count         = var.cloud_provider == "gcp" ? 1 : 0
  name          = "${var.name_prefix}-${random_string.suffix.result}"
  project       = var.gcp_project_id
  location      = var.gcp_region
  storage_class = "STANDARD"
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = var.enable_versioning
  }

  dynamic "encryption" {
    for_each = var.key_vault_key_id != null && var.key_vault_key_id != "" ? [1] : []
    content {
      default_kms_key_name = var.key_vault_key_id
    }
  }

  lifecycle_rule {
    condition {
      age = var.retention_days
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  labels = {
    environment = var.environment
  }
}
