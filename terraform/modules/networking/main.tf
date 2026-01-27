# =============================================================================
# Networking Module - Multi-Cloud Support
# =============================================================================
# Creates VNet/VPC, subnets, NSGs, NAT gateways, and private DNS zones
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
  }
}

# =============================================================================
# Azure Networking
# =============================================================================

# Virtual Network
resource "azurerm_virtual_network" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.name_prefix}-vnet"
  address_space       = [var.vnet_cidr]
  location            = var.azure_location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Application Subnet
resource "azurerm_subnet" "app" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "${var.name_prefix}-app-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = [var.subnet_cidrs.app]

  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.Sql",
  ]
}

# Database Subnet
resource "azurerm_subnet" "database" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "${var.name_prefix}-db-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = [var.subnet_cidrs.database]

  delegation {
    name = "postgresql-delegation"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Bastion Subnet
resource "azurerm_subnet" "bastion" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "AzureBastionSubnet"  # Must be this exact name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = [var.subnet_cidrs.bastion]
}

# Private Endpoints Subnet
resource "azurerm_subnet" "private_endpoints" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "${var.name_prefix}-pe-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = [var.subnet_cidrs.private_endpoints]

  private_endpoint_network_policies_enabled = true
}

# Network Security Group - Application
resource "azurerm_network_security_group" "app" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.name_prefix}-app-nsg"
  location            = var.azure_location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Allow HTTPS inbound
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow HTTP inbound (for Let's Encrypt)
  security_rule {
    name                       = "AllowHTTP"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow internal traffic
  security_rule {
    name                       = "AllowVNetInternal"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# Network Security Group - Database
resource "azurerm_network_security_group" "database" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.name_prefix}-db-nsg"
  location            = var.azure_location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Allow PostgreSQL from app subnet only
  security_rule {
    name                       = "AllowPostgreSQLFromApp"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = var.subnet_cidrs.app
    destination_address_prefix = "*"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# Associate NSGs with subnets
resource "azurerm_subnet_network_security_group_association" "app" {
  count                     = var.cloud_provider == "azure" ? 1 : 0
  subnet_id                 = azurerm_subnet.app[0].id
  network_security_group_id = azurerm_network_security_group.app[0].id
}

resource "azurerm_subnet_network_security_group_association" "database" {
  count                     = var.cloud_provider == "azure" ? 1 : 0
  subnet_id                 = azurerm_subnet.database[0].id
  network_security_group_id = azurerm_network_security_group.database[0].id
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgresql" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Link DNS Zone to VNet
resource "azurerm_private_dns_zone_virtual_network_link" "postgresql" {
  count                 = var.cloud_provider == "azure" ? 1 : 0
  name                  = "${var.name_prefix}-postgresql-dns-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.postgresql[0].name
  virtual_network_id    = azurerm_virtual_network.main[0].id
  registration_enabled  = false
  tags                  = var.tags
}

# NAT Gateway for outbound internet access
resource "azurerm_public_ip" "nat" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.name_prefix}-nat-pip"
  location            = var.azure_location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_nat_gateway" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.name_prefix}-nat-gw"
  location            = var.azure_location
  resource_group_name = var.resource_group_name
  sku_name            = "Standard"
  tags                = var.tags
}

resource "azurerm_nat_gateway_public_ip_association" "main" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  nat_gateway_id       = azurerm_nat_gateway.main[0].id
  public_ip_address_id = azurerm_public_ip.nat[0].id
}

resource "azurerm_subnet_nat_gateway_association" "app" {
  count          = var.cloud_provider == "azure" ? 1 : 0
  subnet_id      = azurerm_subnet.app[0].id
  nat_gateway_id = azurerm_nat_gateway.main[0].id
}

# =============================================================================
# AWS Networking
# =============================================================================

# VPC
resource "aws_vpc" "main" {
  count                = var.cloud_provider == "aws" ? 1 : 0
  cidr_block           = var.vnet_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  vpc_id = aws_vpc.main[0].id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-igw"
  })
}

# Public Subnet (for NAT Gateway)
resource "aws_subnet" "public" {
  count                   = var.cloud_provider == "aws" ? 1 : 0
  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = var.subnet_cidrs.bastion
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-subnet"
  })
}

# App Subnet
resource "aws_subnet" "app" {
  count             = var.cloud_provider == "aws" ? 1 : 0
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = var.subnet_cidrs.app
  availability_zone = "${var.aws_region}a"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-app-subnet"
  })
}

# Database Subnet
resource "aws_subnet" "database" {
  count             = var.cloud_provider == "aws" ? 1 : 0
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = var.subnet_cidrs.database
  availability_zone = "${var.aws_region}a"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-subnet"
  })
}

