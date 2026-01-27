# =============================================================================
# Database Module - Multi-Cloud PostgreSQL
# =============================================================================
# Creates managed PostgreSQL with:
# - Private network access
# - Customer-managed key encryption
# - Automated backups
# - High availability (optional)
# - Read replicas (optional)
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

# Generate random password
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# =============================================================================
# Azure PostgreSQL Flexible Server
# =============================================================================

resource "azurerm_postgresql_flexible_server" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.name_prefix}-psql"
  resource_group_name = var.resource_group_name
  location            = var.azure_location
  version             = "15"
  delegated_subnet_id = var.subnet_id
  private_dns_zone_id = var.private_dns_zone_id

  administrator_login    = var.db_username
  administrator_password = random_password.db_password.result

  sku_name   = var.db_sku
  storage_mb = var.db_storage_mb

  backup_retention_days        = var.db_backup_retention
  geo_redundant_backup_enabled = var.environment == "prod"

  # High Availability
  dynamic "high_availability" {
    for_each = var.enable_ha ? [1] : []
    content {
      mode                      = "ZoneRedundant"
      standby_availability_zone = "2"
    }
  }

  # Customer-Managed Key Encryption (if key_vault_key_id provided)
  dynamic "customer_managed_key" {
    for_each = var.key_vault_key_id != null && var.key_vault_key_id != "" ? [1] : []
    content {
      key_vault_key_id                  = var.key_vault_key_id
      primary_user_assigned_identity_id = azurerm_user_assigned_identity.db_encryption[0].id
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = var.key_vault_key_id != null && var.key_vault_key_id != "" ? [azurerm_user_assigned_identity.db_encryption[0].id] : []
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [
      zone,
      high_availability[0].standby_availability_zone,
    ]
  }
}

# User-assigned identity for CMK encryption
resource "azurerm_user_assigned_identity" "db_encryption" {
  count               = var.cloud_provider == "azure" && var.key_vault_key_id != null && var.key_vault_key_id != "" ? 1 : 0
  name                = "${var.name_prefix}-db-identity"
  resource_group_name = var.resource_group_name
  location            = var.azure_location
  tags                = var.tags
}

# Database
resource "azurerm_postgresql_flexible_server_database" "main" {
  count     = var.cloud_provider == "azure" ? 1 : 0
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.main[0].id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

# PostgreSQL extensions
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  count     = var.cloud_provider == "azure" ? 1 : 0
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main[0].id
  value     = "VECTOR,PG_TRGM,BTREE_GIN,UUID-OSSP,PGCRYPTO"
}

# Performance tuning
resource "azurerm_postgresql_flexible_server_configuration" "shared_buffers" {
  count     = var.cloud_provider == "azure" ? 1 : 0
  name      = "shared_buffers"
  server_id = azurerm_postgresql_flexible_server.main[0].id
  value     = "262144"  # 256MB
}

resource "azurerm_postgresql_flexible_server_configuration" "work_mem" {
  count     = var.cloud_provider == "azure" ? 1 : 0
  name      = "work_mem"
  server_id = azurerm_postgresql_flexible_server.main[0].id
  value     = "65536"  # 64MB
}

# Read Replica
resource "azurerm_postgresql_flexible_server" "replica" {
  count               = var.cloud_provider == "azure" && var.enable_read_replica ? 1 : 0
  name                = "${var.name_prefix}-psql-replica"
  resource_group_name = var.resource_group_name
  location            = var.azure_location
  version             = "15"
  delegated_subnet_id = var.subnet_id
  private_dns_zone_id = var.private_dns_zone_id

  create_mode      = "Replica"
  source_server_id = azurerm_postgresql_flexible_server.main[0].id

  sku_name   = var.db_sku
  storage_mb = var.db_storage_mb

  tags = var.tags
}

# =============================================================================
# AWS RDS PostgreSQL
# =============================================================================

resource "aws_db_instance" "main" {
  count               = var.cloud_provider == "aws" ? 1 : 0
  identifier          = "${var.name_prefix}-psql"
  engine              = "postgres"
  engine_version      = "15.4"
  instance_class      = var.db_sku
  allocated_storage   = var.db_storage_mb / 1024  # Convert MB to GB
  storage_type        = "gp3"
  storage_encrypted   = true
  kms_key_id          = var.key_vault_key_id

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  vpc_security_group_ids = [var.security_group_id]
  db_subnet_group_name   = var.db_subnet_group_name

  backup_retention_period = var.db_backup_retention
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  multi_az               = var.enable_ha
  publicly_accessible    = false
  deletion_protection    = var.environment == "prod"
  skip_final_snapshot    = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${var.name_prefix}-final-snapshot" : null

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  tags = var.tags
}

# Read Replica (AWS)
resource "aws_db_instance" "replica" {
  count               = var.cloud_provider == "aws" && var.enable_read_replica ? 1 : 0
  identifier          = "${var.name_prefix}-psql-replica"
  replicate_source_db = aws_db_instance.main[0].identifier
  instance_class      = var.db_sku
  storage_encrypted   = true
  kms_key_id          = var.key_vault_key_id

  vpc_security_group_ids = [var.security_group_id]

  publicly_accessible = false
  skip_final_snapshot = true

  tags = var.tags
}

# =============================================================================
# GCP Cloud SQL PostgreSQL
# =============================================================================

resource "google_sql_database_instance" "main" {
  count            = var.cloud_provider == "gcp" ? 1 : 0
  name             = "${var.name_prefix}-psql"
  project          = var.gcp_project_id
  region           = var.gcp_region
  database_version = "POSTGRES_15"

  deletion_protection = var.environment == "prod"

  settings {
    tier              = var.db_sku
    availability_type = var.enable_ha ? "REGIONAL" : "ZONAL"
    disk_size         = var.db_storage_mb / 1024
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = var.db_backup_retention
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.subnet_id
      require_ssl     = true
    }

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    maintenance_window {
      day          = 1  # Monday
      hour         = 4
      update_track = "stable"
    }
  }
}

resource "google_sql_database" "main" {
  count    = var.cloud_provider == "gcp" ? 1 : 0
  name     = var.db_name
  project  = var.gcp_project_id
  instance = google_sql_database_instance.main[0].name
}

resource "google_sql_user" "main" {
  count    = var.cloud_provider == "gcp" ? 1 : 0
  name     = var.db_username
  project  = var.gcp_project_id
  instance = google_sql_database_instance.main[0].name
  password = random_password.db_password.result
}

# Read Replica (GCP)
resource "google_sql_database_instance" "replica" {
  count                = var.cloud_provider == "gcp" && var.enable_read_replica ? 1 : 0
  name                 = "${var.name_prefix}-psql-replica"
  project              = var.gcp_project_id
  region               = var.gcp_region
  database_version     = "POSTGRES_15"
  master_instance_name = google_sql_database_instance.main[0].name

  replica_configuration {
    failover_target = false
  }

  settings {
    tier            = var.db_sku
    disk_autoresize = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.subnet_id
      require_ssl     = true
    }
  }
}
