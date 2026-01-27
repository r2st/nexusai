# OpenBao Token Management

## Overview

This guide covers token management for OpenBao, including creation, rotation, and best practices.

## Token Types

### 1. Root Token

- Full access to all OpenBao operations
- Should be stored securely
- Used for initial setup and emergencies
- Should be rotated regularly

### 2. Service Tokens

- Limited scope tokens for services
- Used by NexusAI backend
- Can be revoked independently
- Should follow least privilege

### 3. Periodic Tokens

- Tokens with expiration
- Automatically expire after TTL
- Can be renewed
- More secure than permanent tokens

## Initial Setup

### 1. Initialize OpenBao

```bash
./scripts/init-openbao.sh
```

This creates:
- Root token (save securely!)
- 5 unseal keys (save 3+ securely!)
- Initial configuration

### 2. Unseal OpenBao

```bash
# Unseal with 3 of 5 keys
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

### 3. Create Service Token

```bash
# Login with root token
vault auth -method=userpass username=admin

# Create service token
vault token create \
  -policy=nexusai-service \
  -ttl=8760h \
  -renewable=true
```

## Token Policies

### Service Policy

Create policy for NexusAI service:

```hcl
# nexusai-service.hcl
path "secret/data/tenants/*" {
  capabilities = ["create", "read", "update", "delete"]
}

path "secret/data/connections/*" {
  capabilities = ["create", "read", "update", "delete"]
}

path "transit/encrypt/default" {
  capabilities = ["update"]
}

path "transit/decrypt/default" {
  capabilities = ["update"]
}
```

Apply policy:

```bash
vault policy write nexusai-service nexusai-service.hcl
```

## Token Rotation

### 1. Create New Token

```bash
# Create new service token
NEW_TOKEN=$(vault token create \
  -policy=nexusai-service \
  -ttl=8760h \
  -renewable=true \
  -format=json | jq -r '.auth.client_token')
```

### 2. Update Configuration

```env
OPENBAO_TOKEN=$NEW_TOKEN
```

### 3. Revoke Old Token

```bash
# Revoke old token
vault token revoke <old-token>
```

## Best Practices

### 1. Token Storage

- Store tokens in secure secret manager
- Never commit tokens to git
- Use environment variables
- Rotate regularly

### 2. Token Scope

- Use least privilege principle
- Create separate tokens for different services
- Limit token TTL
- Enable token renewal

### 3. Monitoring

- Monitor token usage
- Alert on token expiration
- Track token access patterns
- Audit token operations

## Automated Rotation

### Script for Token Rotation

```bash
#!/bin/bash
# rotate-openbao-token.sh

OLD_TOKEN=$OPENBAO_TOKEN
NEW_TOKEN=$(vault token create \
  -policy=nexusai-service \
  -ttl=8760h \
  -renewable=true \
  -format=json | jq -r '.auth.client_token')

# Update environment
export OPENBAO_TOKEN=$NEW_TOKEN

# Restart services
systemctl restart nexusai-backend

# Revoke old token
vault token revoke $OLD_TOKEN
```

## Emergency Procedures

### Lost Root Token

If root token is lost:
1. Use unseal keys to unseal OpenBao
2. Generate new root token (requires unseal)
3. Update all configurations
4. Revoke old root token (if found)

### Compromised Token

If token is compromised:
1. Immediately revoke token
2. Create new token
3. Update configuration
4. Review audit logs
5. Rotate affected secrets

## Integration with NexusAI

### Environment Configuration

```env
# Production
OPENBAO_URL=https://openbao.example.com
OPENBAO_TOKEN=<service-token>
OPENBAO_NAMESPACE=nexusai

# Development
OPENBAO_URL=http://localhost:8200
OPENBAO_TOKEN=<dev-token>
```

### Token Validation

NexusAI validates tokens on startup:

```python
from app.core.secrets import openbao_client

if await openbao_client.is_available():
    logger.info("OpenBao is available")
else:
    logger.warning("OpenBao unavailable, using local fallback")
```

## Monitoring

### Token Metrics

Monitor:
- Token expiration times
- Token usage frequency
- Failed authentication attempts
- Token renewal success rate

### Alerts

Set up alerts for:
- Token expiration (7 days before)
- Failed authentication
- Unusual token usage patterns
- Token rotation failures

## References

- [OpenBao Token Documentation](https://openbao.org/docs/concepts/tokens)
- [Token Policies](https://openbao.org/docs/concepts/policies)
- [Token Rotation](https://openbao.org/docs/guides/operations/token-rotation)
