# Getting Started with NexusAI

This guide will help you set up and run NexusAI for development or production use.

## Prerequisites

- **Docker & Docker Compose** (recommended)
- **Node.js 20+** (for local frontend development)
- **Python 3.12+** (for local backend development)
- **PostgreSQL 16** (if running without Docker)
- **Redis 7** (if running without Docker)

## Quick Start with Docker

The fastest way to get started is using Docker Compose:

```bash
# Clone the repository
cd nexusai

# Copy environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env

# Start all services
docker compose up -d

# View logs
docker compose logs -f
```

Access the application:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Local Development Setup

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit configuration
nano .env

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | Random 32+ char string |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

### Optional AI Providers

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic (Claude) API key |
| `GOOGLE_API_KEY` | Google AI (Gemini) API key |
| `OLLAMA_BASE_URL` | Ollama server URL |

### OAuth Configuration

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret |

## Database Setup

If running without Docker, ensure PostgreSQL has the required extensions:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

The application will automatically create tables on first startup.

## First Steps

1. **Register an account** at http://localhost:3000/register
2. **Create a conversation** and start chatting
3. **Upload documents** for RAG functionality
4. **Explore the API** at http://localhost:8000/docs

## Troubleshooting

### Backend won't start

Check database connection:
```bash
docker compose logs postgres
```

Verify environment variables:
```bash
docker compose exec backend env | grep DATABASE
```

### Frontend can't connect to API

Ensure the API is running:
```bash
curl http://localhost:8000/api/v1/health
```

Check CORS configuration in backend settings.

### Vector search not working

Ensure pgvector extension is installed:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## Next Steps

- Read the [Architecture Guide](./ARCHITECTURE.md)
- Explore the [API Documentation](http://localhost:8000/docs)
- Check out the [Contributing Guide](../CONTRIBUTING.md)
