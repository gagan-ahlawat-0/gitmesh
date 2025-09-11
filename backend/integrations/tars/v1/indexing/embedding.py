"""
TARS v1 Advanced Embedding Engine
=================================

Production-ready embedding system with multiple model support, 
caching, and comprehensive performance tracking.
"""

import os
import json
import time
import hashlib
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

# AI framework imports - use existing components
from ai.embeddings.free_embeddings import GitMeshEmbeddings, get_embedding_service
from ai.memory.qdrant_db import QdrantMemory

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingStats:
    """Embedding performance statistics."""
    total_embeddings: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_tokens: int = 0
    embedding_time: float = 0.0
    avg_embedding_time: float = 0.0
    model_name: str = ""
    dimensions: int = 0
    
    @property
    def cache_hit_rate(self) -> float:
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / max(total_requests, 1)
    
    @property
    def embeddings_per_second(self) -> float:
        return self.total_embeddings / max(self.embedding_time, 0.001)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding system."""
    # Model configuration
    primary_model: str = "jina-code-v2"
    fallback_models: List[str] = field(default_factory=lambda: ["all-MiniLM-L6-v2", "all-mpnet-base-v2"])
    
    # Performance settings
    batch_size: int = 32
    max_concurrent: int = 4
    cache_size: int = 10000
    enable_caching: bool = True
    
    # Quality settings
    enable_normalization: bool = True
    similarity_threshold: float = 0.7
    
    # Quantization settings
    enable_quantization: bool = True
    quantization_bits: int = 8
    
    # Advanced features
    enable_pooling: str = "mean"  # mean, max, cls
    enable_dimensionality_reduction: bool = False
    target_dimensions: Optional[int] = None


class EmbeddingCache:
    """High-performance embedding cache with LRU eviction."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache = {}
        self.access_order = []
    
    def _make_key(self, text: str, model: str) -> str:
        """Create cache key from text and model."""
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[np.ndarray]:
        """Get embedding from cache."""
        key = self._make_key(text, model)
        
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        
        return None
    
    def put(self, text: str, model: str, embedding: np.ndarray):
        """Store embedding in cache."""
        key = self._make_key(text, model)
        
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        # Store embedding
        self.cache[key] = embedding.copy()
        
        # Update access order
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.access_order.clear()
    
    @property
    def size(self) -> int:
        return len(self.cache)


