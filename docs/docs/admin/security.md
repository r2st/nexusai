---
sidebar_position: 3
---

# Security Operations

## Authorization model

- Fine-grained authorization is supported via OpenFGA (optional stack).
- Backend permission checks are implemented in the security services layer.

## Secrets

If OpenBao is enabled, treat it as the source of truth for API keys and service credentials and restrict access appropriately.

