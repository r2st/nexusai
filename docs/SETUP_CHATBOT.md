# Setup Chatbot - AI-Powered Admin Assistant

The Setup Chatbot is an intelligent conversational assistant that guides users through all DevLake administrative tasks including connection setup, project creation, pipeline configuration, and initial onboarding.

## Features

### Core Capabilities

1. **Connection Setup Wizard**
   - Step-by-step guidance for connecting data sources
   - Support for 40+ plugins across 11 categories (Source Control, Issue Tracking, CI/CD, Code Quality, Incident Management, Communication, Monitoring, Cloud Providers, Custom)
   - Credential validation and connection testing
   - Scope configuration (repositories, projects, boards)
   - Smart token format detection

2. **Project Management**
   - Create and configure DevLake projects
   - Enable DORA metrics tracking
   - Associate data source connections

3. **Pipeline Configuration**
   - Set up automated data collection schedules
   - Cron-based scheduling with presets (hourly, daily, weekly)
   - Incremental vs full sync options
   - Smart cron expression validation

4. **Onboarding Flow**
   - Complete guided setup for new users
   - Progressive disclosure of features
   - Context-aware recommendations

### Security Features

- **Rate Limiting**: Configurable per-operation rate limits with sliding window
- **Input Sanitization**: XSS/injection detection and prevention
- **Audit Logging**: Comprehensive event logging with severity levels
- **CSRF Protection**: Token-based cross-site request forgery prevention
- **Credential Encryption**: Fernet-based encryption with key rotation support
- **Secure Storage**: Encrypted credential storage with automatic expiration

### UX Features

- **Typing Indicators**: Real-time feedback during processing
- **Error Recovery**: Smart error classification with recovery suggestions
- **Contextual Help**: Plugin-specific help topics and examples
- **Smart Suggestions**: Auto-correction and format validation
- **Progress Tracking**: Visual progress with estimated time remaining

### Analytics & Monitoring

- **Conversation Metrics**: Session duration, completion rates, error rates
- **Performance Monitoring**: Response time percentiles (P50, P95, P99)
- **User Feedback**: Rating collection with sentiment analysis
- **Usage Analytics**: Feature usage tracking and flow funnels

### Technical Features

- **State Machine Architecture**: Flows are implemented as state machines for predictable navigation
- **Intent Classification**: Fast rule-based NLU for understanding user requests
- **Session Management**: Redis-backed sessions for horizontal scalability
- **Multi-tenant Support**: Full tenant isolation for enterprise deployments
- **Quick Replies**: Interactive buttons for common actions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Components                       │
├─────────────────────────────────────────────────────────────┤
│  SetupAssistant  │  SetupLauncher  │  FloatingAssistant    │
└────────┬─────────┴────────┬────────┴──────────┬─────────────┘
         │                  │                   │
         ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  POST /setup-assistant/sessions                              │
│  POST /setup-assistant/sessions/{id}/messages                │
│  GET  /setup-assistant/plugins                               │
│  POST /setup-assistant/quick-setup/{plugin}                  │
│  POST /setup-assistant/onboarding                            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  SetupChatbotService                        │
├─────────────────────────────────────────────────────────────┤
│  Session Management   │  Flow Orchestration  │  NLU Engine  │
└───────────┬───────────┴──────────┬───────────┴──────┬───────┘
            │                      │                  │
            ▼                      ▼                  ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────┐
│   SessionStore    │  │    Setup Flows     │  │   Intent     │
│ (Redis/In-Memory) │  │ Connection/Project │  │  Classifier  │
│                   │  │ Pipeline/Onboard   │  │              │
└───────────────────┘  └────────────────────┘  └──────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                     DevLake Service                          │
│  create_connection() │ create_project() │ trigger_blueprint()│
└─────────────────────────────────────────────────────────────┘
```

## API Reference

### Start a Session

```http
POST /api/v1/setup-assistant/sessions
Content-Type: application/json

{
  "flow_type": "connection",  // Optional: connection, project, pipeline, onboarding
  "plugin": "github"          // Optional: plugin for connection flow
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Welcome message...",
    "quick_replies": [
      {"label": "GitHub", "value": "connect github", "icon": "🐙"}
    ],
    "step_number": 1,
    "total_steps": 5,
    "progress_percent": 20.0
  },
  "flow_type": "connection",
  "current_step": "select_plugin"
}
```

### Send a Message

```http
POST /api/v1/setup-assistant/sessions/{session_id}/messages
Content-Type: application/json

