# =============================================================================
# OpenBao (Vault) Server Configuration
# =============================================================================

# Storage backend - using file storage for simplicity
# For production, consider using PostgreSQL, Consul, or Raft
storage "file" {
  path = "/openbao/data"
}

# Listener configuration
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true  # TLS termination handled by Traefik

  # Enable Prometheus metrics
  telemetry {
    unauthenticated_metrics_access = true
  }
}

# API address for client redirects
api_addr = "http://openbao:8200"

# Cluster address for HA (if needed in future)
cluster_addr = "http://openbao:8201"

# UI configuration
ui = true

# Disable memory locking (set to false in production with proper capabilities)
disable_mlock = true

# Logging
log_level = "info"

# Telemetry for Prometheus
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname          = true
}

# Default lease TTL
default_lease_ttl = "768h"  # 32 days

# Max lease TTL
max_lease_ttl = "8760h"  # 365 days
