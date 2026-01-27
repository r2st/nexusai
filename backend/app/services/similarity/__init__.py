"""Code Similarity Service.

Provides code similarity matching capabilities using:
- Vector embeddings for semantic similarity
- AST-based structural similarity
- Token-based syntactic similarity
"""

from app.services.similarity.service import SimilarityService, similarity_service

__all__ = ["SimilarityService", "similarity_service"]