{
  "message": "connect github",
  "quick_reply": false
}
```

**Response:**
```json
{
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Next step prompt...",
    "quick_replies": []
  },
  "session_id": "uuid",
  "current_step": "enter_name",
  "can_go_back": true,
  "is_complete": false,
  "collected_data": {"plugin": "github"},
  "errors": [],
  "warnings": []
}
```

### Quick Setup

```http
POST /api/v1/setup-assistant/quick-setup/github
```

Starts a connection flow pre-configured for the specified plugin.

### List Plugins

```http
GET /api/v1/setup-assistant/plugins
```

Returns all available plugins with their configuration requirements.

### Start Onboarding

```http
POST /api/v1/setup-assistant/onboarding
```

Starts the complete onboarding flow for new users.

## Supported Plugins (40+)

### Source Control
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| GitHub | Token | token |
| GitLab | Token | token, endpoint |
| Bitbucket | Token | token, endpoint |
| Gitee | Token | token |
| Gitea | Token | token, endpoint |
| Azure Repos | Token | organization, token |

### Issue Tracking
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| Jira | Basic | endpoint, email, token |
| Linear | Token | api_key |
| Asana | Token | access_token |
| Trello | OAuth | api_key, token |
| ClickUp | Token | api_token |
| Monday.com | Token | api_token |
| YouTrack | Token | token, endpoint |

### CI/CD
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| Jenkins | Basic | endpoint, username, token |
| GitHub Actions | Token | token |
| GitLab CI | Token | token, endpoint |
| Azure DevOps | Token | organization, token |
| CircleCI | Token | token |
| Travis CI | Token | token |
| Bamboo | Basic | endpoint, username, password |
| TeamCity | Token | endpoint, token |
| Drone CI | Token | endpoint, token |
| Buildkite | Token | token |
| Argo CD | Token | endpoint, token |

### Code Quality
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| SonarQube | Token | endpoint, token |
| SonarCloud | Token | token |
| Codecov | Token | token |
| Snyk | Token | token |
| Code Climate | Token | token |

### Incident Management
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| PagerDuty | Token | token |
| Opsgenie | Token | api_key |
| Statuspage | Token | api_key, page_id |
| FireHydrant | Token | api_key |
| Rootly | Token | api_key |

### Communication
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| Slack | OAuth | bot_token |
| Feishu (Lark) | OAuth | app_id, app_secret |
| Microsoft Teams | OAuth | client_id, client_secret, tenant_id |

### Monitoring
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| Datadog | Token | api_key, app_key |
| New Relic | Token | api_key, account_id |
| Prometheus | None | endpoint |
| Grafana | Token | endpoint, api_key |

### Cloud Providers
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| AWS | IAM | access_key_id, secret_access_key |
| Kubernetes | Token | endpoint, token |

### Custom Integrations
| Plugin | Auth Type | Required Fields |
|--------|-----------|-----------------|
| Webhook | Token | endpoint, secret |
| REST API | Various | endpoint, auth config |

## Frontend Usage

### Basic Usage

```tsx
import { SetupAssistant } from '@/components/setup-assistant';

function SetupPage() {
  return (
    <SetupAssistant
      initialFlowType="connection"
      initialPlugin="github"
      onClose={() => router.push('/dashboard')}
    />
  );
}
```

### Floating Assistant Widget

```tsx
import { FloatingAssistant } from '@/components/setup-assistant';

function Layout({ children }) {
  return (
    <>
      {children}
      <FloatingAssistant defaultOpen={false} />
    </>
  );
}
```

### Programmatic Control

```tsx
import { useSetupAssistant } from '@/components/setup-assistant';

function Dashboard() {
  const assistant = useSetupAssistant();

  return (
    <button onClick={() => assistant.openConnection('github')}>
      Connect GitHub
    </button>
  );
}
```

### Setup Launcher

```tsx
import { SetupLauncher } from '@/components/setup-assistant';

