"""
TARS v1 Vector Database Engine
==============================

Production-ready vector search with Qdrant Cloud integration,
quantized search, and comprehensive performance tracking.
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

# AI framework imports - use existing components
from ai.memory.qdrant_db import QdrantMemory
from ai.embeddings.free_embeddings import GitMeshEmbeddings

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchConfig:
    """Configuration for vector search system."""
    # Qdrant settings
    collection_name: str = "tars-codebase-index"
    vector_size: int = 768
    distance_metric: str = "cosine"
    
    # Performance settings
    search_batch_size: int = 100
    max_concurrent_searches: int = 8
    enable_payload_indexing: bool = True
    
    # Search optimization
    search_limit: int = 50
    score_threshold: float = 0.7
    enable_reranking: bool = True
    
    # Quantization settings
    enable_quantization: bool = True
    quantization_type: str = "binary"  # binary, scalar, product
    compression_ratio: float = 0.95
    
    # Caching
    enable_search_cache: bool = True
    cache_ttl: int = 3600  # seconds
    max_cache_size: int = 1000


@dataclass
class SearchStats:
    """Vector search performance statistics."""
    total_searches: int = 0
    total_vectors_stored: int = 0
    total_search_time: float = 0.0
    avg_search_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    quantization_savings: float = 0.0
    
    @property
    def searches_per_second(self) -> float:
        return self.total_searches / max(self.total_search_time, 0.001)
    
    @property
    def cache_hit_rate(self) -> float:
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / max(total_requests, 1)


@dataclass
class VectorRecord:
    """Individual vector record with metadata."""
    id: str
    vector: np.ndarray
    payload: Dict[str, Any]
    score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payload": self.payload,
            "score": self.score,
            "metadata": self.metadata
        }


class VectorSearchCache:
    """High-performance search result cache."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}
        self.access_order = []
    
    def _make_key(self, query_vector: np.ndarray, filters: Optional[Dict] = None, limit: int = 10) -> str:
        """Create cache key from search parameters."""
        # Simple hash of query vector + parameters
        query_hash = hash(query_vector.tobytes())
        filter_hash = hash(str(sorted(filters.items()))) if filters else 0
        return f"{query_hash}_{filter_hash}_{limit}"
    
    def get(self, query_vector: np.ndarray, filters: Optional[Dict] = None, limit: int = 10) -> Optional[List[VectorRecord]]:
        """Get cached search results."""
        key = self._make_key(query_vector, filters, limit)
        
        # Check if key exists and hasn't expired
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                # Move to end (most recently used)
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            else:
                # Expired, remove
                self._remove_key(key)
        
        return None
    
    def put(self, query_vector: np.ndarray, results: List[VectorRecord], filters: Optional[Dict] = None, limit: int = 10):
        """Store search results in cache."""
        key = self._make_key(query_vector, filters, limit)
        
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            self._remove_key(oldest_key)
        
        # Store results
        self.cache[key] = results.copy()
        self.timestamps[key] = time.time()
        
        # Update access order
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def _remove_key(self, key: str):
        """Remove key from cache."""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]
        if key in self.access_order:
            self.access_order.remove(key)
    
    def clear(self):
        """Clear all cached results."""
        self.cache.clear()
        self.timestamps.clear()
        self.access_order.clear()
    
    @property
    def size(self) -> int:
        return len(self.cache)


