# OpenBao Storage Strategy

## Overview

NexusAI uses OpenBao (open-source fork of HashiCorp Vault) for secure secret management, providing encryption, secret rotation, and tenant isolation.

## Architecture

### 1. OpenBao Client

**Location**: `backend/app/core/secrets.py`

The `OpenBaoClient` provides:
- Secret storage and retrieval
- Tenant-isolated secrets
- Encryption/decryption
- Local fallback for development

### 2. Secret Storage

Secrets are stored with tenant isolation:
- Path format: `secret/data/tenants/{tenant_id}/{path}`
- Each tenant's secrets are completely isolated
- Secrets are encrypted at rest

### 3. Local Fallback

For development without OpenBao:
- Uses Fernet encryption (symmetric)
- Key derived from `SECRET_KEY`
- Secrets stored in memory (not persistent)

## Setup

### 1. Start OpenBao

```bash
# Using Docker Compose
docker-compose -f docker/compose/services/docker-compose.auth.yml up -d openbao

# Initialize OpenBao
./scripts/init-openbao.sh
```

### 2. Configure Environment

```env
OPENBAO_URL=http://localhost:8200
OPENBAO_TOKEN=your-root-token
OPENBAO_NAMESPACE=nexusai  # Optional
```

### 3. Unseal OpenBao

After initialization, unseal OpenBao using the unseal keys:

```bash
# Unseal with 3 of 5 keys (threshold)
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

## Usage

### Storing Secrets

```python
from app.core.secrets import openbao_client

# Store a secret
path = await openbao_client.store_secret(
    path="github/token",
    data={"token": "ghp_xxx"},
    tenant_id="tenant-uuid"
)
```

### Retrieving Secrets

```python
# Get a secret
secret = await openbao_client.get_secret(
    path="github/token",
    tenant_id="tenant-uuid"
)
if secret:
    token = secret["token"]
```

### Deleting Secrets

```python
# Delete a secret
success = await openbao_client.delete_secret(
    path="github/token",
    tenant_id="tenant-uuid"
)
```

### Encryption/Decryption

```python
# Encrypt data
ciphertext = await openbao_client.encrypt(
    plaintext="sensitive data",
    key_name="default"
)

# Decrypt data
plaintext = await openbao_client.decrypt(
    ciphertext=ciphertext,
    key_name="default"
)
```

## Secret Categories

### 1. Connection Credentials

- GitHub tokens
- GitLab tokens
- Jira credentials
- CI/CD credentials

### 2. API Keys

- LLM API keys (OpenAI, Anthropic, etc.)
- Third-party service keys
- Integration tokens

### 3. Encryption Keys

- Data encryption keys
- Signing keys
- Certificate keys

## Tenant Isolation

All secrets are tenant-isolated:
- Path includes tenant ID
- Cross-tenant access is prevented
- Secrets are scoped to tenant context

## Security Considerations

1. **Token Management**: Root tokens should be rotated regularly
2. **Unseal Keys**: Store unseal keys securely (3 of 5 required)
3. **Access Policies**: Configure OpenBao policies for least privilege
4. **Audit Logging**: Enable audit logging in OpenBao
5. **Secret Rotation**: Implement secret rotation policies

## Development Mode

When OpenBao is unavailable:
- System uses local Fernet encryption
- Secrets stored in memory
- Not suitable for production

## Production Recommendations

1. **High Availability**: Deploy OpenBao in HA mode
2. **Backup**: Regular backups of OpenBao data
3. **Monitoring**: Monitor OpenBao health and performance
4. **Policies**: Define access policies for different roles
5. **Rotation**: Implement automatic secret rotation

## Integration Points

### 1. Connection Management

Connections store credentials in OpenBao:

```python
# Store connection credentials
await openbao_client.store_secret(
    path=f"connections/{connection_id}",
    data={
        "token": token,
        "api_key": api_key
    },
    tenant_id=tenant_id
)
```

### 2. API Key Storage

API keys are stored securely:

```python
# Store API key
await openbao_client.store_secret(
    path="api_keys/openai",
    data={"key": api_key},
    tenant_id=tenant_id
)
```

## Monitoring

Monitor OpenBao:
- Health: `GET /v1/sys/health`
- Metrics: `GET /v1/sys/metrics`
- Audit logs: Check audit log files

## Troubleshooting

### OpenBao Unavailable

If OpenBao is down:
- System uses local fallback
- Secrets are encrypted with Fernet
- Not suitable for production

### Secret Not Found

Check:
1. Path is correct
2. Tenant ID is correct
3. Secret exists in OpenBao
4. Token has read permissions

## References

- [OpenBao Documentation](https://openbao.org/)
- [Secret Engines](https://openbao.org/docs/concepts/secrets-engines)
- [Policies](https://openbao.org/docs/concepts/policies)
