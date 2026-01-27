# AI Analytics Data Flow and Schema

## Overview

NexusAI tracks AI tool usage, code generation metrics, and ROI to provide insights into AI adoption and effectiveness.

## Data Flow

### 1. Event Collection

AI tool usage events are collected from:
- Chat interactions (LLM calls)
- Code generation tools
- AI-powered agents
- Document processing
- Image generation

### 2. Event Processing

Events are processed and stored:
- Real-time event ingestion
- Metric aggregation
- ROI calculations
- Trend analysis

### 3. Analytics Generation

Analytics are generated:
- AI-powered insights
- Natural language summaries
- ROI reports
- Adoption metrics

## Data Schema

### AIAnalyticsMetric

**Location**: `backend/app/models/ai_analytics.py`

```python
class AIAnalyticsMetric(Base):
    id: str
    tenant_id: str
    project_id: str | None
    user_id: str
    tool_name: str  # e.g., "chat", "code_generation", "image_generation"
    provider: str  # e.g., "openai", "anthropic", "google"
    model: str  # e.g., "gpt-4o", "claude-3-sonnet"
    operation: str  # e.g., "chat", "completion", "embedding"
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    success: bool
    error: str | None
    metadata: dict
    created_at: datetime
```

### AIROIMetric

**Location**: `backend/app/models/ai_analytics.py`

```python
class AIROIMetric(Base):
    id: str
    tenant_id: str
    project_id: str | None
    period_start: datetime
    period_end: datetime
    total_cost_usd: float
    time_saved_hours: float
    productivity_gain_percent: float
    estimated_value_usd: float
    roi_percent: float
    adoption_rate: float
    active_users: int
    total_requests: int
    created_at: datetime
```

## Services

### 1. AI Analytics Service

**Location**: `backend/app/services/ai_analytics/base.py`

Provides:
- Metric collection
- Aggregation
- Querying
- Reporting

### 2. ROI Service

**Location**: `backend/app/services/ai_analytics/roi.py`

Calculates:
- Time saved
- Productivity gains
- Cost vs. value
- ROI percentage

### 3. Summary Service

**Location**: `backend/app/services/ai_analytics/summary.py`

Generates:
- AI-powered summaries
- Key insights
- Recommendations
- Trend analysis

## Metrics Tracked

### 1. Usage Metrics

- Total requests
- Requests per user
- Requests per project
- Tool adoption rate
- Active users

### 2. Performance Metrics

- Average latency
- Success rate
- Error rate
- Token usage
- Cost per request

### 3. ROI Metrics

- Time saved (hours)
- Productivity gain (%)
- Cost savings
- Estimated value
- ROI percentage

## Data Flow Diagram

```
User Action
    ↓
Event Collection
    ↓
Metric Storage (AIAnalyticsMetric)
    ↓
Aggregation (hourly/daily)
    ↓
ROI Calculation (AIROIMetric)
    ↓
AI Summary Generation
    ↓
Dashboard Display
```

## API Endpoints

### Get Analytics

```http
GET /api/v1/analytics/ai
```

Returns:
- Usage metrics
- Performance metrics
- ROI metrics
- Trends

### Get ROI Report

```http
GET /api/v1/analytics/ai/roi
```

Returns:
- ROI calculations
- Time saved
- Productivity gains
- Cost analysis

### Get Summary

```http
GET /api/v1/analytics/ai/summary
```

Returns:
- AI-generated summary
- Key insights
- Recommendations

## Integration Points

### 1. Chat Service

Tracks LLM usage:

```python
from app.services.ai_analytics import record_usage

await record_usage(
    user_id=user_id,
    tool_name="chat",
    provider="openai",
    model="gpt-4o",
    input_tokens=100,
    output_tokens=50,
    cost_usd=0.001
)
```

### 2. Code Generation

Tracks code generation:

```python
await record_usage(
    user_id=user_id,
    tool_name="code_generation",
    provider="anthropic",
    model="claude-3-sonnet",
    input_tokens=500,
    output_tokens=1000,
    cost_usd=0.01
)
```

## Dashboards

### 1. Usage Dashboard

- Total requests over time
- Requests by tool
- Requests by user
- Adoption trends

### 2. Performance Dashboard

- Average latency
- Success rate
- Error rate
- Token usage

### 3. ROI Dashboard

- Time saved
- Productivity gains
- Cost vs. value
- ROI trends

## Data Retention

- Raw metrics: 90 days
- Aggregated metrics: 1 year
- ROI reports: 2 years
- Summaries: 1 year

## Privacy Considerations

- User data is anonymized in reports
- Project-level aggregation
- Tenant isolation enforced
- GDPR compliant
