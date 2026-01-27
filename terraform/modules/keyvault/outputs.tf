# =============================================================================
# Key Vault Module - Outputs
# =============================================================================

output "vault_id" {
  description = "Key Vault / Secrets Manager ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_key_vault.main) > 0 ? azurerm_key_vault.main[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_secretsmanager_secret.app) > 0 ? aws_secretsmanager_secret.app[0].arn : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_secret_manager_secret.app) > 0 ? google_secret_manager_secret.app[0].id : null
  ) : null
}

output "vault_uri" {
  description = "Key Vault URI"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_key_vault.main) > 0 ? azurerm_key_vault.main[0].vault_uri : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_secretsmanager_secret.app) > 0 ? aws_secretsmanager_secret.app[0].arn : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_secret_manager_secret.app) > 0 ? google_secret_manager_secret.app[0].name : null
  ) : null
}

output "database_encryption_key_id" {
  description = "Database encryption key ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_key_vault_key.database) > 0 ? azurerm_key_vault_key.database[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_kms_key.database) > 0 ? aws_kms_key.database[0].arn : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_kms_crypto_key.database) > 0 ? google_kms_crypto_key.database[0].id : null
  ) : null
}

output "storage_encryption_key_id" {
  description = "Storage encryption key ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_key_vault_key.storage) > 0 ? azurerm_key_vault_key.storage[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_kms_key.storage) > 0 ? aws_kms_key.storage[0].arn : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_kms_crypto_key.storage) > 0 ? google_kms_crypto_key.storage[0].id : null
  ) : null
}

output "vault_name" {
  description = "Key Vault name"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_key_vault.main) > 0 ? azurerm_key_vault.main[0].name : null
  ) : null
}
