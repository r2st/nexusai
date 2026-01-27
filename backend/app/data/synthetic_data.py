"""
Synthetic Data Provider for NexusAI

Provides pre-generated synthetic data for development and demo purposes.
This allows the application to function without connecting to LLMs.
"""

import random
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4


# =============================================================================
# AI Models Configuration
# =============================================================================

AI_MODELS = [
    {"id": "gpt-4", "provider": "openai", "name": "GPT-4", "cost_per_1k_input": 0.03, "cost_per_1k_output": 0.06},
    {"id": "gpt-4-turbo", "provider": "openai", "name": "GPT-4 Turbo", "cost_per_1k_input": 0.01, "cost_per_1k_output": 0.03},
    {"id": "gpt-3.5-turbo", "provider": "openai", "name": "GPT-3.5 Turbo", "cost_per_1k_input": 0.0005, "cost_per_1k_output": 0.0015},
    {"id": "claude-3-opus", "provider": "anthropic", "name": "Claude 3 Opus", "cost_per_1k_input": 0.015, "cost_per_1k_output": 0.075},
    {"id": "claude-3-sonnet", "provider": "anthropic", "name": "Claude 3 Sonnet", "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015},
    {"id": "claude-3-haiku", "provider": "anthropic", "name": "Claude 3 Haiku", "cost_per_1k_input": 0.00025, "cost_per_1k_output": 0.00125},
]


# =============================================================================
# Synthetic Response Templates
# =============================================================================

SYNTHETIC_RESPONSES = {
    "greeting": [
        "Hello! I'm NexusAI, your intelligent assistant. How can I help you today?",
        "Hi there! I'm ready to help you with any questions or tasks. What would you like to explore?",
        "Welcome! I'm here to assist you with analysis, research, or any questions you might have.",
    ],
    "analysis": [
        """Based on my analysis of the data you've provided, here are the key findings:

**Summary:**
- Overall performance has improved by 15% compared to the previous period
- Key metrics show positive trends across all departments
- Three areas require attention for further optimization

**Detailed Findings:**

1. **Revenue Growth**: Q3 shows a 12% increase in revenue, primarily driven by the new product line launch and expanded market presence in APAC.

2. **Customer Satisfaction**: NPS scores have improved from 42 to 47, indicating stronger customer loyalty and satisfaction with recent service improvements.

3. **Operational Efficiency**: Process automation has reduced manual tasks by 30%, leading to cost savings of approximately $150,000 annually.

**Recommendations:**
- Continue investment in the top-performing product categories
- Expand the customer success team to maintain satisfaction levels
- Implement additional automation in the identified bottleneck areas

Would you like me to dive deeper into any specific area?""",

        """Here's a comprehensive analysis of the information:

**Executive Summary:**
The data reveals several important trends that warrant attention from leadership.

**Key Metrics:**
| Metric | Current | Previous | Change |
|--------|---------|----------|--------|
| Active Users | 1,247 | 1,089 | +14.5% |
| Engagement Rate | 68% | 62% | +6% |
| Conversion | 3.2% | 2.8% | +14.3% |

**Insights:**
1. User engagement has significantly improved following the UX updates
2. Mobile users show 25% higher engagement than desktop users
3. Peak activity occurs between 10 AM - 2 PM and 7 PM - 9 PM

**Action Items:**
- Optimize mobile experience further based on user feedback
- Schedule important communications during peak hours
- A/B test new features with the high-engagement user segment

Is there a specific aspect you'd like me to elaborate on?""",
    ],
    "summary": [
        """**Document Summary**

This document covers the following key topics:

1. **Strategic Objectives** - Outlines the company's goals for the upcoming fiscal year, focusing on market expansion and product innovation.

2. **Financial Projections** - Presents revenue forecasts showing expected 20% growth, with detailed breakdowns by region and product line.

3. **Risk Assessment** - Identifies potential challenges including supply chain volatility and competitive pressures.

4. **Action Plan** - Defines specific initiatives, timelines, and responsible teams for achieving stated objectives.

**Key Takeaways:**
- Aggressive growth targets require increased investment in sales and marketing
- Diversification strategy to reduce dependency on single market
- Technology infrastructure upgrades planned for Q2

Would you like me to extract specific sections or provide more detail on any topic?""",
    ],
    "code": [
        """Here's a solution for your request:

```python
from typing import List, Dict, Any
from datetime import datetime

class DataAnalyzer:
    \"\"\"A class to analyze and process data efficiently.\"\"\"

    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.processed_at = datetime.now()

    def calculate_metrics(self) -> Dict[str, float]:
        \"\"\"Calculate key metrics from the data.\"\"\"
        if not self.data:
            return {}

        values = [item.get('value', 0) for item in self.data]
        return {
            'count': len(values),
            'sum': sum(values),
            'average': sum(values) / len(values) if values else 0,
            'min': min(values) if values else 0,
            'max': max(values) if values else 0,
        }

    def filter_by_threshold(self, threshold: float) -> List[Dict[str, Any]]:
        \"\"\"Filter data items above the specified threshold.\"\"\"
        return [item for item in self.data if item.get('value', 0) > threshold]

# Example usage
analyzer = DataAnalyzer(sample_data)
metrics = analyzer.calculate_metrics()
print(f"Analysis complete: {metrics}")
```

This implementation provides:
- Type hints for better code clarity
- Docstrings for documentation
- Efficient data processing methods
- Easy extensibility for additional metrics

Would you like me to add any additional functionality or explain any part of the code?""",
    ],
    "general": [
        """That's a great question! Let me provide you with a comprehensive answer.

**Overview:**
Based on the context and information available, here are the key points to consider:

1. **Context**: Understanding the background helps frame the appropriate approach
2. **Considerations**: Several factors influence the optimal solution
3. **Recommendations**: Specific actions based on best practices

**Details:**

The approach you should take depends on your specific goals and constraints. Here are some options to consider:

- **Option A**: Best for quick implementation with minimal resources
- **Option B**: Provides more flexibility but requires additional setup
- **Option C**: Most comprehensive solution for long-term scalability

**Next Steps:**
1. Define your primary objective clearly
2. Assess available resources and timeline
3. Choose the approach that best aligns with your constraints

Feel free to ask if you'd like me to elaborate on any of these points or explore a specific direction!""",
    ],
    "error_handling": [
        "I apologize, but I couldn't process that request. Could you please provide more details or rephrase your question?",
        "I'm not quite sure I understood your request correctly. Could you elaborate on what you're looking for?",
    ]
}


# =============================================================================
# Analytics Data Generator
# =============================================================================

def generate_analytics_snapshot() -> dict[str, Any]:
    """Generate a real-time analytics snapshot."""
    now = datetime.now()

    return {
        "timestamp": now.isoformat(),
        "real_time": {
            "active_users": random.randint(45, 120),
            "requests_per_minute": random.randint(50, 200),
            "avg_response_time_ms": random.randint(400, 1200),
            "error_rate": round(random.uniform(0, 0.02), 4),
        },
        "today": {
            "total_conversations": random.randint(200, 500),
            "total_messages": random.randint(1000, 3000),
            "tokens_used": random.randint(500000, 1500000),
            "documents_processed": random.randint(10, 50),
            "unique_users": random.randint(50, 150),
        },
        "trends": {
            "conversations_vs_yesterday": round(random.uniform(-10, 20), 1),
            "tokens_vs_yesterday": round(random.uniform(-5, 25), 1),
            "users_vs_yesterday": round(random.uniform(-5, 15), 1),
        },
        "model_distribution": {
            "gpt-4": round(random.uniform(20, 35), 1),
            "gpt-4-turbo": round(random.uniform(25, 40), 1),
            "claude-3-sonnet": round(random.uniform(15, 25), 1),
            "gpt-3.5-turbo": round(random.uniform(10, 20), 1),
        },
        "top_users": [
            {"name": "John Smith", "conversations": random.randint(10, 50), "tokens": random.randint(50000, 200000)},
            {"name": "Sarah Johnson", "conversations": random.randint(8, 40), "tokens": random.randint(40000, 150000)},
            {"name": "Mike Chen", "conversations": random.randint(5, 30), "tokens": random.randint(30000, 100000)},
        ],
    }


def generate_usage_chart_data(days: int = 30) -> list[dict[str, Any]]:
    """Generate usage chart data for the specified number of days."""
    data = []
    base_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        current_date = base_date + timedelta(days=i)
        day_of_week = current_date.weekday()

        # Simulate weekly patterns
        base_value = 1000 if day_of_week < 5 else 400
        growth = 1 + (i / days) * 0.2  # 20% growth trend

        data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "conversations": int(base_value * growth * random.uniform(0.8, 1.2)),
            "messages": int(base_value * 5 * growth * random.uniform(0.8, 1.2)),
            "tokens": int(base_value * 500 * growth * random.uniform(0.8, 1.2)),
            "users": int(base_value / 20 * growth * random.uniform(0.8, 1.2)),
        })

    return data


