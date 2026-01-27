#!/usr/bin/env python3
"""
Synthetic Data Generator for NexusAI

Generates realistic test data for the platform including:
- Users and organizations
- Conversations and messages
- Documents and embeddings
- AI analytics and metrics
- API usage statistics

Usage:
    python scripts/generate_synthetic_data.py [--output-dir ./data] [--seed 42]
"""

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Try to import faker, fall back to basic generation if not available
try:
    from faker import Faker
    fake = Faker()
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False
    print("Warning: Faker not installed. Using basic data generation.")


# =============================================================================
# Constants
# =============================================================================

AI_MODELS = [
    {"id": "gpt-4", "provider": "openai", "name": "GPT-4", "cost_per_1k_input": 0.03, "cost_per_1k_output": 0.06},
    {"id": "gpt-4-turbo", "provider": "openai", "name": "GPT-4 Turbo", "cost_per_1k_input": 0.01, "cost_per_1k_output": 0.03},
    {"id": "gpt-3.5-turbo", "provider": "openai", "name": "GPT-3.5 Turbo", "cost_per_1k_input": 0.0005, "cost_per_1k_output": 0.0015},
    {"id": "claude-3-opus", "provider": "anthropic", "name": "Claude 3 Opus", "cost_per_1k_input": 0.015, "cost_per_1k_output": 0.075},
    {"id": "claude-3-sonnet", "provider": "anthropic", "name": "Claude 3 Sonnet", "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015},
    {"id": "claude-3-haiku", "provider": "anthropic", "name": "Claude 3 Haiku", "cost_per_1k_input": 0.00025, "cost_per_1k_output": 0.00125},
    {"id": "gemini-pro", "provider": "google", "name": "Gemini Pro", "cost_per_1k_input": 0.00025, "cost_per_1k_output": 0.0005},
]

DOCUMENT_TYPES = ["pdf", "docx", "txt", "md", "csv", "xlsx", "pptx", "html"]

CONVERSATION_TOPICS = [
    "quarterly sales analysis",
    "product roadmap planning",
    "customer feedback summary",
    "technical documentation review",
    "market research insights",
    "budget allocation review",
    "team performance metrics",
    "competitor analysis",
    "risk assessment report",
    "compliance audit findings",
    "project status update",
    "strategic planning discussion",
    "HR policy questions",
    "IT support troubleshooting",
    "marketing campaign analysis",
]

SAMPLE_QUESTIONS = [
    "What were the key findings from the Q3 report?",
    "Can you summarize the main points of this document?",
    "What are the risks identified in this analysis?",
    "How does this compare to last quarter's performance?",
    "What recommendations would you make based on this data?",
    "Can you explain the methodology used in this study?",
    "What are the action items from this meeting?",
    "How should we prioritize these tasks?",
    "What are the compliance requirements for this process?",
    "Can you identify any trends in this data?",
]

SAMPLE_RESPONSES = [
    "Based on my analysis of the document, the key findings include: 1) Revenue increased by 15% compared to Q2, 2) Customer acquisition costs decreased by 8%, and 3) Net promoter score improved from 42 to 47.",
    "The document outlines three main strategic priorities: expanding into new markets, improving operational efficiency, and enhancing customer experience through digital transformation.",
    "I've identified several potential risks: market volatility affecting Q4 projections, supply chain disruptions in the APAC region, and regulatory changes that may impact compliance requirements.",
    "Comparing to last quarter, we see significant improvements in most KPIs. Sales conversion rate is up 12%, average deal size increased by $15,000, and customer churn decreased from 5.2% to 4.1%.",
    "Based on the data analysis, I recommend: 1) Increasing investment in the top-performing product line, 2) Implementing automated follow-up sequences for leads, and 3) Expanding the customer success team.",
]

DEPARTMENT_NAMES = [
    "Engineering", "Sales", "Marketing", "Finance", "HR", "Operations",
    "Product", "Customer Success", "Legal", "Research", "Data Science"
]

PROJECT_NAMES = [
    "Project Alpha", "Customer Portal v2", "Data Migration", "API Redesign",
    "Mobile App Launch", "Security Audit", "Performance Optimization",
    "Documentation Update", "Integration Hub", "Analytics Dashboard"
]


# =============================================================================
# Helper Functions
# =============================================================================

def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_email(name: str) -> str:
    if HAS_FAKER:
        return fake.email()
    clean_name = name.lower().replace(" ", ".").replace("'", "")
    domains = ["nexusai.com", "example.com", "company.org", "corp.net"]
    return f"{clean_name}@{random.choice(domains)}"


def generate_name() -> str:
    if HAS_FAKER:
        return fake.name()
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


def generate_company_name() -> str:
    if HAS_FAKER:
        return fake.company()
    prefixes = ["Tech", "Global", "Smart", "Cloud", "Data", "Cyber", "Digital", "Quantum"]
    suffixes = ["Solutions", "Systems", "Corp", "Inc", "Labs", "Analytics", "Dynamics"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


def generate_sentence() -> str:
    if HAS_FAKER:
        return fake.sentence()
    subjects = ["The team", "Our analysis", "The report", "This data", "The findings"]
    verbs = ["shows", "indicates", "reveals", "suggests", "demonstrates"]
    objects = ["significant growth", "improvement potential", "key insights", "important trends", "actionable recommendations"]
    return f"{random.choice(subjects)} {random.choice(verbs)} {random.choice(objects)}."


def generate_paragraph() -> str:
    if HAS_FAKER:
        return fake.paragraph()
    return " ".join([generate_sentence() for _ in range(random.randint(3, 6))])


def random_datetime(start_days_ago: int = 90, end_days_ago: int = 0) -> datetime:
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def format_datetime(dt: datetime) -> str:
    return dt.isoformat()


# =============================================================================
# Data Generators
# =============================================================================

def generate_users(count: int = 50) -> list[dict[str, Any]]:
    """Generate synthetic user data."""
    users = []
    roles = ["admin", "user", "viewer"]
    role_weights = [0.1, 0.7, 0.2]

    for i in range(count):
        name = generate_name()
        created_at = random_datetime(180, 30)
        last_login = random_datetime(30, 0) if random.random() > 0.1 else None

        user = {
            "id": generate_uuid(),
            "email": generate_email(name),
            "full_name": name,
            "role": random.choices(roles, role_weights)[0],
            "department": random.choice(DEPARTMENT_NAMES),
            "is_active": random.random() > 0.05,
            "created_at": format_datetime(created_at),
            "last_login": format_datetime(last_login) if last_login else None,
            "preferences": {
                "theme": random.choice(["light", "dark", "system"]),
                "language": random.choice(["en", "es", "fr", "de"]),
                "notifications_enabled": random.random() > 0.2,
            },
            "usage_stats": {
                "total_conversations": random.randint(5, 500),
                "total_messages": random.randint(20, 5000),
                "total_documents_uploaded": random.randint(0, 100),
                "tokens_used_this_month": random.randint(1000, 500000),
            }
        }
        users.append(user)

    return users


def generate_organizations(count: int = 5) -> list[dict[str, Any]]:
    """Generate synthetic organization data."""
    organizations = []
    plans = ["free", "starter", "professional", "enterprise"]
    plan_weights = [0.1, 0.3, 0.4, 0.2]

    for i in range(count):
        name = generate_company_name()
        slug = name.lower().replace(" ", "-").replace(".", "")
        created_at = random_datetime(365, 60)

        org = {
            "id": generate_uuid(),
            "name": name,
            "slug": slug,
            "plan": random.choices(plans, plan_weights)[0],
            "created_at": format_datetime(created_at),
            "settings": {
                "allowed_models": random.sample([m["id"] for m in AI_MODELS], random.randint(2, 5)),
                "max_tokens_per_month": random.choice([100000, 500000, 1000000, 5000000, -1]),
                "max_documents": random.choice([100, 500, 1000, 5000, -1]),
                "sso_enabled": random.random() > 0.7,
                "audit_logging": random.random() > 0.5,
            },
            "usage": {
                "total_users": random.randint(5, 200),
                "active_users_30d": random.randint(3, 150),
                "tokens_used_this_month": random.randint(50000, 2000000),
                "documents_count": random.randint(50, 2000),
            }
        }
        organizations.append(org)

    return organizations


def generate_conversations(user_ids: list[str], count: int = 200) -> list[dict[str, Any]]:
    """Generate synthetic conversation data."""
    conversations = []

    for i in range(count):
        topic = random.choice(CONVERSATION_TOPICS)
        created_at = random_datetime(60, 0)
        message_count = random.randint(2, 30)

        conv = {
            "id": generate_uuid(),
            "user_id": random.choice(user_ids),
            "title": topic.title(),
            "model": random.choice(AI_MODELS)["id"],
            "created_at": format_datetime(created_at),
            "updated_at": format_datetime(created_at + timedelta(hours=random.randint(0, 48))),
            "message_count": message_count,
            "total_tokens": random.randint(500, 10000),
            "is_archived": random.random() > 0.9,
            "is_starred": random.random() > 0.85,
            "tags": random.sample(["important", "follow-up", "completed", "review", "urgent"], random.randint(0, 2)),
            "metadata": {
                "source": random.choice(["web", "api", "mobile", "slack"]),
                "project": random.choice(PROJECT_NAMES) if random.random() > 0.5 else None,
            }
        }
        conversations.append(conv)

    return conversations


def generate_messages(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate synthetic message data for conversations."""
    messages = []

    for conv in conversations:
        conv_messages = []
        num_messages = conv["message_count"]
        base_time = datetime.fromisoformat(conv["created_at"])

        for j in range(num_messages):
            is_user = j % 2 == 0
            msg_time = base_time + timedelta(minutes=j * random.randint(1, 5))

            if is_user:
                content = random.choice(SAMPLE_QUESTIONS)
                tokens = random.randint(20, 100)
            else:
                content = random.choice(SAMPLE_RESPONSES)
                tokens = random.randint(100, 500)

            message = {
                "id": generate_uuid(),
                "conversation_id": conv["id"],
                "role": "user" if is_user else "assistant",
                "content": content,
                "tokens": tokens,
                "created_at": format_datetime(msg_time),
                "metadata": {
                    "model": conv["model"] if not is_user else None,
                    "latency_ms": random.randint(200, 3000) if not is_user else None,
                }
            }
            conv_messages.append(message)

        messages.extend(conv_messages)

    return messages


def generate_documents(user_ids: list[str], count: int = 100) -> list[dict[str, Any]]:
    """Generate synthetic document data."""
    documents = []

    doc_names = [
        "Q{q} Financial Report 2024", "Product Roadmap", "Meeting Notes - {date}",
        "Customer Analysis", "Technical Specification", "Policy Document v{v}",
        "Training Manual", "Competitor Research", "Budget Proposal", "Project Plan",
        "Sales Forecast", "Market Analysis", "Risk Assessment", "Compliance Report",
        "User Research Findings", "API Documentation", "Security Audit", "Performance Review"
    ]

    for i in range(count):
        name_template = random.choice(doc_names)
        name = name_template.format(
            q=random.randint(1, 4),
            date=random_datetime(30, 0).strftime("%Y-%m-%d"),
            v=f"{random.randint(1, 5)}.{random.randint(0, 9)}"
        )
        doc_type = random.choice(DOCUMENT_TYPES)
        created_at = random_datetime(90, 0)

        doc = {
            "id": generate_uuid(),
            "name": f"{name}.{doc_type}",
            "type": doc_type,
            "size_bytes": random.randint(10000, 10000000),
            "uploaded_by": random.choice(user_ids),
            "created_at": format_datetime(created_at),
            "updated_at": format_datetime(created_at + timedelta(days=random.randint(0, 30))),
            "status": random.choices(["processed", "processing", "failed"], [0.9, 0.08, 0.02])[0],
            "chunk_count": random.randint(5, 100),
            "embedding_model": "text-embedding-3-small",
            "metadata": {
                "pages": random.randint(1, 50) if doc_type in ["pdf", "docx", "pptx"] else None,
                "word_count": random.randint(500, 20000),
                "language": "en",
                "tags": random.sample(["confidential", "public", "internal", "draft", "final"], random.randint(0, 2)),
            },
            "usage_stats": {
                "times_referenced": random.randint(0, 50),
                "last_referenced": format_datetime(random_datetime(7, 0)) if random.random() > 0.3 else None,
            }
        }
        documents.append(doc)

    return documents


def generate_analytics_daily(days: int = 90) -> list[dict[str, Any]]:
    """Generate daily analytics data."""
    analytics = []
    base_date = datetime.now() - timedelta(days=days)

    # Base values with growth trend
    base_active_users = 50
    base_conversations = 100
    base_messages = 500
    base_tokens = 50000

    for day in range(days):
        current_date = base_date + timedelta(days=day)

        # Add some growth trend and weekly patterns
        growth_factor = 1 + (day / days) * 0.3  # 30% growth over period
        day_of_week = current_date.weekday()
        weekend_factor = 0.4 if day_of_week >= 5 else 1.0

        # Add some randomness
        noise = random.uniform(0.8, 1.2)

        active_users = int(base_active_users * growth_factor * weekend_factor * noise)
        conversations = int(base_conversations * growth_factor * weekend_factor * noise)
        messages = int(base_messages * growth_factor * weekend_factor * noise)
        tokens = int(base_tokens * growth_factor * weekend_factor * noise)

        daily = {
            "date": current_date.strftime("%Y-%m-%d"),
            "metrics": {
                "active_users": active_users,
                "new_users": random.randint(0, int(active_users * 0.1)),
                "conversations_started": conversations,
                "messages_sent": messages,
                "tokens_used": tokens,
                "documents_uploaded": random.randint(0, 20),
                "api_calls": random.randint(100, 5000),
            },
            "model_usage": {
                model["id"]: {
                    "requests": random.randint(10, 500),
                    "tokens_input": random.randint(5000, 100000),
                    "tokens_output": random.randint(10000, 200000),
                    "avg_latency_ms": random.randint(300, 2000),
                    "error_rate": round(random.uniform(0, 0.05), 4),
                }
                for model in random.sample(AI_MODELS, random.randint(3, 5))
            },
            "costs": {
                "total_usd": round(random.uniform(10, 500), 2),
                "by_model": {
                    model["id"]: round(random.uniform(1, 100), 2)
                    for model in random.sample(AI_MODELS, random.randint(2, 4))
                }
            },
            "performance": {
                "avg_response_time_ms": random.randint(500, 2500),
                "p95_response_time_ms": random.randint(2000, 5000),
                "p99_response_time_ms": random.randint(4000, 10000),
                "error_count": random.randint(0, 20),
                "timeout_count": random.randint(0, 5),
            }
        }
        analytics.append(daily)

    return analytics


def generate_analytics_hourly(hours: int = 168) -> list[dict[str, Any]]:
    """Generate hourly analytics data (last 7 days)."""
    analytics = []
    base_time = datetime.now() - timedelta(hours=hours)

    for hour in range(hours):
        current_time = base_time + timedelta(hours=hour)
        hour_of_day = current_time.hour

        # Simulate daily patterns
        if 9 <= hour_of_day <= 17:  # Business hours
            activity_factor = 1.0
        elif 6 <= hour_of_day <= 9 or 17 <= hour_of_day <= 21:  # Before/after work
            activity_factor = 0.5
        else:  # Night time
            activity_factor = 0.1

        # Weekend reduction
        if current_time.weekday() >= 5:
            activity_factor *= 0.3

        hourly = {
            "timestamp": format_datetime(current_time),
            "requests": int(random.randint(10, 200) * activity_factor),
            "active_users": int(random.randint(5, 50) * activity_factor),
            "tokens_used": int(random.randint(5000, 50000) * activity_factor),
            "avg_latency_ms": random.randint(300, 1500),
            "error_rate": round(random.uniform(0, 0.03), 4),
        }
        analytics.append(hourly)

    return analytics


def generate_api_keys(org_ids: list[str], user_ids: list[str], count: int = 20) -> list[dict[str, Any]]:
    """Generate synthetic API keys."""
    api_keys = []

    for i in range(count):
        created_at = random_datetime(180, 0)
        last_used = random_datetime(7, 0) if random.random() > 0.2 else None

        key = {
            "id": generate_uuid(),
            "name": f"API Key - {random.choice(['Production', 'Development', 'Testing', 'Integration'])} {i+1}",
            "key_prefix": f"nxai_{uuid.uuid4().hex[:8]}",
            "organization_id": random.choice(org_ids),
            "created_by": random.choice(user_ids),
            "created_at": format_datetime(created_at),
            "last_used_at": format_datetime(last_used) if last_used else None,
            "expires_at": format_datetime(created_at + timedelta(days=365)) if random.random() > 0.3 else None,
            "is_active": random.random() > 0.1,
            "scopes": random.sample(["read", "write", "admin", "chat", "documents", "analytics"], random.randint(1, 4)),
            "rate_limit": random.choice([100, 500, 1000, 5000, None]),
            "usage": {
                "total_requests": random.randint(0, 100000),
                "requests_today": random.randint(0, 1000),
                "tokens_used_total": random.randint(0, 5000000),
            }
        }
        api_keys.append(key)

    return api_keys


def generate_audit_logs(user_ids: list[str], count: int = 500) -> list[dict[str, Any]]:
    """Generate synthetic audit log entries."""
    logs = []

    actions = [
        ("user.login", "User logged in"),
        ("user.logout", "User logged out"),
        ("conversation.create", "Created new conversation"),
        ("conversation.delete", "Deleted conversation"),
        ("document.upload", "Uploaded document"),
        ("document.delete", "Deleted document"),
        ("api_key.create", "Created API key"),
        ("api_key.revoke", "Revoked API key"),
        ("settings.update", "Updated settings"),
        ("user.invite", "Invited user"),
        ("export.data", "Exported data"),
    ]

    for i in range(count):
        action, description = random.choice(actions)
        timestamp = random_datetime(30, 0)

        log = {
            "id": generate_uuid(),
            "timestamp": format_datetime(timestamp),
            "user_id": random.choice(user_ids),
            "action": action,
            "description": description,
            "ip_address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            "user_agent": random.choice([
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Mozilla/5.0 (X11; Linux x86_64)",
                "NexusAI-SDK/1.0.0",
            ]),
            "metadata": {
                "resource_id": generate_uuid() if random.random() > 0.5 else None,
                "resource_type": action.split(".")[0],
            }
        }
        logs.append(log)

    # Sort by timestamp
    logs.sort(key=lambda x: x["timestamp"], reverse=True)

    return logs


def generate_model_performance_data() -> list[dict[str, Any]]:
    """Generate AI model performance comparison data."""
    performance_data = []

    for model in AI_MODELS:
        perf = {
            "model_id": model["id"],
            "model_name": model["name"],
            "provider": model["provider"],
            "pricing": {
                "input_per_1k": model["cost_per_1k_input"],
                "output_per_1k": model["cost_per_1k_output"],
            },
            "performance": {
                "avg_latency_ms": random.randint(500, 3000),
                "p50_latency_ms": random.randint(400, 2000),
                "p95_latency_ms": random.randint(2000, 6000),
                "p99_latency_ms": random.randint(4000, 10000),
                "throughput_rpm": random.randint(50, 500),
            },
            "quality_metrics": {
                "accuracy_score": round(random.uniform(0.85, 0.98), 3),
                "relevance_score": round(random.uniform(0.80, 0.95), 3),
                "coherence_score": round(random.uniform(0.85, 0.98), 3),
                "helpfulness_rating": round(random.uniform(4.0, 5.0), 2),
            },
            "usage_stats": {
                "total_requests_30d": random.randint(1000, 100000),
                "total_tokens_30d": random.randint(500000, 10000000),
                "unique_users_30d": random.randint(10, 200),
                "error_rate_30d": round(random.uniform(0.001, 0.02), 4),
            }
        }
        performance_data.append(perf)

    return performance_data


def generate_dashboard_summary(
    users: list[dict],
    conversations: list[dict],
    documents: list[dict],
    daily_analytics: list[dict]
) -> dict[str, Any]:
    """Generate dashboard summary data."""

    # Calculate totals from recent analytics
    recent_analytics = daily_analytics[-30:]  # Last 30 days

    total_tokens = sum(d["metrics"]["tokens_used"] for d in recent_analytics)
    total_messages = sum(d["metrics"]["messages_sent"] for d in recent_analytics)
    total_cost = sum(d["costs"]["total_usd"] for d in recent_analytics)

    # Previous period for comparison
    prev_analytics = daily_analytics[-60:-30] if len(daily_analytics) >= 60 else daily_analytics[:30]
    prev_tokens = sum(d["metrics"]["tokens_used"] for d in prev_analytics)
    prev_messages = sum(d["metrics"]["messages_sent"] for d in prev_analytics)
    prev_cost = sum(d["costs"]["total_usd"] for d in prev_analytics)

    def calc_change(current: float, previous: float) -> float:
        if previous == 0:
            return 0
        return round(((current - previous) / previous) * 100, 1)

    return {
        "summary": {
            "total_users": len(users),
            "active_users_30d": len([u for u in users if u["is_active"]]),
            "total_conversations": len(conversations),
            "total_documents": len(documents),
            "total_tokens_30d": total_tokens,
            "total_messages_30d": total_messages,
            "total_cost_30d": round(total_cost, 2),
        },
        "changes": {
            "users_change": calc_change(len(users), len(users) * 0.9),
            "conversations_change": calc_change(len(conversations), len(conversations) * 0.85),
            "tokens_change": calc_change(total_tokens, prev_tokens),
            "messages_change": calc_change(total_messages, prev_messages),
            "cost_change": calc_change(total_cost, prev_cost),
        },
        "top_models": sorted(
            [
                {
                    "model": model["name"],
                    "requests": random.randint(1000, 50000),
                    "tokens": random.randint(100000, 2000000),
                    "cost": round(random.uniform(50, 500), 2),
                }
                for model in AI_MODELS[:5]
            ],
            key=lambda x: x["requests"],
            reverse=True
        ),
        "recent_activity": [
            {
                "type": random.choice(["conversation", "document", "api_call"]),
                "description": generate_sentence(),
                "timestamp": format_datetime(random_datetime(1, 0)),
                "user": generate_name(),
            }
            for _ in range(10)
        ],
        "alerts": [
            {
                "id": generate_uuid(),
                "severity": random.choice(["info", "warning", "error"]),
                "message": random.choice([
                    "Token usage approaching monthly limit",
                    "New model version available",
                    "Scheduled maintenance in 24 hours",
                    "API rate limit reached for 2 users",
                    "Document processing queue is high",
                ]),
                "timestamp": format_datetime(random_datetime(3, 0)),
            }
            for _ in range(random.randint(0, 5))
        ],
        "generated_at": format_datetime(datetime.now()),
    }


# =============================================================================
# Main Generator
# =============================================================================

def generate_all_data(seed: int = 42) -> dict[str, Any]:
    """Generate all synthetic data."""
    random.seed(seed)
    if HAS_FAKER:
        Faker.seed(seed)

    print("Generating synthetic data...")

    # Generate base data
    print("  - Generating users...")
    users = generate_users(50)
    user_ids = [u["id"] for u in users]

    print("  - Generating organizations...")
    organizations = generate_organizations(5)
    org_ids = [o["id"] for o in organizations]

    print("  - Generating conversations...")
    conversations = generate_conversations(user_ids, 200)

    print("  - Generating messages...")
    messages = generate_messages(conversations)

    print("  - Generating documents...")
    documents = generate_documents(user_ids, 100)

    print("  - Generating daily analytics...")
    daily_analytics = generate_analytics_daily(90)

    print("  - Generating hourly analytics...")
    hourly_analytics = generate_analytics_hourly(168)

    print("  - Generating API keys...")
    api_keys = generate_api_keys(org_ids, user_ids, 20)

    print("  - Generating audit logs...")
    audit_logs = generate_audit_logs(user_ids, 500)

    print("  - Generating model performance data...")
    model_performance = generate_model_performance_data()

    print("  - Generating dashboard summary...")
    dashboard = generate_dashboard_summary(users, conversations, documents, daily_analytics)

    return {
        "users": users,
        "organizations": organizations,
        "conversations": conversations,
        "messages": messages,
        "documents": documents,
        "analytics_daily": daily_analytics,
        "analytics_hourly": hourly_analytics,
        "api_keys": api_keys,
        "audit_logs": audit_logs,
        "model_performance": model_performance,
        "dashboard": dashboard,
        "ai_models": AI_MODELS,
        "metadata": {
            "generated_at": format_datetime(datetime.now()),
            "seed": seed,
            "counts": {
                "users": len(users),
                "organizations": len(organizations),
                "conversations": len(conversations),
                "messages": len(messages),
                "documents": len(documents),
                "api_keys": len(api_keys),
                "audit_logs": len(audit_logs),
            }
        }
    }


def save_data(data: dict[str, Any], output_dir: str) -> None:
    """Save generated data to JSON files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save individual files
    for key, value in data.items():
        if key == "metadata":
            continue

        file_path = output_path / f"{key}.json"
        with open(file_path, "w") as f:
            json.dump(value, f, indent=2)
        print(f"  - Saved {file_path}")

    # Save combined file
    combined_path = output_path / "all_data.json"
    with open(combined_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  - Saved {combined_path}")

    # Save metadata
    metadata_path = output_path / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(data["metadata"], f, indent=2)
    print(f"  - Saved {metadata_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic data for NexusAI")
    parser.add_argument("--output-dir", "-o", default="./data/synthetic", help="Output directory for generated data")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    data = generate_all_data(args.seed)

    print(f"\nSaving data to {args.output_dir}...")
    save_data(data, args.output_dir)

    print(f"\n✅ Synthetic data generation complete!")
    print(f"   Generated {data['metadata']['counts']['users']} users")
    print(f"   Generated {data['metadata']['counts']['organizations']} organizations")
    print(f"   Generated {data['metadata']['counts']['conversations']} conversations")
    print(f"   Generated {data['metadata']['counts']['messages']} messages")
    print(f"   Generated {data['metadata']['counts']['documents']} documents")
    print(f"   Generated 90 days of daily analytics")
    print(f"   Generated 168 hours of hourly analytics")


if __name__ == "__main__":
    main()
