#!/bin/bash
# =============================================================================
# Initialize OpenFGA Store and Authorization Model
# =============================================================================
set -e

OPENFGA_URL=${OPENFGA_URL:-http://localhost:8080}
MODEL_FILE=${MODEL_FILE:-./deploy/openfga/model.json}

echo "Initializing OpenFGA..."
echo "URL: $OPENFGA_URL"

# Wait for OpenFGA to be ready
echo "Waiting for OpenFGA to be ready..."
until curl -s "$OPENFGA_URL/health" > /dev/null 2>&1; do
    echo "Waiting..."
    sleep 2
done
echo "OpenFGA is ready!"

# Create a store
echo "Creating store..."
STORE_RESPONSE=$(curl -s -X POST "$OPENFGA_URL/stores" \
    -H "Content-Type: application/json" \
    -d '{"name": "nexusai"}')

STORE_ID=$(echo "$STORE_RESPONSE" | jq -r '.id')

if [ "$STORE_ID" = "null" ] || [ -z "$STORE_ID" ]; then
    echo "Error creating store. Response:"
    echo "$STORE_RESPONSE"
    exit 1
fi

echo "Store created with ID: $STORE_ID"

# Create the authorization model
echo "Creating authorization model..."
if [ -f "$MODEL_FILE" ]; then
    MODEL_RESPONSE=$(curl -s -X POST "$OPENFGA_URL/stores/$STORE_ID/authorization-models" \
        -H "Content-Type: application/json" \
        -d @"$MODEL_FILE")

    MODEL_ID=$(echo "$MODEL_RESPONSE" | jq -r '.authorization_model_id')

    if [ "$MODEL_ID" = "null" ] || [ -z "$MODEL_ID" ]; then
        echo "Error creating model. Response:"
        echo "$MODEL_RESPONSE"
        exit 1
    fi

    echo "Authorization model created with ID: $MODEL_ID"
else
    echo "Warning: Model file not found at $MODEL_FILE"
    echo "Skipping model creation."
fi

echo ""
echo "=========================================="
echo "OpenFGA initialization complete!"
echo "=========================================="
echo ""
echo "Store ID: $STORE_ID"
echo "Model ID: $MODEL_ID"
echo ""
echo "Add these to your .env file:"
echo "  OPENFGA_STORE_ID=$STORE_ID"
echo "  OPENFGA_MODEL_ID=$MODEL_ID"