def generate_cost_breakdown() -> dict[str, Any]:
    """Generate cost breakdown by model and category."""
    return {
        "period": "last_30_days",
        "total_cost_usd": round(random.uniform(500, 2000), 2),
        "by_model": [
            {"model": "GPT-4", "cost": round(random.uniform(200, 600), 2), "percentage": round(random.uniform(25, 35), 1)},
            {"model": "GPT-4 Turbo", "cost": round(random.uniform(150, 400), 2), "percentage": round(random.uniform(20, 30), 1)},
            {"model": "Claude 3 Sonnet", "cost": round(random.uniform(100, 300), 2), "percentage": round(random.uniform(15, 25), 1)},
            {"model": "GPT-3.5 Turbo", "cost": round(random.uniform(50, 150), 2), "percentage": round(random.uniform(5, 15), 1)},
            {"model": "Claude 3 Haiku", "cost": round(random.uniform(20, 80), 2), "percentage": round(random.uniform(3, 8), 1)},
        ],
        "by_category": [
            {"category": "Chat Completions", "cost": round(random.uniform(400, 1200), 2), "percentage": 65},
            {"category": "Document Processing", "cost": round(random.uniform(100, 400), 2), "percentage": 20},
            {"category": "Embeddings", "cost": round(random.uniform(50, 200), 2), "percentage": 10},
            {"category": "Other", "cost": round(random.uniform(20, 100), 2), "percentage": 5},
        ],
        "projected_monthly": round(random.uniform(600, 2500), 2),
        "budget_used_percentage": round(random.uniform(40, 85), 1),
    }