class AdvancedEmbeddingEngine:
    """Advanced embedding engine with multi-model support and optimization."""
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self.stats = EmbeddingStats()
        
        # Initialize cache
        self.cache = EmbeddingCache(self.config.cache_size) if self.config.enable_caching else None
        
        # Initialize embedding services
        self.embedding_services = {}
        self.primary_service = None
        
        # Performance tracking
        self.embedding_history = []
    
    async def initialize(self):
        """Initialize embedding services."""
        logger.info("Initializing Advanced Embedding Engine...")
        
        try:
            # Initialize primary embedding service
            self.primary_service = self._create_embedding_service(self.config.primary_model)
            self.embedding_services[self.config.primary_model] = self.primary_service
            
            # Update stats
            self.stats.model_name = self.config.primary_model
            self.stats.dimensions = self.primary_service.embedding_dimension
            
            # Initialize fallback services
            for model_name in self.config.fallback_models:
                if model_name not in self.embedding_services:
                    try:
                        service = self._create_embedding_service(model_name)
                        self.embedding_services[model_name] = service
                        logger.info(f"Initialized fallback model: {model_name}")
                    except Exception as e:
                        logger.warning(f"Failed to initialize fallback model {model_name}: {e}")
            
            logger.info(f"Embedding engine initialized with {len(self.embedding_services)} models")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding engine: {e}")
            raise
    
    def _create_embedding_service(self, model_name: str) -> GitMeshEmbeddings:
        """Create embedding service for specific model."""
        # Map model names to embedding service types
        if "jina" in model_name.lower():
            return get_embedding_service("best")  # Use best quality for Jina models
        elif "minilm" in model_name.lower():
            return get_embedding_service("fast")
        elif "mpnet" in model_name.lower():
            return get_embedding_service("best")
        else:
            return get_embedding_service("fast")  # Default
    
    async def embed_text(
        self, 
        text: str, 
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Embed single text with performance tracking."""
        model = model or self.config.primary_model
        start_time = time.time()
        
        # Check cache first
        if use_cache and self.cache:
            cached_embedding = self.cache.get(text, model)
            if cached_embedding is not None:
                self.stats.cache_hits += 1
                metadata = {
                    "cache_hit": True,
                    "model": model,
                    "embedding_time": time.time() - start_time,
                    "dimensions": len(cached_embedding)
                }
                return cached_embedding, metadata
        
        self.stats.cache_misses += 1
        
        # Generate embedding
        embedding_service = self.embedding_services.get(model, self.primary_service)
        
        try:
            # Get raw embedding
            raw_embedding = embedding_service.embed(text, normalize=self.config.enable_normalization)
            
            # Convert to numpy array if needed
            if not isinstance(raw_embedding, np.ndarray):
                raw_embedding = np.array(raw_embedding)
            
            # Apply post-processing
            processed_embedding = await self._post_process_embedding(raw_embedding)
            
            # Cache the result
            if use_cache and self.cache:
                self.cache.put(text, model, processed_embedding)
            
            # Update statistics
            embedding_time = time.time() - start_time
            self.stats.total_embeddings += 1
            self.stats.total_tokens += len(text.split())
            self.stats.embedding_time += embedding_time
            self.stats.avg_embedding_time = self.stats.embedding_time / self.stats.total_embeddings
            
            metadata = {
                "cache_hit": False,
                "model": model,
                "embedding_time": embedding_time,
                "dimensions": len(processed_embedding),
                "normalized": self.config.enable_normalization,
                "quantized": self.config.enable_quantization
            }
            
            # Record embedding history
            self.embedding_history.append({
                "timestamp": datetime.now().isoformat(),
                "text_length": len(text),
                "tokens": len(text.split()),
                "model": model,
                "embedding_time": embedding_time,
                "cache_hit": False,
                "dimensions": len(processed_embedding)
            })
            
            return processed_embedding, metadata
            
        except Exception as e:
            logger.error(f"Error generating embedding with model {model}: {e}")
            
            # Try fallback models
            for fallback_model in self.config.fallback_models:
                if fallback_model != model and fallback_model in self.embedding_services:
                    logger.info(f"Trying fallback model: {fallback_model}")
                    try:
                        return await self.embed_text(text, fallback_model, use_cache)
                    except Exception as fe:
                        logger.warning(f"Fallback model {fallback_model} also failed: {fe}")
            
            raise Exception(f"All embedding models failed for text: {text[:100]}...")
    
    async def embed_batch(
        self, 
        texts: List[str], 
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> Tuple[List[np.ndarray], List[Dict[str, Any]]]:
        """Embed batch of texts efficiently."""
        model = model or self.config.primary_model
        
        embeddings = []
        metadatas = []
        
        # Process in batches
        batch_size = self.config.batch_size
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                self.embed_text(text, model, use_cache)
                for text in batch_texts
            ]
            
            # Limit concurrency
            semaphore = asyncio.Semaphore(self.config.max_concurrent)
            
            async def bounded_embed(task):
                async with semaphore:
                    return await task
            
            batch_results = await asyncio.gather(
                *[bounded_embed(task) for task in tasks],
                return_exceptions=True
            )
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch embedding error: {result}")
                    # Add placeholder for failed embedding
                    embeddings.append(np.zeros(self.stats.dimensions))
                    metadatas.append({"error": str(result)})
                else:
                    embedding, metadata = result
                    embeddings.append(embedding)
                    metadatas.append(metadata)
        
        return embeddings, metadatas
    
    async def _post_process_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Apply post-processing to embeddings."""
        processed = embedding.copy()
        
        # Apply quantization if enabled
        if self.config.enable_quantization:
            processed = self._quantize_embedding(processed, self.config.quantization_bits)
        
        # Apply dimensionality reduction if enabled
        if self.config.enable_dimensionality_reduction and self.config.target_dimensions:
            processed = self._reduce_dimensions(processed, self.config.target_dimensions)
        
        return processed
    
    def _quantize_embedding(self, embedding: np.ndarray, bits: int) -> np.ndarray:
        """Quantize embedding to reduce memory usage."""
        if bits >= 32:
            return embedding
        
        # Simple uniform quantization
        min_val = embedding.min()
        max_val = embedding.max()
        
        # Avoid division by zero
        if max_val == min_val:
            return embedding
        
        # Quantize to specified bits
        num_levels = 2 ** bits - 1
        quantized = np.round((embedding - min_val) / (max_val - min_val) * num_levels)
        
        # Dequantize back to float
        dequantized = quantized / num_levels * (max_val - min_val) + min_val
        
        return dequantized.astype(np.float32)
    
    def _reduce_dimensions(self, embedding: np.ndarray, target_dims: int) -> np.ndarray:
        """Reduce embedding dimensions using PCA or truncation."""
        if len(embedding) <= target_dims:
            return embedding
        
        # Simple truncation for now (could implement PCA later)
        return embedding[:target_dims]
    
    async def compute_similarity(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray,
        metric: str = "cosine"
    ) -> float:
        """Compute similarity between embeddings."""
        if metric == "cosine":
            # Ensure embeddings are normalized
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(np.dot(embedding1, embedding2) / (norm1 * norm2))
        
        elif metric == "euclidean":
            return float(1.0 / (1.0 + np.linalg.norm(embedding1 - embedding2)))
        
        elif metric == "manhattan":
            return float(1.0 / (1.0 + np.sum(np.abs(embedding1 - embedding2))))
        
        else:
            raise ValueError(f"Unsupported similarity metric: {metric}")
    
    async def find_similar_embeddings(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: List[np.ndarray],
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Tuple[int, float]]:
        """Find most similar embeddings to query."""
        threshold = threshold or self.config.similarity_threshold
        
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            similarity = await self.compute_similarity(query_embedding, candidate)
            if similarity >= threshold:
                similarities.append((i, similarity))
        
        # Sort by similarity (descending) and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get comprehensive embedding statistics."""
        return {
            "performance": {
                "total_embeddings": self.stats.total_embeddings,
                "total_tokens": self.stats.total_tokens,
                "total_time": f"{self.stats.embedding_time:.2f}s",
                "avg_time_per_embedding": f"{self.stats.avg_embedding_time:.4f}s",
                "embeddings_per_second": f"{self.stats.embeddings_per_second:.2f}"
            },
            "caching": {
                "cache_enabled": self.config.enable_caching,
                "cache_size": self.cache.size if self.cache else 0,
                "cache_hit_rate": f"{self.stats.cache_hit_rate:.1%}",
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses
            },
            "models": {
                "primary_model": self.config.primary_model,
                "available_models": list(self.embedding_services.keys()),
                "dimensions": self.stats.dimensions
            },
            "configuration": {
                "batch_size": self.config.batch_size,
                "max_concurrent": self.config.max_concurrent,
                "normalization": self.config.enable_normalization,
                "quantization": self.config.enable_quantization,
                "quantization_bits": self.config.quantization_bits if self.config.enable_quantization else None
            }
        }
    
    def get_recent_embeddings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent embedding history."""
        return self.embedding_history[-limit:] if self.embedding_history else []
    
    def clear_cache(self):
        """Clear embedding cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Embedding cache cleared")
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = EmbeddingStats()
        self.stats.model_name = self.config.primary_model
        if self.primary_service:
            self.stats.dimensions = self.primary_service.embedding_dimension
        self.embedding_history.clear()
        logger.info("Embedding statistics reset")


class CodeSpecificEmbeddingEngine(AdvancedEmbeddingEngine):
    """Specialized embedding engine for code with programming language awareness."""
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        # Override default config for code-specific settings
        if config is None:
            config = EmbeddingConfig()
            # Use code-optimized models by default
            config.primary_model = "jina-code-v2"  # Best for code
            config.fallback_models = ["all-mpnet-base-v2", "all-MiniLM-L6-v2"]
        
        super().__init__(config)
        
        # Code-specific preprocessing
        self.language_processors = {
            "python": self._preprocess_python,
            "javascript": self._preprocess_javascript,
            "typescript": self._preprocess_typescript,
            "java": self._preprocess_java,
            "cpp": self._preprocess_cpp,
            "c": self._preprocess_cpp,
            "go": self._preprocess_go,
            "rust": self._preprocess_rust,
            "php": self._preprocess_php,
            "ruby": self._preprocess_ruby,
            "scala": self._preprocess_scala,
            "kotlin": self._preprocess_kotlin
        }
    
    async def embed_code(
        self,
        code: str,
        language: str = "unknown",
        include_context: bool = True,
        model: Optional[str] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Embed code with language-specific preprocessing."""
        
        # Preprocess code based on language
        processed_code = self._preprocess_code(code, language)
        
        # Add language context if requested
        if include_context and language != "unknown":
            processed_code = f"[{language.upper()}] {processed_code}"
        
        # Generate embedding
        embedding, metadata = await self.embed_text(processed_code, model)
        
        # Add code-specific metadata
        metadata.update({
            "code_language": language,
            "code_length": len(code),
            "processed_length": len(processed_code),
            "include_context": include_context,
            "preprocessing_applied": language in self.language_processors
        })
        
        return embedding, metadata
    
    def _preprocess_code(self, code: str, language: str) -> str:
        """Preprocess code based on programming language."""
        if language.lower() in self.language_processors:
            return self.language_processors[language.lower()](code)
        return code  # No preprocessing for unknown languages
    
    def _preprocess_python(self, code: str) -> str:
        """Python-specific preprocessing."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip comments and docstrings for embedding focus
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _preprocess_javascript(self, code: str) -> str:
        """JavaScript-specific preprocessing."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip single-line comments
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _preprocess_typescript(self, code: str) -> str:
        """TypeScript-specific preprocessing (similar to JavaScript)."""
        return self._preprocess_javascript(code)
    
    def _preprocess_java(self, code: str) -> str:
        """Java-specific preprocessing."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip single-line comments and some imports
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                # Keep important imports
                if stripped.startswith('import') and any(keyword in stripped for keyword in ['java.util', 'java.lang', 'org.springframework']):
                    processed_lines.append(line)
                elif not stripped.startswith('import'):
                    processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _preprocess_cpp(self, code: str) -> str:
        """C/C++-specific preprocessing."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip single-line comments and preprocessor directives (except important ones)
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                if stripped.startswith('#include'):
                    # Keep standard library includes
                    if any(header in stripped for header in ['<iostream>', '<vector>', '<string>', '<algorithm>', '<memory>']):
                        processed_lines.append(line)
                elif not stripped.startswith('#'):
                    processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _preprocess_go(self, code: str) -> str:
        """Go-specific preprocessing."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//'):
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _preprocess_rust(self, code: str) -> str:
        """Rust-specific preprocessing."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _preprocess_php(self, code: str) -> str:
        """PHP-specific preprocessing."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//') and not stripped.startswith('#') and not stripped.startswith('/*'):
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _preprocess_ruby(self, code: str) -> str:
        """Ruby-specific preprocessing."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _preprocess_scala(self, code: str) -> str:
        """Scala-specific preprocessing."""
        return self._preprocess_java(code)  # Similar to Java
    
    def _preprocess_kotlin(self, code: str) -> str:
        """Kotlin-specific preprocessing."""
        return self._preprocess_java(code)  # Similar to Java
