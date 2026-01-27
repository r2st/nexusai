# NexusAI

Engineering metrics platform powered by DevLake with AI-assisted setup.

## Quick Start

### Option 1: Free Cloud LLM (Recommended for Quick Start)

```bash
# Clone and setup
git clone <repo-url> && cd nexusai
cp .env.example .env

# Get a FREE Google Gemini API key at: https://makersuite.google.com/app/apikey
# Add to .env: GOOGLE_API_KEY=your-key-here

# Start development
make dev
make migrate
```

### Option 2: Local LLM (Free, Unlimited, Private)

```bash
# Clone and setup
git clone <repo-url> && cd nexusai
cp .env.example .env

# Start Ollama and pull a model
make ollama-up
make ollama-pull MODEL=llama3.2   # or mistral, codellama, mixtral

# Update .env:
# DEFAULT_AI_PROVIDER=ollama
# DEFAULT_AI_MODEL=llama3.2

# Start development
make dev
make migrate
```

## Free LLM Options

NexusAI supports multiple free LLM providers out of the box:

| Provider | Free Tier | Speed | Get API Key |
|----------|-----------|-------|-------------|
| **Ollama** | Unlimited (local) | Medium | No key needed |
| **Google Gemini** | 60 req/min | Fast | [makersuite.google.com](https://makersuite.google.com/app/apikey) |
| **Groq** | 30 req/min | Very Fast | [console.groq.com](https://console.groq.com) |
| **Together AI** | $25 credit | Fast | [api.together.xyz](https://api.together.xyz) |
| **OpenRouter** | Some free models | Varies | [openrouter.ai](https://openrouter.ai) |
| **DeepSeek** | Limited free | Fast | [platform.deepseek.com](https://platform.deepseek.com) |

## Requirements

- Docker & Docker Compose v2.0+
- 8GB RAM (16GB recommended)
- One of: Free API key (Google, Groq) OR local LLM via Ollama

## Endpoints

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| DevLake UI | http://localhost:4000 |
| Grafana Dashboards | http://localhost:3002 |
| Ollama Web UI | http://localhost:3003 |

## Connecting Data Sources (GitHub, Jira, etc.)

NexusAI uses [Apache DevLake](https://devlake.apache.org/) to collect data from 40+ engineering tools.

```bash
# Start DevLake
make devlake-up

# Wait 30-60 seconds, then open: http://localhost:4000
```

### Connect GitHub

1. Open http://localhost:4000
2. Click **Connections** → **Create Connection**
3. Select **GitHub**
4. Enter your **GitHub Personal Access Token** ([create one here](https://github.com/settings/tokens))
   - Required scopes: `repo`, `read:org`, `read:user`
5. Click **Save Connection**
6. Create a **Project** and add your GitHub repos
7. Click **Collect Data** to start syncing

### Supported Data Sources

| Category | Tools |
|----------|-------|
| **Code** | GitHub, GitLab, Bitbucket, Gitee |
| **Issues** | Jira, GitHub Issues, GitLab Issues, Tapd, Zentao |
| **CI/CD** | Jenkins, GitHub Actions, GitLab CI, CircleCI, Azure DevOps |
| **Code Review** | GitHub PRs, GitLab MRs, Gerrit, Bitbucket |

### View Metrics

After data collection, view dashboards at http://localhost:3002:
- DORA Metrics (Deployment Frequency, Lead Time, MTTR, Change Failure Rate)
- Engineering Productivity
- Code Quality
- Sprint Reports

## Common Commands

```bash
# Development
make dev              # Start development environment
make stop             # Stop all services
make logs             # View all logs
make logs-backend     # View backend logs only
make status           # Show container status

# Database
make migrate          # Run database migrations
make clean-db-volume  # Reset database (WARNING: destroys data)

# Rebuilding (after changing dependencies)
make rebuild-backend  # Rebuild backend container
make rebuild-frontend # Rebuild frontend container

# Local LLM
make ollama-up        # Start Ollama + Web UI
make ollama-pull      # Pull a model (MODEL=llama3.2)

# DevLake (Data Collection)
make devlake-up       # Start DevLake + Grafana
make devlake-down     # Stop DevLake
make devlake-status   # Check DevLake status

# Testing
make test             # Run all tests
make lint             # Run linters

# Production
make prod             # Start production environment

# Cleanup
make reset-dev        # Full reset of dev environment
make nuke             # Nuclear option: remove everything

# Help
make help             # Show all available commands
```

## Configuration

### Switching AI Providers

Edit your `.env` file:

```bash
# For Google Gemini (default, free tier)
DEFAULT_AI_PROVIDER=google
DEFAULT_AI_MODEL=gemini-1.5-flash
GOOGLE_API_KEY=your-key

# For Groq (fastest free option)
DEFAULT_AI_PROVIDER=groq
DEFAULT_AI_MODEL=llama-3.1-70b-versatile
GROQ_API_KEY=your-key

# For Ollama (local, unlimited)
DEFAULT_AI_PROVIDER=ollama
DEFAULT_AI_MODEL=llama3.2

# For OpenAI (paid)
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key
```

## Documentation

- [Development Guide](docs/DEVELOPMENT.md) - Full setup, commands, and architecture
- [Setup Chatbot](docs/SETUP_CHATBOT.md) - AI assistant documentation
- [DevLake Improvements](docs/DEVLAKE_IMPROVEMENTS.md) - Enhancement details

## License

MIT
