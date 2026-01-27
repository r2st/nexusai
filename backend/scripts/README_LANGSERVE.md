# LangServe Test Script

This script tests the LangServe API endpoints for NexusAI.

## Prerequisites

1. Backend server running (default: `http://localhost:8000`)
2. Optional: Authentication token for testing authenticated endpoints

## Usage

### Basic Usage

```bash
# Test all endpoints (no auth required for health/info/playground)
python scripts/test_langserve.py

# Test with authentication token
python scripts/test_langserve.py --token YOUR_AUTH_TOKEN

# Test specific endpoint
python scripts/test_langserve.py --test health
python scripts/test_langserve.py --test invoke --token YOUR_TOKEN

# Test against different server
python scripts/test_langserve.py --url http://localhost:8080
```

### Available Tests

- `health` - Health check endpoint
- `info` - Service information endpoint
- `invoke` - Non-streaming chat endpoint (requires auth)
- `stream` - Streaming chat endpoint (requires auth)
- `batch` - Batch processing endpoint (requires auth)
- `playground` - Playground UI endpoint
- `all` - Run all tests (default)

## Getting an Auth Token

To test authenticated endpoints, you need a JWT token. You can:

1. Login via the API:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@nexusai.dev", "password": "admin123"}'
```

2. Extract the `access_token` from the response

3. Use it with the test script:
```bash
python scripts/test_langserve.py --token YOUR_ACCESS_TOKEN
```

## Example Output

```
================================================================================
LangServe Integration Tests
================================================================================
Testing: http://localhost:8000

================================================================================
LangServe Test Results
================================================================================
Test                          Status               Details
Health Check                  ✅ PASS              {'status': 'healthy', 'service': 'langserve'}
Info Endpoint                 ✅ PASS              {'name': 'NexusAI Chat Service', ...}
Playground Endpoint           ✅ PASS              HTML page returned
Invoke Endpoint               ⚠️  AUTH REQUIRED    Need authentication token
Stream Endpoint               ⚠️  AUTH REQUIRED    Need authentication token
Batch Endpoint                ⚠️  AUTH REQUIRED    Need authentication token

Summary: 3/6 tests passed
Note: 3 tests require authentication. Provide a token with --token option.
```

## Running Pytest Tests

For more comprehensive testing with database fixtures:

```bash
# Run all LangServe integration tests
pytest tests/integration/test_langserve.py -v

# Run specific test
pytest tests/integration/test_langserve.py::TestLangServeEndpoints::test_invoke_endpoint -v
```

## Endpoints

- `GET /api/v1/langserve/health` - Health check
- `GET /api/v1/langserve/info` - Service information
- `POST /api/v1/langserve/chat/invoke` - Non-streaming chat
- `POST /api/v1/langserve/chat/stream` - Streaming chat (SSE)
- `POST /api/v1/langserve/chat/batch` - Batch processing
- `GET /api/v1/langserve/chat/playground` - Playground UI

## Troubleshooting

### Connection Errors

If you get connection errors, ensure:
- Backend server is running
- Correct URL is specified (default: `http://localhost:8000`)
- No firewall blocking the connection

### Authentication Errors

If authenticated endpoints return 401:
- Verify your token is valid
- Check token hasn't expired
- Ensure user account is active

### Timeout Errors

If tests timeout:
- Check backend server is responsive
- Verify database connection is working
- Check LLM API keys are configured
