---
sidebar_position: 3
---

# Terraform

Terraform configuration lives under `terraform/` and can be used to provision infrastructure for production deployments.

## Typical flow

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Because cloud layouts vary, consult the module structure in `terraform/` for provider-specific details.

