---
sidebar_position: 2
---

# Kubernetes (Helm)

NexusAI includes a Helm chart under `helm/nexusai/` for cluster deployments.

## Typical flow

```bash
helm upgrade --install nexusai ./helm/nexusai -f ./helm/nexusai/values.yaml
```

## Notes

- Configure secrets via Kubernetes secrets (or external secret managers).
- Ensure Postgres/Redis are provided (in-cluster or managed services).
- Configure ingress (Traefik/Nginx) and TLS for your domain.

