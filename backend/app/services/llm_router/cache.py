"""
Semantic Cache

Cache LLM responses based on semantic similarity.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import asyncio
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached response."""
    key: str
    query: str
    response: Any
    model_id: str
    task_type: str
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    embedding: Optional[List[float]] = None


class SemanticCache:
    """
    Semantic cache for LLM responses.
    
    Features:
    - Exact match caching
    - Semantic similarity matching
    - TTL-based expiration
    - Hit tracking
    """
    
    def __init__(
        self,
        backend: Optional[Any] = None,
        embeddings_service: Optional[Any] = None,
        similarity_threshold: float = 0.95,
        default_ttl: int = 3600,
    ):
        self.backend = backend  # Redis or similar
        self.embeddings = embeddings_service
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        
        # In-memory cache for local mode
        self._local_cache: Dict[str, CacheEntry] = {}
    
    def generate_key(
        self,
        query: str,
        task_type: str,
        model_id: Optional[str] = None,
    ) -> str:
        """Generate cache key from query."""
        content = f"{task_type}:{query}"
        if model_id:
            content = f"{model_id}:{content}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response."""
        # Try backend first
        if self.backend:
            try:
                data = await self.backend.get(f"llm_cache:{key}")
                if data:
                    entry = json.loads(data)
                    # Check expiration
                    if datetime.fromisoformat(entry["expires_at"]) > datetime.utcnow():
                        # Update hit count
                        entry["hit_count"] = entry.get("hit_count", 0) + 1
                        await self.backend.set(
                            f"llm_cache:{key}",
                            json.dumps(entry),
                        )
                        return entry
            except Exception as e:
                logger.warning(f"Cache backend error: {e}")
        
        # Fall back to local cache
        if key in self._local_cache:
            entry = self._local_cache[key]
            if entry.expires_at > datetime.utcnow():
                entry.hit_count += 1
                return {
                    "response": entry.response,
                    "model_id": entry.model_id,
                    "task_type": entry.task_type,
                    "hit_count": entry.hit_count,
                }
            else:
                del self._local_cache[key]
        
        return None
    
    async def set(
        self,
        key: str,
        query: str,
        response: Any,
        model_id: str,
        task_type: str,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache a response."""
        ttl = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        entry_data = {
            "key": key,
            "query": query,
            "response": response,
            "model_id": model_id,
            "task_type": task_type,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "hit_count": 0,
        }
        
        # Store in backend
        if self.backend:
            try:
                await self.backend.set(
                    f"llm_cache:{key}",
                    json.dumps(entry_data),
                    ex=ttl,
                )
            except Exception as e:
                logger.warning(f"Cache backend error: {e}")
        
        # Also store locally
        self._local_cache[key] = CacheEntry(
            key=key,
            query=query,
            response=response,
            model_id=model_id,
            task_type=task_type,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )
    
    async def find_similar(
        self,
        query: str,
        task_type: str,
        top_k: int = 5,
    ) -> List[CacheEntry]:
        """
        Find semantically similar cached queries.
        
        Requires embeddings service to be configured.
        """
        if not self.embeddings:
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self.embeddings.embed_single(query)
            
            # Search for similar entries
            similar = []
            for entry in self._local_cache.values():
                if entry.task_type != task_type:
                    continue
                if entry.expires_at <= datetime.utcnow():
                    continue
                if not entry.embedding:
                    continue
                
                # Calculate similarity
                similarity = self._cosine_similarity(
                    query_embedding.embedding,
                    entry.embedding,
                )
                
                if similarity >= self.similarity_threshold:
                    similar.append((entry, similarity))
            
            # Sort by similarity
            similar.sort(key=lambda x: x[1], reverse=True)
            
            return [entry for entry, _ in similar[:top_k]]
            
        except Exception as e:
            logger.warning(f"Semantic search error: {e}")
            return []
    
    def _cosine_similarity(
        self,
        a: List[float],
        b: List[float],
    ) -> float:
        """Calculate cosine similarity."""
        import numpy as np
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    async def invalidate(self, key: str) -> None:
        """Invalidate a cache entry."""
        if self.backend:
            try:
                await self.backend.delete(f"llm_cache:{key}")
            except Exception:
                pass
        
        if key in self._local_cache:
            del self._local_cache[key]
    
    async def clear(self, task_type: Optional[str] = None) -> int:
        """Clear cache entries."""
        count = 0
        
        keys_to_delete = []
        for key, entry in self._local_cache.items():
            if task_type is None or entry.task_type == task_type:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._local_cache[key]
            count += 1
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        
        total = len(self._local_cache)
        expired = sum(1 for e in self._local_cache.values() if e.expires_at <= now)
        total_hits = sum(e.hit_count for e in self._local_cache.values())
        
        by_task = {}
        for entry in self._local_cache.values():
            if entry.task_type not in by_task:
                by_task[entry.task_type] = 0
            by_task[entry.task_type] += 1
        
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "total_hits": total_hits,
            "by_task_type": by_task,
        }
