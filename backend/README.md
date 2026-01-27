# NexusAI Backend

FastAPI-based backend for NexusAI - an enterprise AI platform with RAG capabilities.

## Features

- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy** - Async ORM with PostgreSQL and pgvector support
- **Redis** - Caching and session management
- **Celery** - Background task processing
- **JWT Authentication** - Secure token-based auth
- **RAG Pipeline** - Retrieval-Augmented Generation for document Q&A

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ with pgvector extension
- Redis 7+

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev,test]"

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── api/            # API routes
│   ├── core/           # Core configuration
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   └── main.py         # Application entry point
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── fixtures/       # Test data
├── alembic/            # Database migrations
└── pyproject.toml      # Project configuration
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | - |
| `SECRET_KEY` | JWT signing key | - |
| `ENVIRONMENT` | Runtime environment | `development` |

## License

Proprietary - All rights reserved.
