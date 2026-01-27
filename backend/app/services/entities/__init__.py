"""Entity service for canonical domain model.

This module provides:
- Canonical entity models (Repo, Commit, PR, Build, Deploy, Incident, Service, Team)
- Entity store with tenant isolation
- Identity resolution across sources
- Source-specific normalizers
"""

from app.services.entities.models import (
    # Base
    Entity,
    EntityType,
    EntityRelation,
    RelationType,
    # Domain entities
    Repository,
    Commit,
    PullRequest,
    Build,
    Deployment,
    Incident,
    Service,
    Team,
    Developer,
    Environment,
    # Supporting
    IdentityMapping,
    EntityQuery,
)
from app.services.entities.store import EntityStore, get_entity_store
from app.services.entities.identity import IdentityResolver, get_identity_resolver

__all__ = [
    # Base
    "Entity",
    "EntityType",
    "EntityRelation",
    "RelationType",
    # Domain entities
    "Repository",
    "Commit",
    "PullRequest",
    "Build",
    "Deployment",
    "Incident",
    "Service",
    "Team",
    "Developer",
    "Environment",
    # Supporting
    "IdentityMapping",
    "EntityQuery",
    # Store
    "EntityStore",
    "get_entity_store",
    # Identity
    "IdentityResolver",
    "get_identity_resolver",
]
