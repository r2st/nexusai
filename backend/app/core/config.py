"""Application configuration using Pydantic Settings.

All configuration is loaded from environment variables or .env file.
No hardcoded defaults for critical infrastructure settings.
Copy .env.example to .env and customize as needed.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import json

from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory (where .env should be)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

# Pre-load environment variables from .env file
# This ensures all env vars are available before Settings is instantiated
# Note: override=False so Docker environment variables take precedence over .env file
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=False)


def parse_str_list(v: Any) -> list[str]:
    """Parse list from JSON string or comma-separated values."""
    if v is None:
        return []
    if isinstance(v, list):
        return list(v)
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return []
        # Try JSON parsing first
        if v.startswith("["):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        # Fall back to comma-separated
        return [item.strip() for item in v.split(",") if item.strip()]
    return []


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required settings will fail fast if not provided in .env file.
    Optional settings have sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application (defaults are fine for these)
    # ==========================================================================
    APP_NAME: str = "NexusAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    SECRET_KEY: str | None = None
    API_PREFIX: str = "/api/v1"

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def secret_key_from_jwt(cls, v: Any) -> str:
        """Accept SECRET_KEY or fall back to JWT_SECRET."""
        if v:
            return v
        jwt = os.environ.get("JWT_SECRET")
        if jwt:
            return jwt
        raise ValueError("SECRET_KEY or JWT_SECRET must be set")

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = True
    BACKEND_URL: str = "http://localhost:8000"  # Base URL for self-referencing

    # CORS - use str type to prevent auto JSON parsing, validator converts to list
    CORS_ORIGINS: str | list[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str | list[str] = ["*"]
    CORS_ALLOW_HEADERS: str | list[str] = ["*"]

    @field_validator("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", "ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_list_fields(cls, v: Any) -> list[str]:
        """Parse list fields from JSON string or comma-separated values."""
        return parse_str_list(v)

    # ==========================================================================
    # Database - ALL from .env, no defaults
    # ==========================================================================
    DATABASE_HOST: str | None = None
    DATABASE_PORT: int = 5432
    DATABASE_USER: str | None = None
    DATABASE_PASSWORD: str | None = None
    DATABASE_NAME: str | None = None
    DATABASE_URL: str | None = None
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        """Build DATABASE_URL from components, or use DATABASE_URL directly."""
        if not self.DATABASE_URL:
            if not all([self.DATABASE_HOST, self.DATABASE_USER, self.DATABASE_PASSWORD, self.DATABASE_NAME]):
                raise ValueError(
                    "Either DATABASE_URL or DATABASE_HOST/USER/PASSWORD/NAME must be set"
                )
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
                f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        return self

    # ==========================================================================
    # Redis - ALL from .env, no defaults
    # ==========================================================================
    REDIS_HOST: str | None = None
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str | None = None

    @model_validator(mode="after")
    def build_redis_url(self) -> "Settings":
        """Build REDIS_URL from components, or use REDIS_URL directly."""
        if not self.REDIS_URL:
            if not self.REDIS_HOST:
                raise ValueError("Either REDIS_URL or REDIS_HOST must be set")
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.REDIS_URL = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return self

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # OAuth Providers
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    # AI Providers - each provider has its own default model
    # Just change DEFAULT_AI_PROVIDER to switch providers
    DEFAULT_AI_PROVIDER: str = "google"
    AI_PROVIDER_FALLBACK: str = "anthropic,ollama,openai"

    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE: str | None = None
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"

    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_DEFAULT_MODEL: str = "claude-sonnet-4-20250514"

    GOOGLE_API_KEY: str | None = None
    GOOGLE_DEFAULT_MODEL: str = "gemini-2.5-flash"

    GROQ_API_KEY: str | None = None
    GROQ_DEFAULT_MODEL: str = "llama-3.3-70b-versatile"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.2"

    # Vector Store
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # File Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: str | list[str] = [
        ".pdf", ".docx", ".doc", ".txt", ".md",
        ".csv", ".xlsx", ".xls", ".json",
        ".png", ".jpg", ".jpeg", ".gif", ".webp"
    ]
    UPLOAD_DIR: str = "./uploads"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    PER_TENANT_RATE_LIMIT: int = 1000  # Per tenant per minute
    PER_USER_RATE_LIMIT: int = 100  # Per user per minute
    WS_IDLE_TIMEOUT_SECONDS: int = 120
    WS_RATE_LIMIT_WINDOW_SECONDS: int = 60
    WS_MAX_MESSAGES_PER_WINDOW: int = 120

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # DevLake Integration
    DEVLAKE_API_URL: str = "http://localhost:8080"
    DEVLAKE_ENABLED: bool = True
    DEVLAKE_UI_URL: str = "http://localhost:4000"
    GRAFANA_URL: str = "http://localhost:3002"
    GRAFANA_ADMIN_TOKEN: str | None = None

    # OpenBao (Secret Management)
    OPENBAO_URL: str | None = None
    OPENBAO_TOKEN: str | None = None
    OPENBAO_NAMESPACE: str | None = None

    # OpenFGA (Authorization)
    OPENFGA_URL: str | None = None
    OPENFGA_STORE_ID: str | None = None
    OPENFGA_MODEL_ID: str | None = None

    # OpenTelemetry (Observability)
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "nexusai-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_EXPORTER_OTLP_PROTOCOL: str = "grpc"
    OTEL_TRACES_SAMPLER: str = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = 0.1

    # Phoenix (Arize AI) - Hallucination Detection
    PHOENIX_ENABLED: bool = False
    PHOENIX_ENDPOINT: str | None = None  # Local: "http://localhost:6006", Cloud: "https://app.phoenix.arize.com"
    PHOENIX_API_KEY: str | None = None  # Required for Phoenix Cloud
    PHOENIX_PROJECT_NAME: str = "nexusai"
    PHOENIX_COLLECT_TRACES: bool = True
    HALLUCINATION_DETECTION_ENABLED: bool = True
    HALLUCINATION_SCORE_THRESHOLD: float = 0.7  # Responses below this are flagged
    HALLUCINATION_CHECK_RAG_RESPONSES: bool = True  # Check RAG responses for grounding
    HALLUCINATION_EVAL_MODEL: str | None = None  # Model for evals (defaults to configured LLM)

    # Multi-tenancy
    MULTI_TENANT_ENABLED: bool = True
    DEFAULT_ORG_MAX_MEMBERS: int = 5
    DEFAULT_ORG_MAX_PROJECTS: int = 3

    # Trial Settings
    TRIAL_DURATION_DAYS: int = 14
    TRIAL_TIER: str = "professional"  # Tier level during trial
    TRIAL_MAX_MEMBERS: int = 50  # Member limit during trial
    TRIAL_MAX_PROJECTS: int = 20  # Project limit during trial
    TRIAL_REMINDER_DAYS: int = 3  # Days before expiry to send reminders

    # Tier Limits (default limits per tier)
    FREE_TIER_MAX_MEMBERS: int = 5
    FREE_TIER_MAX_PROJECTS: int = 3
    STARTER_TIER_MAX_MEMBERS: int = 10
    STARTER_TIER_MAX_PROJECTS: int = 10
    PROFESSIONAL_TIER_MAX_MEMBERS: int = 50
    PROFESSIONAL_TIER_MAX_PROJECTS: int = 50
    ENTERPRISE_TIER_MAX_MEMBERS: int = 1000
    ENTERPRISE_TIER_MAX_PROJECTS: int = 500

    # Code Similarity Service
    SIMILARITY_SERVICE_URL: str | None = None
    SIMILARITY_ENABLED: bool = False

    # ClickHouse Analytics
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_DATABASE: str = "nexusai"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""

    # Keycloak OAuth2/OIDC
    KEYCLOAK_URL: str | None = None
    KEYCLOAK_REALM: str = "nexusai"
    KEYCLOAK_CLIENT_ID: str | None = None
    KEYCLOAK_CLIENT_SECRET: str | None = None

    # Database Scalability
    DATABASE_READ_REPLICA_URL: str | None = None
    DATABASE_USE_NULL_POOL: bool = False
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800  # Recycle connections after 30 minutes
    DATABASE_STATEMENT_TIMEOUT: int = 30000  # 30 seconds in ms
    DATABASE_LOCK_TIMEOUT: int = 10000  # 10 seconds in ms

    # Horizontal Scaling
    ENABLE_CLUSTER_MODE: bool = False
    WORKER_ID: str | None = None  # Unique ID for this worker instance
    HEALTH_CHECK_INTERVAL: int = 30  # seconds

    # Connection Limits (for scaling)
    MAX_CONCURRENT_REQUESTS: int = 1000
    MAX_REQUEST_BODY_SIZE: int = 10 * 1024 * 1024  # 10MB
    REQUEST_TIMEOUT: int = 30  # seconds

    # Background Tasks
    TASK_QUEUE_ENABLED: bool = True
    TASK_WORKER_CONCURRENCY: int = 10
    TASK_QUEUE_MAX_JOBS: int = 100
    TASK_QUEUE_JOB_TIMEOUT: int = 300  # 5 minutes

    # Auto-scaling hints
    SCALE_MIN_INSTANCES: int = 1
    SCALE_MAX_INSTANCES: int = 10
    SCALE_CPU_TARGET: int = 70  # Target CPU utilization percentage
    SCALE_MEMORY_TARGET: int = 80  # Target memory utilization percentage

    # Feature Flags
    FEATURE_AI_ANALYTICS: bool = True
    FEATURE_CODE_SIMILARITY: bool = True
    FEATURE_PR_ISSUE_CORRELATION: bool = True
    FEATURE_SPACE_METRICS: bool = True
    FEATURE_BUSINESS_METRICS: bool = True
    FEATURE_PRODUCTIVITY_METRICS: bool = True

    # Additional AI Providers
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT: str | None = None

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"

    GOOGLE_VERTEX_PROJECT_ID: str | None = None
    GOOGLE_VERTEX_LOCATION: str = "us-central1"
    GOOGLE_VERTEX_API_KEY: str | None = None

    GROQ_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    MISTRAL_DEFAULT_MODEL: str = "mistral-large-latest"
    COHERE_API_KEY: str | None = None
    TOGETHER_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    PERPLEXITY_API_KEY: str | None = None

    # Search Providers
    TAVILY_API_KEY: str | None = None
    SERP_API_KEY: str | None = None
    BRAVE_API_KEY: str | None = None
    JINA_API_KEY: str | None = None

    # Image Generation
    STABILITY_API_KEY: str | None = None
    FLUX_API_KEY: str | None = None
    REPLICATE_API_KEY: str | None = None
    REMOVEBG_API_KEY: str | None = None

    # Speech Services
    AZURE_SPEECH_KEY: str | None = None
    AZURE_SPEECH_REGION: str | None = None
    DEEPGRAM_API_KEY: str | None = None
    ASSEMBLYAI_API_KEY: str | None = None
    ELEVENLABS_API_KEY: str | None = None
    GOOGLE_TTS_API_KEY: str | None = None

    # Meilisearch
    MEILISEARCH_HOST: str = "http://localhost:7700"
    MEILISEARCH_API_KEY: str | None = None

    # Qdrant Vector Store
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None

    # Cloud Storage - S3
    S3_BUCKET_NAME: str | None = None
    S3_REGION: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_URL_EXPIRY_SECONDS: int = 3600
    S3_DEFAULT: bool = False

    # Cloud Storage - Azure Blob
    AZURE_STORAGE_CONNECTION_STRING: str | None = None
    AZURE_STORAGE_ACCOUNT_NAME: str | None = None
    AZURE_STORAGE_ACCOUNT_KEY: str | None = None
    AZURE_STORAGE_CONTAINER: str = "nexusai"
    AZURE_STORAGE_DEFAULT: bool = False

    # Cloud Storage - Google Cloud Storage
    GCS_BUCKET_NAME: str | None = None
    GCS_PROJECT_ID: str | None = None
    GCS_CREDENTIALS_PATH: str | None = None
    GCS_REGION: str = "US"
    GCS_DEFAULT: bool = False

    # Neo4j Knowledge Graph
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str | None = None  # Required from environment if NEO4J_ENABLED=True
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_ENABLED: bool = False
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50

    # Agents Configuration
    AGENTS_ENABLED: bool = True
    AGENT_DEFAULT_LLM_PROVIDER: str = "google"
    AGENT_DEFAULT_LLM_MODEL: str = "gemini-2.5-flash"
    AGENT_MAX_EXECUTION_TIME: int = 300  # 5 minutes
    AGENT_MAX_STEPS: int = 20
    AGENT_MEMORY_ENABLED: bool = True

    # DevOps Agents
    DEVOPS_AGENTS_ENABLED: bool = True
    DORA_METRICS_CACHE_TTL: int = 3600  # 1 hour
    ADOPTION_METRICS_CACHE_TTL: int = 3600

    # OpenAPI Actions
    OPENAPI_ACTIONS_ENABLED: bool = True
    OPENAPI_ACTION_TIMEOUT: int = 30
    OPENAPI_ACTION_RATE_LIMIT: int = 60

    # Code Interpreter / Sandbox
    CODE_SANDBOX_ENABLED: bool = True
    CODE_SANDBOX_URL: str = "http://localhost:8090"
    CODE_SANDBOX_TIMEOUT: int = 30
    CODE_SANDBOX_MEMORY_LIMIT: str = "512m"
    CODE_SANDBOX_CPU_LIMIT: float = 1.0

    # MCP (Model Context Protocol)
    MCP_ENABLED: bool = True
    MCP_DEFAULT_TIMEOUT: int = 30
    MCP_MAX_CONNECTIONS: int = 10
    # MCP Error Recovery Settings
    MCP_AUTO_EXECUTE_RECOVERY: bool = True
    MCP_MAX_RECOVERY_DEPTH: int = 1

    # Feature Flags - ChatInterface Features
    FEATURE_CODE_INTERPRETER: bool = True
    FEATURE_WEB_SEARCH: bool = True
    FEATURE_IMAGE_GENERATION: bool = True
    FEATURE_SPEECH_STT: bool = True
    FEATURE_SPEECH_TTS: bool = True
    FEATURE_MCP_TOOLS: bool = True
    FEATURE_AGENT_HANDOFF: bool = True
    FEATURE_GENERATIVE_UI: bool = True
    FEATURE_CONVERSATION_IMPORT: bool = True
    FEATURE_CONVERSATION_EXPORT: bool = True
    FEATURE_KNOWLEDGE_GRAPH: bool = True
    FEATURE_DEVOPS_AGENTS: bool = True
    FEATURE_OPENAPI_ACTIONS: bool = True

    # Guardrails
    GUARDRAILS_ENABLED: bool = True
    NEMO_GUARDRAILS_ENABLED: bool = False
    NEMO_GUARDRAILS_CONFIG_PATH: str | None = None
    # JSON map keyed by tenant_id, e.g.
    # {"tenant-a":{"enable_content_filter":true,"injection_block_threshold":0.9}}
    GUARDRAILS_TENANT_POLICIES: str = "{}"
    GUARDRAILS_STREAM_HOLDBACK_CHARS: int = 80

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
