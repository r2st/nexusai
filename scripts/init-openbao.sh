#!/bin/bash
# =============================================================================
# Initialize OpenBao (Vault) for Secrets Management
# =============================================================================
set -e

OPENBAO_ADDR=${OPENBAO_ADDR:-http://localhost:8200}

echo "Initializing OpenBao..."
echo "Address: $OPENBAO_ADDR"

# Wait for OpenBao to be ready
echo "Waiting for OpenBao to be ready..."
until curl -s "$OPENBAO_ADDR/v1/sys/health" > /dev/null 2>&1; do
    echo "Waiting..."
    sleep 2
done
echo "OpenBao is ready!"

# Check if already initialized
INIT_STATUS=$(curl -s "$OPENBAO_ADDR/v1/sys/init" | jq -r '.initialized')

if [ "$INIT_STATUS" = "true" ]; then
    echo "OpenBao is already initialized."

    # Check seal status
    SEAL_STATUS=$(curl -s "$OPENBAO_ADDR/v1/sys/seal-status" | jq -r '.sealed')
    if [ "$SEAL_STATUS" = "true" ]; then
        echo "Warning: OpenBao is sealed. Please unseal manually."
    else
        echo "OpenBao is unsealed and ready."
    fi
    exit 0
fi

# Initialize OpenBao
echo "Initializing OpenBao with 5 key shares and 3 threshold..."
INIT_RESPONSE=$(curl -s -X POST "$OPENBAO_ADDR/v1/sys/init" \
    -H "Content-Type: application/json" \
    -d '{
        "secret_shares": 5,
        "secret_threshold": 3
    }')

# Extract keys and root token
ROOT_TOKEN=$(echo "$INIT_RESPONSE" | jq -r '.root_token')
UNSEAL_KEYS=$(echo "$INIT_RESPONSE" | jq -r '.keys[]')

if [ "$ROOT_TOKEN" = "null" ] || [ -z "$ROOT_TOKEN" ]; then
    echo "Error initializing OpenBao. Response:"
    echo "$INIT_RESPONSE"
    exit 1
fi

# Save keys to secure file
KEYS_FILE="./openbao-keys.json"
echo "$INIT_RESPONSE" > "$KEYS_FILE"
chmod 600 "$KEYS_FILE"

echo ""
echo "=========================================="
echo "OpenBao initialized successfully!"
echo "=========================================="
echo ""
echo "Root Token: $ROOT_TOKEN"
echo ""
echo "Unseal Keys saved to: $KEYS_FILE"
echo "IMPORTANT: Store these keys securely and delete this file!"
echo ""

# Unseal OpenBao
echo "Unsealing OpenBao..."
KEYS_ARRAY=($(echo "$INIT_RESPONSE" | jq -r '.keys[:3][]'))

for KEY in "${KEYS_ARRAY[@]}"; do
    curl -s -X POST "$OPENBAO_ADDR/v1/sys/unseal" \
        -H "Content-Type: application/json" \
        -d "{\"key\": \"$KEY\"}" > /dev/null
done

# Verify unseal
SEAL_STATUS=$(curl -s "$OPENBAO_ADDR/v1/sys/seal-status" | jq -r '.sealed')
if [ "$SEAL_STATUS" = "false" ]; then
    echo "OpenBao successfully unsealed!"
else
    echo "Warning: OpenBao is still sealed."
fi

# Enable KV secrets engine
echo "Enabling KV secrets engine..."
export BAO_ADDR="$OPENBAO_ADDR"
export BAO_TOKEN="$ROOT_TOKEN"

curl -s -X POST "$OPENBAO_ADDR/v1/sys/mounts/secret" \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "type": "kv",
        "options": {
            "version": "2"
        }
    }' > /dev/null

echo "KV secrets engine enabled at secret/"

# Create policies
echo "Creating access policies..."

# Admin policy
curl -s -X PUT "$OPENBAO_ADDR/v1/sys/policies/acl/admin" \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "policy": "path \"secret/*\" { capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\"] }\npath \"sys/*\" { capabilities = [\"read\", \"list\"] }"
    }' > /dev/null

# App policy (read-only for secrets)
curl -s -X PUT "$OPENBAO_ADDR/v1/sys/policies/acl/app" \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "policy": "path \"secret/data/nexusai/*\" { capabilities = [\"read\", \"list\"] }\npath \"secret/metadata/nexusai/*\" { capabilities = [\"read\", \"list\"] }"
    }' > /dev/null

echo "Policies created: admin, app"

echo ""
echo "=========================================="
echo "OpenBao setup complete!"
echo "=========================================="
echo ""
echo "Add this to your .env file:"
echo "  OPENBAO_TOKEN=$ROOT_TOKEN"
echo ""
echo "Create a less privileged token for the application:"
echo "  bao token create -policy=app -ttl=720h"