function SetupCenter() {
  const handleStart = (type, plugin) => {
    // Navigate to setup flow
  };

  return <SetupLauncher onStartSetup={handleStart} />;
}
```

## Flow Customization

### Creating Custom Flows

```python
from app.services.setup_chatbot.flows import SetupFlow, FlowStep

class CustomFlow(SetupFlow):
    def _build_steps(self):
        self.steps["step1"] = FlowStep(
            name="step1",
            prompt="What would you like to configure?",
            field_name="config_type",
            field_type="select",
            options=[
                {"value": "a", "label": "Option A"},
                {"value": "b", "label": "Option B"},
            ],
            next_step="step2",
        )
        self.initial_step = "step1"

    def get_intro_message(self):
        return ChatMessage(
            role="assistant",
            content="Let's configure your custom setup!",
        )
```

### Adding Validation

```python
def validate_api_key(value: str) -> tuple[bool, str | None]:
    if not value.startswith("sk-"):
        return False, "API key must start with 'sk-'"
    if len(value) < 20:
        return False, "API key is too short"
    return True, None

FlowStep(
    name="enter_api_key",
    prompt="Enter your API key:",
    field_name="api_key",
    field_type="password",
    validator=validate_api_key,
)
```

### Conditional Navigation

```python
FlowStep(
    name="select_auth",
    prompt="Choose authentication method:",
    field_name="auth_type",
    field_type="select",
    options=[
        {"value": "token", "label": "Personal Access Token"},
        {"value": "oauth", "label": "OAuth"},
    ],
    conditional_next=lambda data: "enter_token" if data.get("auth_type") == "token" else "oauth_setup",
)
```

## Session Store Configuration

### Redis (Production)

```python
# settings.py
REDIS_URL = "redis://localhost:6379/0"
```

The Redis session store provides:
- Horizontal scalability
- Automatic expiration (24 hour TTL)
- User session indexing

### In-Memory (Development)

Used automatically when Redis is not configured. Not suitable for production or multi-instance deployments.

## Intent Classification

The chatbot uses rule-based intent classification for fast response times:

```python
from app.services.setup_chatbot import classify_intent

result = classify_intent("connect my github account")
# IntentMatch(intent=Intent.CONNECT, confidence=0.9, entities={"plugin": "github"})
```

Supported intents:
- `CONNECT` - Setup a connection
- `CREATE_PROJECT` - Create a new project
- `CREATE_PIPELINE` - Configure a pipeline
- `GET_HELP` - Request help
- `CONFIRM` / `CANCEL` - Flow control
- And more...

## Best Practices

1. **Always test connections** before finalizing setup
2. **Use quick replies** when options are limited
3. **Provide clear error messages** with actionable guidance
4. **Enable progress indicators** for multi-step flows
5. **Cache plugin configs** to reduce API calls

## Troubleshooting

### Common Issues

**Session not found:**
- Sessions expire after 24 hours
- Check if Redis is connected (if using Redis store)

**Connection test fails:**
- Verify credentials are correct
- Check network connectivity to the data source
- Ensure tokens have required permissions

**Flow stuck:**
- Send "cancel" to reset the flow
- Check for validation errors in the response

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("app.services.setup_chatbot").setLevel(logging.DEBUG)
```

## Security Usage

### Rate Limiting

```python
from app.services.setup_chatbot import rate_limiter, RateLimitRule, RateLimitWindow

# Add custom rate limit rule
rate_limiter.add_rule(
    "custom_operation",
    RateLimitRule(max_requests=10, window=RateLimitWindow.MINUTE)
)

# Check and record a request
result = rate_limiter.check_and_record("message", user_id)
if not result.allowed:
    print(f"Rate limited. Retry after {result.retry_after_seconds}s")
```

### Input Sanitization

```python
from app.services.setup_chatbot import input_sanitizer

# Sanitize user input
clean_text = input_sanitizer.sanitize_text(user_input)

# Detect potential injection attacks
injections = input_sanitizer.detect_injection(user_input)
if injections:
    print(f"Detected: {injections}")
```

### Audit Logging

