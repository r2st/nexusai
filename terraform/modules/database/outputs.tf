# =============================================================================
# Database Module - Outputs
# =============================================================================

output "database_id" {
  description = "Database server ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_postgresql_flexible_server.main) > 0 ? azurerm_postgresql_flexible_server.main[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_db_instance.main) > 0 ? aws_db_instance.main[0].id : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_sql_database_instance.main) > 0 ? google_sql_database_instance.main[0].id : null
  ) : null
}

output "host" {
  description = "Database hostname"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_postgresql_flexible_server.main) > 0 ? azurerm_postgresql_flexible_server.main[0].fqdn : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_db_instance.main) > 0 ? aws_db_instance.main[0].address : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_sql_database_instance.main) > 0 ? google_sql_database_instance.main[0].private_ip_address : null
  ) : null
}

output "replica_host" {
  description = "Read replica hostname"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_postgresql_flexible_server.replica) > 0 ? azurerm_postgresql_flexible_server.replica[0].fqdn : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_db_instance.replica) > 0 ? aws_db_instance.replica[0].address : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_sql_database_instance.replica) > 0 ? google_sql_database_instance.replica[0].private_ip_address : null
  ) : null
}

output "port" {
  description = "Database port"
  value       = 5432
}

output "database_name" {
  description = "Database name"
  value       = var.db_name
}

output "username" {
  description = "Database username"
  value       = var.db_username
}

output "password" {
  description = "Database password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "connection_string" {
  description = "Full connection string"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_postgresql_flexible_server.main) > 0 ?
    "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${azurerm_postgresql_flexible_server.main[0].fqdn}:5432/${var.db_name}" : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_db_instance.main) > 0 ?
    "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.main[0].address}:5432/${var.db_name}" : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_sql_database_instance.main) > 0 ?
    "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${google_sql_database_instance.main[0].private_ip_address}:5432/${var.db_name}" : null
  ) : null
  sensitive = true
}

output "read_replica_connection_string" {
  description = "Read replica connection string"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_postgresql_flexible_server.replica) > 0 ?
    "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${azurerm_postgresql_flexible_server.replica[0].fqdn}:5432/${var.db_name}" : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_db_instance.replica) > 0 ?
    "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.replica[0].address}:5432/${var.db_name}" : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_sql_database_instance.replica) > 0 ?
    "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${google_sql_database_instance.replica[0].private_ip_address}:5432/${var.db_name}" : null
  ) : null
  sensitive = true
}
