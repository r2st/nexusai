# =============================================================================
# Networking Module - Outputs
# =============================================================================

output "vnet_id" {
  description = "Virtual network ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_virtual_network.main) > 0 ? azurerm_virtual_network.main[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_vpc.main) > 0 ? aws_vpc.main[0].id : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_compute_network.main) > 0 ? google_compute_network.main[0].id : null
  ) : null
}

output "compute_subnet_id" {
  description = "Compute/Application subnet ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_subnet.app) > 0 ? azurerm_subnet.app[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_subnet.app) > 0 ? aws_subnet.app[0].id : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_compute_subnetwork.app) > 0 ? google_compute_subnetwork.app[0].id : null
  ) : null
}

output "database_subnet_id" {
  description = "Database subnet ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_subnet.database) > 0 ? azurerm_subnet.database[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_subnet.database) > 0 ? aws_subnet.database[0].id : null
  ) : var.cloud_provider == "gcp" ? (
    length(google_compute_subnetwork.database) > 0 ? google_compute_subnetwork.database[0].id : null
  ) : null
}

output "bastion_subnet_id" {
  description = "Bastion subnet ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_subnet.bastion) > 0 ? azurerm_subnet.bastion[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_subnet.public) > 0 ? aws_subnet.public[0].id : null
  ) : null
}

output "private_dns_zone_id" {
  description = "Private DNS zone ID for PostgreSQL"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_private_dns_zone.postgresql) > 0 ? azurerm_private_dns_zone.postgresql[0].id : null
  ) : null
}

output "app_security_group_id" {
  description = "Application security group ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_network_security_group.app) > 0 ? azurerm_network_security_group.app[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_security_group.app) > 0 ? aws_security_group.app[0].id : null
  ) : null
}

output "database_security_group_id" {
  description = "Database security group ID"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_network_security_group.database) > 0 ? azurerm_network_security_group.database[0].id : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_security_group.database) > 0 ? aws_security_group.database[0].id : null
  ) : null
}

output "db_subnet_group_name" {
  description = "AWS RDS subnet group name"
  value = var.cloud_provider == "aws" ? (
    length(aws_db_subnet_group.main) > 0 ? aws_db_subnet_group.main[0].name : null
  ) : null
}

output "nat_gateway_ip" {
  description = "NAT Gateway public IP"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_public_ip.nat) > 0 ? azurerm_public_ip.nat[0].ip_address : null
  ) : var.cloud_provider == "aws" ? (
    length(aws_eip.nat) > 0 ? aws_eip.nat[0].public_ip : null
  ) : null
}
