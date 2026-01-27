# =============================================================================
# NexusAI Backend Dockerfile - Multi-stage Production Build
# =============================================================================
# Build stages:
#   1. base       - Common Python base with system dependencies
#   2. builder    - Builds Python dependencies with build tools
#   3. development - Full development environment with dev tools
#   4. production  - Minimal production image with only runtime deps
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base Image
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies required at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for healthcheck
    curl \
    # Required for PostgreSQL
    libpq5 \
    # Required for some ML libraries
    libgomp1 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 nexusai \
    && useradd --uid 1000 --gid nexusai --shell /bin/bash --create-home nexusai

# -----------------------------------------------------------------------------
# Stage 2: Builder
# -----------------------------------------------------------------------------
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
WORKDIR /build

# Copy only requirements first for better caching
COPY requirements.txt requirements-prod.txt* ./

# Install production dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# If requirements-prod.txt exists, install those too
RUN if [ -f requirements-prod.txt ]; then pip install -r requirements-prod.txt; fi

# Install Gunicorn for production
RUN pip install gunicorn

# -----------------------------------------------------------------------------
# Stage 3: Development
# -----------------------------------------------------------------------------
FROM base AS development

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install development dependencies
WORKDIR /app
COPY requirements-dev.txt* ./
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

# Install debugpy for remote debugging
RUN pip install debugpy watchdog[watchmedo]

# Set ownership
RUN chown -R nexusai:nexusai /app

# Switch to non-root user
USER nexusai

# Expose ports (API + debugger)
EXPOSE 8000 5678

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -----------------------------------------------------------------------------
# Stage 4: Production
# -----------------------------------------------------------------------------
FROM base AS production

# Labels for container metadata
LABEL org.opencontainers.image.title="NexusAI Backend" \
      org.opencontainers.image.description="NexusAI Backend API Service" \
      org.opencontainers.image.vendor="NexusAI" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT"

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=nexusai:nexusai . .

# Remove unnecessary files
RUN rm -rf \
    tests/ \
    .git/ \
    .github/ \
    .pytest_cache/ \
    .mypy_cache/ \
    __pycache__/ \
    *.md \
    Dockerfile* \
    docker-compose* \
    .env* \
    .gitignore \
    .dockerignore \
    Makefile \
    2>/dev/null || true

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/tmp /app/uploads \
    && chown -R nexusai:nexusai /app

# Switch to non-root user
USER nexusai

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command with Gunicorn + Uvicorn workers
CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "--enable-stdio-inheritance"]