# Database Subnet (second AZ for RDS)
resource "aws_subnet" "database_b" {
  count             = var.cloud_provider == "aws" ? 1 : 0
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = cidrsubnet(var.vnet_cidr, 8, 5)  # Additional subnet
  availability_zone = "${var.aws_region}b"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-subnet-b"
  })
}

# NAT Gateway
resource "aws_eip" "nat" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-nat-eip"
  })
}

resource "aws_nat_gateway" "main" {
  count         = var.cloud_provider == "aws" ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-nat-gw"
  })
}

# Route Tables
resource "aws_route_table" "public" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-rt"
  })
}

resource "aws_route_table" "private" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[0].id
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-private-rt"
  })
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = var.cloud_provider == "aws" ? 1 : 0
  subnet_id      = aws_subnet.public[0].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table_association" "app" {
  count          = var.cloud_provider == "aws" ? 1 : 0
  subnet_id      = aws_subnet.app[0].id
  route_table_id = aws_route_table.private[0].id
}

resource "aws_route_table_association" "database" {
  count          = var.cloud_provider == "aws" ? 1 : 0
  subnet_id      = aws_subnet.database[0].id
  route_table_id = aws_route_table.private[0].id
}

# Security Groups
resource "aws_security_group" "app" {
  count       = var.cloud_provider == "aws" ? 1 : 0
  name        = "${var.name_prefix}-app-sg"
  description = "Security group for application"
  vpc_id      = aws_vpc.main[0].id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-app-sg"
  })
}

resource "aws_security_group" "database" {
  count       = var.cloud_provider == "aws" ? 1 : 0
  name        = "${var.name_prefix}-db-sg"
  description = "Security group for database"
  vpc_id      = aws_vpc.main[0].id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app[0].id]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-sg"
  })
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  count      = var.cloud_provider == "aws" ? 1 : 0
  name       = "${var.name_prefix}-db-subnet-group"
  subnet_ids = [aws_subnet.database[0].id, aws_subnet.database_b[0].id]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-subnet-group"
  })
}

# =============================================================================
# GCP Networking
# =============================================================================

# VPC Network
resource "google_compute_network" "main" {
  count                   = var.cloud_provider == "gcp" ? 1 : 0
  name                    = "${var.name_prefix}-vpc"
  project                 = var.gcp_project_id
  auto_create_subnetworks = false
}

# Subnets
resource "google_compute_subnetwork" "app" {
  count         = var.cloud_provider == "gcp" ? 1 : 0
  name          = "${var.name_prefix}-app-subnet"
  project       = var.gcp_project_id
  region        = var.gcp_region
  network       = google_compute_network.main[0].id
  ip_cidr_range = var.subnet_cidrs.app

  private_ip_google_access = true
}

resource "google_compute_subnetwork" "database" {
  count         = var.cloud_provider == "gcp" ? 1 : 0
  name          = "${var.name_prefix}-db-subnet"
  project       = var.gcp_project_id
  region        = var.gcp_region
  network       = google_compute_network.main[0].id
  ip_cidr_range = var.subnet_cidrs.database

  private_ip_google_access = true
}

# Cloud NAT
resource "google_compute_router" "main" {
  count   = var.cloud_provider == "gcp" ? 1 : 0
  name    = "${var.name_prefix}-router"
  project = var.gcp_project_id
  region  = var.gcp_region
  network = google_compute_network.main[0].id
}

resource "google_compute_router_nat" "main" {
  count                              = var.cloud_provider == "gcp" ? 1 : 0
  name                               = "${var.name_prefix}-nat"
  project                            = var.gcp_project_id
  router                             = google_compute_router.main[0].name
  region                             = var.gcp_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Firewall Rules
resource "google_compute_firewall" "allow_http_https" {
  count   = var.cloud_provider == "gcp" ? 1 : 0
  name    = "${var.name_prefix}-allow-http-https"
  project = var.gcp_project_id
  network = google_compute_network.main[0].name

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["web"]
}

resource "google_compute_firewall" "allow_internal" {
  count   = var.cloud_provider == "gcp" ? 1 : 0
  name    = "${var.name_prefix}-allow-internal"
  project = var.gcp_project_id
  network = google_compute_network.main[0].name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.vnet_cidr]
}

# Private Service Access for Cloud SQL
resource "google_compute_global_address" "private_ip" {
  count         = var.cloud_provider == "gcp" ? 1 : 0
  name          = "${var.name_prefix}-private-ip"
  project       = var.gcp_project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main[0].id
}

resource "google_service_networking_connection" "private_vpc" {
  count                   = var.cloud_provider == "gcp" ? 1 : 0
  network                 = google_compute_network.main[0].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip[0].name]
}