# =============================================================================
# Synthetic Chat Response Generator
# =============================================================================

class SyntheticChatProvider:
    """Provides synthetic chat responses for demo/development mode."""

    def __init__(self, latency_ms: tuple[int, int] = (200, 1500)):
        self.min_latency = latency_ms[0]
        self.max_latency = latency_ms[1]

    def classify_query(self, query: str) -> str:
        """Classify the query type based on keywords."""
        query_lower = query.lower()

        if any(word in query_lower for word in ["hello", "hi", "hey", "greetings"]):
            return "greeting"
        elif any(word in query_lower for word in ["analyze", "analysis", "metrics", "performance", "data"]):
            return "analysis"
        elif any(word in query_lower for word in ["summarize", "summary", "tldr", "overview"]):
            return "summary"
        elif any(word in query_lower for word in ["code", "function", "implement", "script", "program"]):
            return "code"
        else:
            return "general"

    def generate_response(self, query: str, model: str = "gpt-4") -> dict[str, Any]:
        """Generate a synthetic response for the given query."""
        query_type = self.classify_query(query)
        responses = SYNTHETIC_RESPONSES.get(query_type, SYNTHETIC_RESPONSES["general"])
        response_text = random.choice(responses)

        # Calculate synthetic token counts
        input_tokens = len(query.split()) * 1.3  # Rough estimate
        output_tokens = len(response_text.split()) * 1.3

        # Find model info
        model_info = next((m for m in AI_MODELS if m["id"] == model), AI_MODELS[0])

        # Calculate cost
        input_cost = (input_tokens / 1000) * model_info["cost_per_1k_input"]
        output_cost = (output_tokens / 1000) * model_info["cost_per_1k_output"]

        return {
            "id": str(uuid4()),
            "model": model,
            "content": response_text,
            "role": "assistant",
            "created_at": datetime.now().isoformat(),
            "usage": {
                "prompt_tokens": int(input_tokens),
                "completion_tokens": int(output_tokens),
                "total_tokens": int(input_tokens + output_tokens),
            },
            "cost": {
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6),
                "total_cost": round(input_cost + output_cost, 6),
            },
            "latency_ms": random.randint(self.min_latency, self.max_latency),
            "synthetic": True,  # Flag to indicate this is synthetic data
        }

    async def generate_streaming_response(self, query: str, model: str = "gpt-4"):
        """Generate a streaming synthetic response (async generator)."""
        import asyncio

        query_type = self.classify_query(query)
        responses = SYNTHETIC_RESPONSES.get(query_type, SYNTHETIC_RESPONSES["general"])
        response_text = random.choice(responses)

        # Split into chunks for streaming
        words = response_text.split()
        chunk_size = random.randint(3, 8)

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i > 0:
                chunk = " " + chunk

            yield {
                "content": chunk,
                "done": i + chunk_size >= len(words),
            }

            # Simulate streaming delay
            await asyncio.sleep(random.uniform(0.02, 0.08))