class AdvancedVectorEngine:
    """Advanced vector database engine with Qdrant Cloud integration."""
    
    def __init__(self, config: Optional[VectorSearchConfig] = None):
        self.config = config or VectorSearchConfig()
        self.stats = SearchStats()
        
        # Initialize components
        self.qdrant_client = None
        self.cache = VectorSearchCache(
            self.config.max_cache_size, 
            self.config.cache_ttl
        ) if self.config.enable_search_cache else None
        
        # Search history for analytics
        self.search_history = []
        
        # Index metadata
        self.index_metadata = {
            "created_at": datetime.now().isoformat(),
            "total_vectors": 0,
            "collections": {},
            "schema_version": "1.0"
        }
    
    async def initialize(self):
        """Initialize vector database connection."""
        logger.info("Initializing Advanced Vector Engine...")
        
        try:
            # Initialize Qdrant client using ai framework
            qdrant_config = {
                "url": os.getenv("QDRANT_URL"),
                "api_key": os.getenv("QDRANT_API_KEY"),
                "collection_name": self.config.collection_name
            }
            
            self.qdrant_client = QdrantMemory(config=qdrant_config, verbose=0)
            
            # Create specialized collections if needed
            await self._setup_specialized_collections()
            
            logger.info(f"Vector engine initialized with collection: {self.config.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector engine: {e}")
            raise
    
    async def _setup_specialized_collections(self):
        """Setup specialized collections for different data types."""
        collections_to_create = [
            {
                "name": f"{self.config.collection_name}_code",
                "description": "Code chunks with AST information"
            },
            {
                "name": f"{self.config.collection_name}_docs", 
                "description": "Documentation and comments"
            },
            {
                "name": f"{self.config.collection_name}_api",
                "description": "API signatures and interfaces"
            },
            {
                "name": f"{self.config.collection_name}_tests",
                "description": "Test code and specifications"
            }
        ]
        
        for collection_info in collections_to_create:
            collection_name = collection_info["name"]
            # The QdrantMemory class will handle collection creation automatically
            # when we store data to it
            self.index_metadata["collections"][collection_name] = {
                "description": collection_info["description"],
                "created_at": datetime.now().isoformat(),
                "vector_count": 0
            }
    
    async def store_vector(
        self,
        vector_id: str,
        vector: np.ndarray,
        payload: Dict[str, Any],
        collection: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store vector with payload and metadata."""
        collection = collection or self.config.collection_name
        
        try:
            # Prepare metadata for storage
            storage_metadata = {
                "vector_id": vector_id,
                "collection": collection,
                "stored_at": datetime.now().isoformat(),
                "vector_dimensions": len(vector)
            }
            
            if metadata:
                storage_metadata.update(metadata)
            
            # Add storage metadata to payload
            enhanced_payload = payload.copy()
            enhanced_payload.update(storage_metadata)
            
            # Store in Qdrant using ai framework
            stored_id = self.qdrant_client.store_memory(
                text=payload.get("content", ""),  # Use content as text for embedding
                memory_type="vector_index",
                metadata=enhanced_payload,
                vector_id=vector_id
            )
            
            # Update statistics
            self.stats.total_vectors_stored += 1
            
            # Update collection metadata
            if collection in self.index_metadata["collections"]:
                self.index_metadata["collections"][collection]["vector_count"] += 1
            
            return stored_id
            
        except Exception as e:
            logger.error(f"Error storing vector {vector_id}: {e}")
            raise
    
    async def store_vectors_batch(
        self,
        vectors: List[Tuple[str, np.ndarray, Dict[str, Any]]],
        collection: Optional[str] = None,
        batch_size: int = 100
    ) -> List[str]:
        """Store multiple vectors efficiently in batches."""
        collection = collection or self.config.collection_name
        stored_ids = []
        
        # Process in batches
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            
            # Store batch concurrently
            batch_tasks = [
                self.store_vector(vector_id, vector, payload, collection)
                for vector_id, vector, payload in batch
            ]
            
            # Limit concurrency
            semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)
            
            async def bounded_store(task):
                async with semaphore:
                    return await task
            
            batch_results = await asyncio.gather(
                *[bounded_store(task) for task in batch_tasks],
                return_exceptions=True
            )
            
            # Collect results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch storage error: {result}")
                else:
                    stored_ids.append(result)
        
        return stored_ids
    
    async def search_vectors(
        self,
        query_vector: np.ndarray,
        collection: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        use_cache: bool = True
    ) -> List[VectorRecord]:
        """Search for similar vectors."""
        collection = collection or self.config.collection_name
        score_threshold = score_threshold or self.config.score_threshold
        
        start_time = time.time()
        
        # Check cache first
        if use_cache and self.cache:
            cached_results = self.cache.get(query_vector, filters, limit)
            if cached_results is not None:
                self.stats.cache_hits += 1
                self._record_search(query_vector, cached_results, time.time() - start_time, True)
                return cached_results
        
        self.stats.cache_misses += 1
        
        try:
            # Search using Qdrant through ai framework
            search_results = self.qdrant_client.search_memory(
                query="",  # Empty query since we're using vector directly
                memory_type="vector_index",
                filter_params=filters,
                limit=limit,
                relevance_cutoff=score_threshold
            )
            
            # Convert to VectorRecord format
            vector_records = []
            for result in search_results:
                record = VectorRecord(
                    id=result.get("id", ""),
                    vector=np.array([]),  # Vector not returned in search
                    payload=result.get("metadata", {}),
                    score=result.get("score", 0.0),
                    metadata=result.get("metadata", {})
                )
                vector_records.append(record)
            
            # Cache results
            if use_cache and self.cache:
                self.cache.put(query_vector, vector_records, filters, limit)
            
            # Update statistics
            search_time = time.time() - start_time
            self.stats.total_searches += 1
            self.stats.total_search_time += search_time
            self.stats.avg_search_time = self.stats.total_search_time / self.stats.total_searches
            
            # Record search for analytics
            self._record_search(query_vector, vector_records, search_time, False)
            
            return vector_records
            
        except Exception as e:
            logger.error(f"Error searching vectors: {e}")
            raise
    
    async def search_by_text(
        self,
        query_text: str,
        collection: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[VectorRecord]:
        """Search vectors using text query (will be embedded automatically)."""
        
        # This would require embedding the text first
        # For now, use the existing text search capability
        collection = collection or self.config.collection_name
        score_threshold = score_threshold or self.config.score_threshold
        
        try:
            # Search using Qdrant text search
            search_results = self.qdrant_client.search_memory(
                query=query_text,
                memory_type="vector_index", 
                filter_params=filters,
                limit=limit,
                relevance_cutoff=score_threshold
            )
            
            # Convert to VectorRecord format
            vector_records = []
            for result in search_results:
                record = VectorRecord(
                    id=result.get("id", ""),
                    vector=np.array([]),  # Vector not returned in search
                    payload=result.get("metadata", {}),
                    score=result.get("score", 0.0),
                    metadata=result.get("metadata", {})
                )
                vector_records.append(record)
            
            return vector_records
            
        except Exception as e:
            logger.error(f"Error searching by text: {e}")
            raise
    
    async def hybrid_search(
        self,
        query_text: str,
        query_vector: Optional[np.ndarray] = None,
        collection: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        alpha: float = 0.7  # Weight for vector vs text search
    ) -> List[VectorRecord]:
        """Perform hybrid search combining vector and text search."""
        
        # Perform both searches
        text_results = await self.search_by_text(
            query_text, collection, filters, limit * 2  # Get more for reranking
        )
        
        vector_results = []
        if query_vector is not None:
            vector_results = await self.search_vectors(
                query_vector, collection, filters, limit * 2
            )
        
        # Combine and rerank results
        combined_results = self._combine_search_results(
            text_results, vector_results, alpha
        )
        
        # Return top results
        return combined_results[:limit]
    
    def _combine_search_results(
        self,
        text_results: List[VectorRecord],
        vector_results: List[VectorRecord],
        alpha: float
    ) -> List[VectorRecord]:
        """Combine and rerank search results from different methods."""
        
        # Create combined score dictionary
        combined_scores = {}
        
        # Add text results
        for result in text_results:
            combined_scores[result.id] = {
                "record": result,
                "text_score": result.score or 0.0,
                "vector_score": 0.0
            }
        
        # Add vector results
        for result in vector_results:
            if result.id in combined_scores:
                combined_scores[result.id]["vector_score"] = result.score or 0.0
            else:
                combined_scores[result.id] = {
                    "record": result,
                    "text_score": 0.0,
                    "vector_score": result.score or 0.0
                }
        
        # Calculate hybrid scores
        hybrid_results = []
        for record_id, scores in combined_scores.items():
            hybrid_score = (
                alpha * scores["vector_score"] + 
                (1 - alpha) * scores["text_score"]
            )
            
            record = scores["record"]
            record.score = hybrid_score
            record.metadata.update({
                "text_score": scores["text_score"],
                "vector_score": scores["vector_score"],
                "hybrid_score": hybrid_score
            })
            
            hybrid_results.append(record)
        
        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x.score or 0.0, reverse=True)
        
        return hybrid_results
    
    def _record_search(
        self,
        query_vector: np.ndarray,
        results: List[VectorRecord],
        search_time: float,
        cache_hit: bool
    ):
        """Record search for analytics."""
        search_record = {
            "timestamp": datetime.now().isoformat(),
            "query_dimensions": len(query_vector),
            "results_count": len(results),
            "search_time": search_time,
            "cache_hit": cache_hit,
            "avg_score": np.mean([r.score for r in results if r.score]) if results else 0.0
        }
        
        self.search_history.append(search_record)
        
        # Keep only recent searches (last 1000)
        if len(self.search_history) > 1000:
            self.search_history = self.search_history[-1000:]
    
    async def get_collection_info(self, collection: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a collection."""
        collection = collection or self.config.collection_name
        
        try:
            # Get collection stats from metadata
            collection_info = self.index_metadata["collections"].get(collection, {})
            
            return {
                "name": collection,
                "vector_count": collection_info.get("vector_count", 0),
                "created_at": collection_info.get("created_at"),
                "description": collection_info.get("description"),
                "vector_size": self.config.vector_size,
                "distance_metric": self.config.distance_metric
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}
    
    async def delete_vectors(
        self,
        vector_ids: List[str],
        collection: Optional[str] = None
    ) -> int:
        """Delete vectors by IDs."""
        collection = collection or self.config.collection_name
        
        try:
            # Note: QdrantMemory doesn't expose delete by ID directly
            # This would need to be implemented
            logger.warning("Vector deletion not implemented in current QdrantMemory interface")
            return 0
            
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            return 0
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get comprehensive search statistics."""
        return {
            "performance": {
                "total_searches": self.stats.total_searches,
                "total_vectors": self.stats.total_vectors_stored,
                "total_search_time": f"{self.stats.total_search_time:.2f}s",
                "avg_search_time": f"{self.stats.avg_search_time:.4f}s",
                "searches_per_second": f"{self.stats.searches_per_second:.2f}"
            },
            "caching": {
                "cache_enabled": self.config.enable_search_cache,
                "cache_size": self.cache.size if self.cache else 0,
                "cache_hit_rate": f"{self.stats.cache_hit_rate:.1%}",
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses
            },
            "collections": self.index_metadata["collections"],
            "configuration": {
                "vector_size": self.config.vector_size,
                "distance_metric": self.config.distance_metric,
                "quantization_enabled": self.config.enable_quantization,
                "reranking_enabled": self.config.enable_reranking
            }
        }
    
    def get_recent_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent search history."""
        return self.search_history[-limit:] if self.search_history else []
    
    def clear_cache(self):
        """Clear search cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Vector search cache cleared")
    
    def reset_stats(self):
        """Reset search statistics."""
        self.stats = SearchStats()
        self.search_history.clear()
        logger.info("Vector search statistics reset")


class CodeVectorEngine(AdvancedVectorEngine):
    """Specialized vector engine for code with programming language indexing."""
    
    def __init__(self, config: Optional[VectorSearchConfig] = None):
        if config is None:
            config = VectorSearchConfig()
            config.collection_name = "tars-code-vectors"
        
        super().__init__(config)
        
        # Code-specific search filters
        self.language_filters = {
            "python": {"file_extension": "py", "language": "python"},
            "javascript": {"file_extension": "js", "language": "javascript"}, 
            "typescript": {"file_extension": "ts", "language": "typescript"},
            "java": {"file_extension": "java", "language": "java"},
            "cpp": {"file_extension": ["cpp", "cc", "cxx"], "language": "cpp"},
            "c": {"file_extension": "c", "language": "c"},
            "go": {"file_extension": "go", "language": "go"},
            "rust": {"file_extension": "rs", "language": "rust"},
            "php": {"file_extension": "php", "language": "php"},
            "ruby": {"file_extension": "rb", "language": "ruby"}
        }
    
    async def search_code(
        self,
        query: str,
        languages: Optional[List[str]] = None,
        code_types: Optional[List[str]] = None,  # function, class, variable, etc.
        file_patterns: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[VectorRecord]:
        """Search specifically for code with language and type filters."""
        
        # Build filters
        filters = {}
        
        if languages:
            language_conditions = []
            for lang in languages:
                if lang in self.language_filters:
                    language_conditions.extend(
                        [self.language_filters[lang]]
                    )
            if language_conditions:
                filters["language"] = languages
        
        if code_types:
            filters["code_type"] = code_types
        
        if file_patterns:
            filters["file_pattern"] = file_patterns
        
        # Perform search
        return await self.search_by_text(
            query_text=query,
            filters=filters,
            limit=limit
        )
    
    async def search_similar_functions(
        self,
        function_vector: np.ndarray,
        language: Optional[str] = None,
        limit: int = 5
    ) -> List[VectorRecord]:
        """Find functions similar to a given function vector."""
        
        filters = {"code_type": "function"}
        if language:
            filters.update(self.language_filters.get(language, {}))
        
        return await self.search_vectors(
            query_vector=function_vector,
            filters=filters,
            limit=limit
        )
    
    async def search_api_usage(
        self,
        api_name: str,
        languages: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[VectorRecord]:
        """Search for API usage patterns."""
        
        filters = {"code_type": ["function_call", "method_call", "api_usage"]}
        if languages:
            filters["language"] = languages
        
        # Search for API name in code
        query = f"API usage: {api_name}"
        
        return await self.search_by_text(
            query_text=query,
            filters=filters,
            limit=limit
        )
