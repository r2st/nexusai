---
sidebar_position: 1
---

# Installation

This guide covers the different ways to install and run NexusAI.

## Prerequisites

Before installing NexusAI, ensure you have the following:

- **Docker** 24.0+ and **Docker Compose** v2.20+
- **Git** for cloning the repository
- At least **4GB RAM** available for containers
- An **API key** from at least one AI provider (OpenAI, Anthropic, etc.)

## Quick Start with Docker Compose

The fastest way to get NexusAI running locally:

```bash
# Clone the repository
git clone https://github.com/nexusai/nexusai.git
cd nexusai

# Copy the example environment file
cp .env.example .env

# Edit the .env file with your API keys
# Required: Set OPENAI_API_KEY or ANTHROPIC_API_KEY
# Required: Set SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD

# Start all services
docker compose up -d

# Check service health
docker compose ps
```

Once running, access NexusAI at:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Environment Configuration

Create a `.env` file with the following required variables:

```bash
# Application
SECRET_KEY=your-secret-key-at-least-32-characters
DOMAIN=localhost

# Database
POSTGRES_USER=nexusai
POSTGRES_PASSWORD=your-secure-database-password
POSTGRES_DB=nexusai

# Redis
REDIS_PASSWORD=your-secure-redis-password

# Search
MEILISEARCH_API_KEY=your-meilisearch-key

# AI Providers (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Production Deployment

For production environments, we recommend:

### Option 1: Kubernetes with Helm

```bash
# Add the Helm repository
helm repo add nexusai https://charts.nexusai.example.com
helm repo update

# Install NexusAI
helm install nexusai nexusai/nexusai \
  --namespace nexusai \
  --create-namespace \
  -f values-prod.yaml
```

See the [Kubernetes Deployment Guide](/docs/deployment/kubernetes) for details.

### Option 2: Terraform Infrastructure

```bash
# Initialize Terraform
cd terraform
terraform init

# Plan the deployment
terraform plan -var-file=environments/prod/terraform.tfvars

# Apply
terraform apply -var-file=environments/prod/terraform.tfvars
```

See the [Terraform Deployment Guide](/docs/deployment/terraform) for details.

## Verification

After installation, verify everything is working:

```bash
# Check all services are healthy
docker compose ps

# Test the API
curl http://localhost:8000/health

# Test the frontend
curl http://localhost:3000

# View logs if needed
docker compose logs -f backend
```

## Next Steps

- [Quick Start Guide](/docs/getting-started/quickstart) - Create your first chat
- [Configuration](/docs/getting-started/configuration) - Customize your installation
- [Security Setup](/docs/architecture/security) - Configure authentication
