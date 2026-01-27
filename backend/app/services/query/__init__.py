"""Query Gateway for unified data access.

This module provides:
- Unified query interface for dashboards
- Cross-store data aggregation
- Tenant-scoped queries
- Caching and optimization
"""

from app.services.query.models import (
    QueryRequest,
    QueryResponse,
    DataSource,
    DashboardQuery,
)
from app.services.query.gateway import QueryGateway, get_query_gateway

__all__ = [
    # Models
    "QueryRequest",
    "QueryResponse",
    "DataSource",
    "DashboardQuery",
    # Gateway
    "QueryGateway",
    "get_query_gateway",
]
