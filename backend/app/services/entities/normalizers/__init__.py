"""Entity normalizers for transforming source data to canonical entities.

Each normalizer handles data from a specific source system and transforms
it into the canonical entity model.
"""

from app.services.entities.normalizers.base import BaseNormalizer
from app.services.entities.normalizers.github import GitHubNormalizer
from app.services.entities.normalizers.gitlab import GitLabNormalizer

__all__ = [
    "BaseNormalizer",
    "GitHubNormalizer",
    "GitLabNormalizer",
]
