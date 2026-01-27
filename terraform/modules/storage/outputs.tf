# =============================================================================
# Storage Module - Outputs
# =============================================================================

output "storage_id" {
  description = "Storage account/bucket ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_storage_account.main) > 0 ? azurerm_storage_account.main[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_s3_bucket.main) > 0 ? aws_s3_bucket.main[0].id : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_storage_bucket.main) > 0 ? google_storage_bucket.main[0].id : null
  ) : null
}

output "bucket_name" {
  description = "Storage bucket/container name"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_storage_account.main) > 0 ? azurerm_storage_account.main[0].name : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_s3_bucket.main) > 0 ? aws_s3_bucket.main[0].bucket : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_storage_bucket.main) > 0 ? google_storage_bucket.main[0].name : null
  ) : null
}

output "endpoint" {
  description = "Storage endpoint URL"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_storage_account.main) > 0 ? azurerm_storage_account.main[0].primary_blob_endpoint : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_s3_bucket.main) > 0 ? "https://${aws_s3_bucket.main[0].bucket_regional_domain_name}" : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_storage_bucket.main) > 0 ? "https://storage.googleapis.com/${google_storage_bucket.main[0].name}" : null
  ) : null
}

output "connection_string" {
  description = "Storage connection string (Azure only)"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_storage_account.main) > 0 ? azurerm_storage_account.main[0].primary_connection_string : null
  ) : null
  sensitive = true
}

output "access_key" {
  description = "Storage access key"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_storage_account.main) > 0 ? azurerm_storage_account.main[0].primary_access_key : null
  ) : null
  sensitive = true
}