```python
from app.services.setup_chatbot import audit_logger, AuditEventType

# Log an event
audit_logger.log(
    event_type=AuditEventType.CONNECTION_CREATED,
    tenant_id="tenant_123",
    user_id="user_456",
    resource_type="connection",
    resource_id="conn_789",
    action="create",
    details={"plugin": "github"},
)

# Get recent security events
security_events = audit_logger.get_security_events(since=datetime.now() - timedelta(hours=24))
```

### Credential Encryption

```python
from app.services.setup_chatbot import credential_store, connection_credential_manager

# Store encrypted credentials
connection_credential_manager.store_connection_credentials(
    tenant_id="tenant_123",
    connection_id="conn_789",
    credentials={"token": "ghp_xxxxx", "secret": "my_secret"},
    expires_in_days=365,
)

# Retrieve decrypted credentials
creds = connection_credential_manager.retrieve_connection_credentials(
    tenant_id="tenant_123",
    connection_id="conn_789",
    field_names=["token", "secret"],
)
```

## Analytics Usage

### Conversation Analytics

```python
from app.services.setup_chatbot import conversation_analytics, get_analytics_dashboard

# Get aggregate stats
stats = conversation_analytics.get_aggregate_stats(hours=24)
print(f"Completion rate: {stats['flow_completion_rate']}%")

# Get flow funnel
funnel = conversation_analytics.get_flow_funnel("connection", hours=24)
print(f"Drop-off rate: {funnel['drop_off_rate']}%")

# Get full dashboard data
dashboard = get_analytics_dashboard(hours=24)
```

### User Feedback

```python
from app.services.setup_chatbot import feedback_collector, FeedbackType, FeedbackSentiment

# Collect feedback
feedback_collector.submit_feedback(
    session_id="session_123",
    feedback_type=FeedbackType.HELPFUL,
    sentiment=FeedbackSentiment.POSITIVE,
    rating=5,
    comment="Very helpful!",
)

# Get feedback summary
summary = feedback_collector.get_feedback_summary(hours=24)
print(f"Average rating: {summary['average_rating']}")
```

### Performance Monitoring

```python
from app.services.setup_chatbot import performance_monitor

# Get current metrics
metrics = performance_monitor.get_metrics()
print(f"P95 response time: {metrics.p95_response_time_ms}ms")

# Health check
is_healthy, issues = performance_monitor.is_healthy()
if not is_healthy:
    print(f"Issues: {issues}")
```

## Smart Validation

### Token Validation

```python
from app.services.setup_chatbot import TokenValidator

validator = TokenValidator(expected_plugin="github")
result = validator.validate("ghp_xxxxxxxxxxxx", "token")

if not result.is_valid:
    for issue in result.issues:
        print(f"{issue.severity}: {issue.message}")

# Get detected token type
print(result.suggestions)  # ["Detected: Classic GitHub Personal Access Token"]
```

### URL Validation

```python
from app.services.setup_chatbot import UrlValidator

validator = UrlValidator(require_https=True, plugin_hint="gitlab")
result = validator.validate("gitlab.company.com", "endpoint")

# Auto-fixes applied
print(result.normalized_value)  # "https://gitlab.company.com"
print(result.suggestions)  # ["Added scheme to make: https://gitlab.company.com"]
```

### Smart Suggestions

```python
from app.services.setup_chatbot import suggestion_engine

# Get field suggestions
suggestions = suggestion_engine.get_suggestions_for_field(
    field_type="name",
    partial_value="",
    context={"item_type": "connection", "plugin": "GitHub"},
)
# ["Production GitHub", "Development GitHub", "Main GitHub"]

# Auto-correct input
corrected, changes = suggestion_engine.auto_correct("url", "gitlab.com/api")
print(corrected)  # "https://gitlab.com/api"
print(changes)  # ["Added scheme to make: https://gitlab.com/api"]
```

## Future Improvements

1. **Voice Input** - Speech-to-text for hands-free setup
2. **Proactive Suggestions** - AI-powered recommendations based on usage
3. **Batch Operations** - Configure multiple connections at once
4. **Templates** - Save and reuse configuration templates
5. **Webhooks** - Notify external systems on setup completion
6. **LLM-powered Error Analysis** - AI-assisted troubleshooting
7. **Credential Rotation** - Automated token refresh and rotation
8. **Multi-language Support** - Internationalized chatbot responses