# =============================================================================
# Dashboard Data
# =============================================================================

def generate_dashboard_data() -> dict[str, Any]:
    """Generate comprehensive dashboard data."""
    return {
        "overview": {
            "total_users": random.randint(100, 500),
            "active_users_today": random.randint(30, 100),
            "total_conversations": random.randint(5000, 20000),
            "total_documents": random.randint(500, 2000),
            "tokens_used_month": random.randint(2000000, 10000000),
            "cost_month_usd": round(random.uniform(500, 3000), 2),
        },
        "changes": {
            "users": round(random.uniform(5, 25), 1),
            "conversations": round(random.uniform(-5, 30), 1),
            "tokens": round(random.uniform(0, 40), 1),
            "cost": round(random.uniform(-10, 20), 1),
        },
        "charts": {
            "usage_trend": generate_usage_chart_data(30),
            "model_distribution": [
                {"name": "GPT-4", "value": random.randint(20, 35)},
                {"name": "GPT-4 Turbo", "value": random.randint(25, 40)},
                {"name": "Claude 3 Sonnet", "value": random.randint(15, 25)},
                {"name": "GPT-3.5 Turbo", "value": random.randint(10, 20)},
            ],
            "hourly_requests": [
                {"hour": h, "requests": random.randint(10, 200) if 8 <= h <= 20 else random.randint(0, 30)}
                for h in range(24)
            ],
        },
        "recent_activity": [
            {
                "id": str(uuid4()),
                "type": random.choice(["conversation", "document", "user"]),
                "action": random.choice(["created", "updated", "completed"]),
                "description": f"User {random.choice(['started a new conversation', 'uploaded a document', 'generated a report'])}",
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 120))).isoformat(),
                "user": random.choice(["John Smith", "Sarah Johnson", "Mike Chen", "Emily Davis"]),
            }
            for _ in range(10)
        ],
        "alerts": [
            {
                "id": str(uuid4()),
                "severity": "warning",
                "message": "Token usage at 75% of monthly limit",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "id": str(uuid4()),
                "severity": "info",
                "message": "New model Claude 3.5 Sonnet available",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            },
        ],
        "generated_at": datetime.now().isoformat(),
        "is_synthetic": True,
    }


# =============================================================================
# Singleton Instance
# =============================================================================

# Global synthetic chat provider
synthetic_chat = SyntheticChatProvider()


def get_synthetic_response(query: str, model: str = "gpt-4") -> dict[str, Any]:
    """Convenience function to get a synthetic response."""
    return synthetic_chat.generate_response(query, model)


def is_synthetic_mode() -> bool:
    """Check if the application is running in synthetic/demo mode."""
    import os
    return os.getenv("SYNTHETIC_MODE", "false").lower() in ("true", "1", "yes")
