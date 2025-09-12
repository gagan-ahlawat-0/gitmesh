"""
TARS v1 Core Indexing Engine
============================

Main indexing engine implementing hybrid multi-level architecture with
comprehensive performance tracking and context optimization.
"""

import os
import time
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import contextmanager

# AI framework imports
import ai.tools as tools
from ai.knowledge import Knowledge
from ai.memory import Memory
from ai.embeddings.free_embeddings import get_default_embeddings
from ai.memory.qdrant_db import QdrantMemory
from ai.memory.supabase_db import SupabaseMemory

# Advanced indexing components
from .embedding import AdvancedEmbeddingEngine, CodeSpecificEmbeddingEngine, EmbeddingConfig
from .vector import AdvancedVectorEngine, CodeVectorEngine, VectorSearchConfig
from .graph import GraphIntelligenceEngine, CodeRelationshipExtractor, GraphConfig

# Performance tracking
import psutil
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class IndexingConfig:
    """Production-ready configuration for the indexing system."""
    # Embedding settings - use production models
    embedding_model: str = "jina-code-v2"  # Best for code
    embedding_dim: int = 768
    context_window: int = 4000  # Conservative context window for better responses
    
    # Chunking settings - optimized for better AI responses
    chunk_sizes: List[int] = field(default_factory=lambda: [256, 512, 1024])  # Smaller chunks for better context
    overlap_ratio: float = 0.2  # Reduced overlap to fit more diverse content
    enable_semantic_chunking: bool = True
    enable_ast_chunking: bool = True
    
    # Performance settings - production optimized
    max_workers: int = min(8, (os.cpu_count() or 1))  # Reduced for stability
    batch_size: int = 64  # Smaller batches for better memory management
    enable_quantization: bool = True
    cache_size: int = 25000  # Reduced cache size
    
    # Memory settings - conservative limits for better responses
    max_memory_mb: int = 4096  # Reduced memory limit
    enable_lazy_loading: bool = True
    enable_memory_monitoring: bool = True
    memory_threshold: float = 0.8  # More conservative threshold
    
    # Context optimization settings - new for better AI responses
    max_context_items: int = 15  # Limit total context items
    max_context_tokens: int = 3000  # Reserve tokens for response
    context_relevance_threshold: float = 0.5  # Minimum relevance score
    enable_progressive_loading: bool = True  # Use progressive context loading
    context_compression_ratio: float = 0.7  # Target compression ratio
    
    # Quality settings - production standards
    min_chunk_quality: float = 0.6  # Slightly lower for more content
    enable_deduplication: bool = True
    enable_quality_analysis: bool = True
    
    # Database configurations - production setup
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "tars-production-index"
    
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Advanced features
    enable_graph_indexing: bool = True
    enable_vector_search: bool = True
    enable_hybrid_search: bool = True
    
    def __post_init__(self):
        """Auto-configure from environment variables."""
        if not self.qdrant_url:
            self.qdrant_url = os.getenv("QDRANT_URL")
        if not self.qdrant_api_key:
            self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        if not self.supabase_url:
            self.supabase_url = os.getenv("SUPABASE_URL")
        if not self.supabase_key:
            self.supabase_key = os.getenv("SUPABASE_ANON_KEY")


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    # Timing
    total_time: float = 0.0
    indexing_time: float = 0.0
    embedding_time: float = 0.0
    storage_time: float = 0.0
    
    # Resource usage
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Token statistics
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    context_tokens_used: int = 0
    context_tokens_available: int = 0
    
    # Context optimization
    context_utilization: float = 0.0
    context_compression_ratio: float = 0.0
    optimal_context_chunks: int = 0
    
    # Throughput
    files_per_second: float = 0.0
    tokens_per_second: float = 0.0
    chunks_per_second: float = 0.0
    
    # Quality metrics
    avg_chunk_quality: float = 0.0
    deduplication_ratio: float = 0.0
    index_coverage: float = 0.0


@dataclass
class TokenStats:
    """Detailed token usage statistics."""
    model_name: str
    max_context: int
    used_input: int
    used_output: int
    remaining_context: int
    efficiency_score: float
    optimization_suggestions: List[str] = field(default_factory=list)


@dataclass
class ContextStats:
    """Context window utilization statistics."""
    total_context_available: int
    context_used: int
    context_remaining: int
    utilization_percentage: float
    optimal_chunk_count: int
    context_fragmentation: float
    compression_achieved: float


class PerformanceTracker:
    """Real-time performance tracking with detailed metrics."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.start_time = None
        self.memory_samples = deque(maxlen=1000)
        self.token_history = []
        self.context_history = []
        self._monitoring = False
        self._monitor_thread = None
    
    def start_monitoring(self):
        """Start continuous performance monitoring."""
        self.start_time = time.time()
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_resources)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring and calculate final metrics."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join()
        
        if self.start_time:
            self.metrics.total_time = time.time() - self.start_time
        
        # Calculate averages
        if self.memory_samples:
            self.metrics.avg_memory_mb = sum(self.memory_samples) / len(self.memory_samples)
            self.metrics.peak_memory_mb = max(self.memory_samples)
    
    def _monitor_resources(self):
        """Continuous resource monitoring in background thread."""
        process = psutil.Process()
        
        while self._monitoring:
            try:
                # Memory usage
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.memory_samples.append(memory_mb)
                
                # CPU usage
                self.metrics.cpu_usage_percent = process.cpu_percent()
                
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
                break
    
    @contextmanager
    def track_operation(self, operation_name: str):
        """Context manager for tracking specific operations."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            # Update specific timing
            if operation_name == "indexing":
                self.metrics.indexing_time += duration
            elif operation_name == "embedding":
                self.metrics.embedding_time += duration
            elif operation_name == "storage":
                self.metrics.storage_time += duration
    
    def track_tokens(self, model_name: str, input_tokens: int, output_tokens: int, 
                    max_context: int, context_used: int):
        """Track token usage for a specific operation."""
        self.metrics.total_tokens_input += input_tokens
        self.metrics.total_tokens_output += output_tokens
        self.metrics.context_tokens_used += context_used
        self.metrics.context_tokens_available = max_context
        
        # Calculate efficiency
        remaining = max_context - context_used
        efficiency = context_used / max_context if max_context > 0 else 0
        
        # Create detailed token stats
        token_stats = TokenStats(
            model_name=model_name,
            max_context=max_context,
            used_input=input_tokens,
            used_output=output_tokens,
            remaining_context=remaining,
            efficiency_score=efficiency
        )
        
        # Add optimization suggestions
        if efficiency < 0.7:
            token_stats.optimization_suggestions.append("Context underutilized - consider larger chunks")
        elif efficiency > 0.95:
            token_stats.optimization_suggestions.append("Context nearly full - consider chunking")
        
        self.token_history.append(token_stats)
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get current real-time performance statistics."""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        current_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            "current_memory_mb": current_memory,
            "elapsed_time": current_time,
            "total_tokens": self.metrics.total_tokens_input + self.metrics.total_tokens_output,
            "context_utilization": self.metrics.context_utilization,
            "avg_processing_speed": self.metrics.tokens_per_second
        }


class ContextOptimizer:
    """Intelligent context window optimization."""
    
    def __init__(self, config: IndexingConfig):
        self.config = config
        self.context_stats = ContextStats(
            total_context_available=config.context_window,
            context_used=0,
            context_remaining=config.context_window,
            utilization_percentage=0.0,
            optimal_chunk_count=0,
            context_fragmentation=0.0,
            compression_achieved=0.0
        )
    
    def optimize_chunk_sizes(self, content_size: int, importance_score: float) -> List[int]:
        """Dynamically optimize chunk sizes based on content."""
        base_sizes = self.config.chunk_sizes.copy()
        
        # Adjust based on importance
        if importance_score > 0.8:
            # High importance - use larger context
            base_sizes = [size * 2 for size in base_sizes]
        elif importance_score < 0.3:
            # Low importance - use smaller context
            base_sizes = [size // 2 for size in base_sizes]
        
        # Ensure we don't exceed context window
        max_size = int(self.config.context_window * 0.8)  # Leave 20% buffer
        base_sizes = [min(size, max_size) for size in base_sizes]
        
        return sorted(set(base_sizes))
    
    def calculate_optimal_context(self, chunks: List[str], query: str = "") -> Tuple[List[str], ContextStats]:
        """Calculate optimal context selection with hierarchical chunking and relevance scoring."""
        available_context = self.config.context_window
        
        # Reserve space for query and response - more conservative for better responses
        query_tokens = len(query.split()) * 1.3  # Rough token estimate
        reserved_tokens = int(query_tokens + available_context * 0.35)  # 35% for response and overhead
        
        usable_context = available_context - reserved_tokens
        
        # Implement hierarchical context selection
        high_relevance_chunks = []
        medium_relevance_chunks = []
        low_relevance_chunks = []
        
        # Score and categorize chunks by relevance/importance
        for i, chunk in enumerate(chunks):
            chunk_tokens = len(chunk.split()) * 1.3
            importance = self._calculate_chunk_importance(chunk, query)
            
            chunk_data = (chunk, chunk_tokens, importance, i)
            
            if importance >= 0.8:
                high_relevance_chunks.append(chunk_data)
            elif importance >= 0.5:
                medium_relevance_chunks.append(chunk_data)
            else:
                low_relevance_chunks.append(chunk_data)
        
        # Sort each category by importance
        high_relevance_chunks.sort(key=lambda x: x[2], reverse=True)
        medium_relevance_chunks.sort(key=lambda x: x[2], reverse=True)
        low_relevance_chunks.sort(key=lambda x: x[2], reverse=True)
        
        # Progressive selection: prioritize high relevance, then medium, then low
        selected_chunks = []
        used_tokens = 0
        
        # First, include high relevance chunks (up to 60% of available context)
        high_context_limit = int(usable_context * 0.6)
        for chunk, tokens, importance, idx in high_relevance_chunks:
            if used_tokens + tokens <= high_context_limit:
                selected_chunks.append(chunk)
                used_tokens += tokens
            else:
                break
        
        # Then, add medium relevance chunks (up to 30% of available context)
        medium_context_limit = int(usable_context * 0.3)
        medium_tokens_used = 0
        for chunk, tokens, importance, idx in medium_relevance_chunks:
            if used_tokens + tokens <= usable_context and medium_tokens_used + tokens <= medium_context_limit:
                selected_chunks.append(chunk)
                used_tokens += tokens
                medium_tokens_used += tokens
            else:
                break
        
        # Finally, fill remaining space with low relevance chunks (up to 10%)
        low_context_limit = int(usable_context * 0.1)
        low_tokens_used = 0
        for chunk, tokens, importance, idx in low_relevance_chunks:
            if used_tokens + tokens <= usable_context and low_tokens_used + tokens <= low_context_limit:
                selected_chunks.append(chunk)
                used_tokens += tokens
                low_tokens_used += tokens
            else:
                break
        
        # Update context stats
        self.context_stats.context_used = int(used_tokens + reserved_tokens)
        self.context_stats.context_remaining = available_context - self.context_stats.context_used
        self.context_stats.utilization_percentage = (self.context_stats.context_used / available_context) * 100
        self.context_stats.optimal_chunk_count = len(selected_chunks)
        
        # Calculate fragmentation (unused context between selected chunks)
        total_possible = len(chunks)
        selected_ratio = len(selected_chunks) / total_possible if total_possible > 0 else 0
        self.context_stats.context_fragmentation = 1.0 - selected_ratio
        
        # Calculate compression achieved
        original_tokens = sum(len(chunk.split()) * 1.3 for chunk in chunks)
        compressed_tokens = used_tokens
        self.context_stats.compression_achieved = 1.0 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0
        
        return selected_chunks, self.context_stats
    
    def _calculate_chunk_importance(self, chunk: str, query: str) -> float:
        """Calculate importance score for a chunk with enhanced relevance scoring."""
        if not chunk.strip():
            return 0.0
        
        chunk_lower = chunk.lower()
        query_lower = query.lower() if query else ""
        
        importance_score = 0.0
        
        # 1. Direct keyword matching (40% weight)
        if query_lower:
            query_words = set(query_lower.split())
            chunk_words = set(chunk_lower.split())
            
            # Exact matches
            exact_matches = len(query_words.intersection(chunk_words))
            if len(query_words) > 0:
                exact_match_ratio = exact_matches / len(query_words)
                importance_score += exact_match_ratio * 0.4
            
            # Partial matches (substrings)
            partial_matches = 0
            for query_word in query_words:
                if any(query_word in chunk_word for chunk_word in chunk_words):
                    partial_matches += 1
            
            if len(query_words) > 0:
                partial_match_ratio = partial_matches / len(query_words)
                importance_score += partial_match_ratio * 0.2
        else:
            # No query provided, use base importance
            importance_score = 0.3
        
        # 2. Code structure importance (25% weight)
        code_indicators = [
            'def ', 'class ', 'function ', 'import ', 'from ',
            'export ', 'interface ', 'type ', 'const ', 'let ', 'var ',
            '@', 'async ', 'await ', 'return ', 'if ', 'for ', 'while'
        ]
        
        code_score = 0.0
        for indicator in code_indicators:
            if indicator in chunk_lower:
                code_score += 0.1
        
        importance_score += min(code_score, 0.25)
        
        # 3. Documentation and comments (15% weight)
        doc_indicators = ['"""', "'''", '/*', '//', '#', 'readme', 'documentation', 'comment']
        doc_score = 0.0
        for indicator in doc_indicators:
            if indicator in chunk_lower:
                doc_score += 0.05
        
        importance_score += min(doc_score, 0.15)
        
        # 4. Error handling and important keywords (10% weight)
        important_keywords = [
            'error', 'exception', 'try', 'catch', 'finally', 'raise',
            'main', 'init', 'setup', 'config', 'settings', 'api',
            'todo', 'fixme', 'bug', 'issue', 'security', 'auth'
        ]
        
        keyword_score = 0.0
        for keyword in important_keywords:
            if keyword in chunk_lower:
                keyword_score += 0.02
        
        importance_score += min(keyword_score, 0.1)
        
        # 5. Chunk length and information density (10% weight)
        chunk_length = len(chunk)
        
        # Prefer medium-length chunks (not too short, not too long)
        if 100 <= chunk_length <= 800:
            length_score = 0.1
        elif 50 <= chunk_length < 100 or 800 < chunk_length <= 1500:
            length_score = 0.05
        else:
            length_score = 0.02
        
        importance_score += length_score
        
        # Ensure score is between 0 and 1
        return min(max(importance_score, 0.0), 1.0)


class CodebaseIndexer:
    """Production-ready codebase indexer with state-of-the-art techniques."""
    
    def __init__(self, config: Optional[IndexingConfig] = None):
        self.config = config or IndexingConfig()
        self.performance_tracker = PerformanceTracker()
        self.context_optimizer = ContextOptimizer(self.config)
        
        # Initialize AI framework components
        self.knowledge = None
        self.memory = None
        
        # Initialize advanced indexing engines
        self.embedding_engine = None
        self.vector_engine = None
        self.graph_engine = None
        
        # Initialize chunking systems
        self.chunkers = {}
        self.quality_analyzer = None
        
        # Caching and state
        self.chunk_cache = {}
        self.embedding_cache = {}
        self.index_metadata = {
            "created_at": datetime.now().isoformat(),
            "config": self.config,
            "version": "2.0",
            "features": [
                "hierarchical_chunking",
                "semantic_embeddings", 
                "vector_search",
                "graph_analysis",
                "quality_monitoring",
                "context_optimization"
            ]
        }
    
    async def initialize(self):
        """Initialize all indexing components."""
        logger.info("Initializing Production TARS Codebase Indexer...")
        
        try:
            # Initialize AI framework components first
            await self._init_ai_framework()
            
            # Initialize advanced embedding engine
            await self._init_embedding_engine()
            
            # Initialize vector search engine  
            await self._init_vector_engine()
            
            # Initialize graph intelligence engine
            if self.config.enable_graph_indexing:
                await self._init_graph_engine()
            
            # Initialize chunking systems
            await self._init_chunking_systems()
            
            # Initialize quality analysis
            await self._init_quality_systems()
            
            logger.info("Production indexer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize indexer: {e}")
            raise
    
    async def _init_ai_framework(self):
        """Initialize AI framework components."""
        try:
            # Initialize Knowledge system with hybrid memory
            knowledge_config = {
                "version": "v2.0",
                "memory_type": "hybrid",
                "supabase": {
                    "url": self.config.supabase_url,
                    "key": self.config.supabase_key
                },
                "qdrant": {
                    "url": self.config.qdrant_url,
                    "api_key": self.config.qdrant_api_key,
                    "collection_name": self.config.qdrant_collection
                }
            }
            
            self.knowledge = Knowledge(config=knowledge_config, verbose=0)
            self.memory = Memory()
            
            logger.info("AI framework components initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI framework: {e}")
            raise
    
    async def _init_embedding_engine(self):
        """Initialize advanced embedding engine."""
        try:
            embedding_config = EmbeddingConfig(
                primary_model=self.config.embedding_model,
                batch_size=self.config.batch_size,
                cache_size=self.config.cache_size,
                enable_quantization=self.config.enable_quantization
            )
            
            # Use code-specific embedding engine for better code understanding
            self.embedding_engine = CodeSpecificEmbeddingEngine(embedding_config)
            await self.embedding_engine.initialize()
            
            logger.info(f"Embedding engine initialized with model: {self.config.embedding_model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding engine: {e}")
            raise
    
    async def _init_vector_engine(self):
        """Initialize vector search engine."""
        try:
            vector_config = VectorSearchConfig(
                collection_name=self.config.qdrant_collection,
                vector_size=self.config.embedding_dim,
                enable_quantization=self.config.enable_quantization,
                search_batch_size=self.config.batch_size
            )
            
            # Use code-specific vector engine
            self.vector_engine = CodeVectorEngine(vector_config)
            await self.vector_engine.initialize()
            
            logger.info(f"Vector engine initialized with collection: {self.config.qdrant_collection}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector engine: {e}")
            raise
    
    async def _init_graph_engine(self):
        """Initialize graph intelligence engine."""
        try:
            graph_config = GraphConfig(
                use_supabase_backend=True,
                graph_collection=f"{self.config.qdrant_collection}_graph",
                enable_ast_relationships=self.config.enable_ast_chunking,
                batch_size=self.config.batch_size
            )
            
            self.graph_engine = GraphIntelligenceEngine(graph_config)
            await self.graph_engine.initialize()
            
            logger.info("Graph intelligence engine initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize graph engine: {e}")
            raise
    
    async def _init_chunking_systems(self):
        """Initialize enhanced chunking systems using ai framework."""
        try:
            # Import enhanced chunking components
            from .chunking import EnhancedChunker, HierarchicalChunker, create_adaptive_chunker
            
            # Create adaptive chunker for primary use
            self.primary_chunker = create_adaptive_chunker(
                language="python",  # Will be dynamic based on file
                content_size=2048,
                use_case="code_search"
            )
            
            # Hierarchical chunker for multi-level analysis using ai framework
            self.hierarchical_chunker = HierarchicalChunker(
                chunk_sizes=self.config.chunk_sizes,
                chunker_types=['token', 'sentence', 'semantic', 'recursive'],
                overlap_ratio=self.config.overlap_ratio,
                embedding_model=self.embedding_model
            )
            
            # Specialized chunkers using ai framework
            self.chunkers = {
                "primary": self.primary_chunker,
                "hierarchical": self.hierarchical_chunker,
                "token": EnhancedChunker(
                    chunker_type='token',
                    chunk_size=1024,
                    chunk_overlap=128,
                    tokenizer="gpt2"
                ),
                "semantic": EnhancedChunker(
                    chunker_type='semantic',
                    chunk_size=1536,
                    chunk_overlap=256,
                    embedding_model=self.embedding_model
                )
            }
            
            # Add sentence chunker for text processing
            if self.config.enable_semantic_chunking:
                self.chunkers["sentence"] = EnhancedChunker(
                    chunker_type='sentence',
                    chunk_size=1024,
                    chunk_overlap=128
                )
            
            logger.info(f"Enhanced ai framework chunking initialized with {len(self.chunkers)} chunkers")
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced chunking systems: {e}")
            # Fallback to basic chunking
            self.chunkers = {
                "primary": EnhancedChunker(chunker_type='token', chunk_size=1024),
                "hierarchical": HierarchicalChunker(chunk_sizes=[512, 1024])
            }
            logger.warning("Using fallback chunking configuration")
    
    async def _init_quality_systems(self):
        """Initialize quality analysis systems."""
        try:
            if self.config.enable_quality_analysis:
                # Import quality analysis functions from enhanced chunking
                from .chunking import analyze_chunking_quality
                self.analyze_chunking_quality = analyze_chunking_quality
                logger.info("Enhanced quality analysis systems initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize quality systems: {e}")
            self.analyze_chunking_quality = None
    
    async def index_repository(self, repo_path: str, repo_url: Optional[str] = None) -> Dict[str, Any]:
        """Index a complete repository with state-of-the-art techniques."""
        self.performance_tracker.start_monitoring()
        
        try:
            with self.performance_tracker.track_operation("indexing"):
                result = await self._index_repository_internal(repo_path, repo_url)
            
            # Calculate final metrics
            self._calculate_final_metrics(result)
            
            return {
                "indexing_result": result,
                "performance_metrics": self.performance_tracker.metrics,
                "context_stats": self.context_optimizer.context_stats,
                "embedding_stats": self.embedding_engine.get_embedding_stats() if self.embedding_engine else {},
                "vector_stats": self.vector_engine.get_search_stats() if self.vector_engine else {},
                "graph_stats": await self.graph_engine.get_graph_statistics() if self.graph_engine else {},
                "quality_report": await self._generate_quality_report(),
                "token_usage": self.performance_tracker.token_history[-10:] if self.performance_tracker.token_history else []
            }
            
        finally:
            self.performance_tracker.stop_monitoring()
    
    async def _index_repository_internal(self, repo_path: str, repo_url: Optional[str]) -> Dict[str, Any]:
        """Internal repository indexing with advanced techniques."""
        repo_path = Path(repo_path)
        
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        # Collect all source files with language detection
        source_files = self._collect_source_files_with_metadata(repo_path)
        logger.info(f"Found {len(source_files)} source files across {len(set(f['language'] for f in source_files))} languages")
        
        # Initialize graph relationship extractor
        relationship_extractor = CodeRelationshipExtractor(self.graph_engine) if self.graph_engine else None
        
        # Process files with advanced indexing
        indexing_results = []
        graph_nodes = []
        graph_edges = []
        
        # Use async processing for better performance
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def process_file(file_info: Dict[str, Any]):
            async with semaphore:
                return await self._index_file_advanced(file_info, relationship_extractor)
        
        # Process files in batches
        batch_size = min(self.config.batch_size, len(source_files))
        for i in range(0, len(source_files), batch_size):
            batch = source_files[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [process_file(file_info) for file_info in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"File processing error: {result}")
                else:
                    indexing_results.append(result["indexing"])
                    if "graph_nodes" in result:
                        graph_nodes.extend(result["graph_nodes"])
                    if "graph_edges" in result:
                        graph_edges.extend(result["graph_edges"])
        
        # Build graph relationships
        if self.graph_engine and graph_nodes:
            await self._build_graph_index(graph_nodes, graph_edges)
        
        return {
            "repository_path": str(repo_path),
            "repository_url": repo_url,
            "total_files": len(source_files),
            "processed_files": len(indexing_results),
            "languages_detected": list(set(f['language'] for f in source_files)),
            "indexing_results": indexing_results,
            "graph_nodes_created": len(graph_nodes),
            "graph_edges_created": len(graph_edges),
            "timestamp": datetime.now().isoformat(),
            "indexer_version": "2.0"
        }
    
    def _collect_source_files_with_metadata(self, repo_path: Path) -> List[Dict[str, Any]]:
        """Collect source files with enhanced metadata."""
        # Enhanced file extensions mapping
        language_extensions = {
            '.py': 'python', '.pyx': 'python', '.pyi': 'python',
            '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript',
            '.ts': 'typescript', '.tsx': 'typescript',
            '.java': 'java', '.kt': 'kotlin', '.scala': 'scala',
            '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.c++': 'cpp',
            '.c': 'c', '.h': 'c', '.hpp': 'cpp',
            '.cs': 'csharp', '.vb': 'vb',
            '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
            '.swift': 'swift', '.m': 'objc', '.mm': 'objcpp',
            '.sql': 'sql', '.sh': 'shell', '.bash': 'shell',
            '.md': 'markdown', '.rst': 'rst', '.tex': 'latex',
            '.yml': 'yaml', '.yaml': 'yaml', '.json': 'json',
            '.xml': 'xml', '.html': 'html', '.htm': 'html', '.css': 'css',
            '.r': 'r', '.R': 'r', '.jl': 'julia', '.m': 'matlab',
            '.pl': 'perl', '.lua': 'lua', '.dart': 'dart'
        }
        
        source_files = []
        
        for file_path in repo_path.rglob('*'):
            if (file_path.is_file() and 
                not self._should_ignore_file(file_path)):
                
                extension = file_path.suffix.lower()
                language = language_extensions.get(extension, 'unknown')
                
                # Only include known languages or documentation
                if language != 'unknown' or extension in ['.md', '.rst', '.txt']:
                    file_info = {
                        'path': file_path,
                        'language': language,
                        'extension': extension,
                        'size': file_path.stat().st_size,
                        'relative_path': str(file_path.relative_to(repo_path))
                    }
                    source_files.append(file_info)
        
        # Sort by importance (prioritize main files and smaller files first)
        def file_priority(file_info):
            path = file_info['path']
            size = file_info['size']
            language = file_info['language']
            
            priority = 0
            
            # Prioritize by file importance
            if path.name in {'__init__.py', 'main.py', 'index.js', 'app.py', 'main.java'}:
                priority += 1000
            elif 'main' in path.name.lower() or 'index' in path.name.lower():
                priority += 500
            
            # Prioritize by language
            lang_priority = {
                'python': 100, 'javascript': 90, 'typescript': 85,
                'java': 80, 'cpp': 75, 'go': 70, 'rust': 65
            }
            priority += lang_priority.get(language, 0)
            
            # Smaller files first (easier to process)
            if size < 10000:  # < 10KB
                priority += 50
            elif size < 50000:  # < 50KB  
                priority += 25
            
            return -priority  # Negative for descending sort
        
        return sorted(source_files, key=file_priority)
    
    async def _index_file_advanced(
        self, 
        file_info: Dict[str, Any], 
        relationship_extractor: Optional[CodeRelationshipExtractor]
    ) -> Dict[str, Any]:
        """Index a single file with advanced techniques."""
        file_path = file_info['path']
        language = file_info['language']
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip():
                return {"indexing": {"file_path": str(file_path), "status": "empty"}}
            
            # Track token usage
            estimated_tokens = len(content.split()) * 1.3
            self.performance_tracker.track_tokens(
                model_name=self.config.embedding_model,
                input_tokens=int(estimated_tokens),
                output_tokens=0,
                max_context=self.config.context_window,
                context_used=min(int(estimated_tokens), self.config.context_window)
            )
            
            # Create advanced chunks
            chunks = await self._create_advanced_chunks(content, file_path, language)
            
            # Generate embeddings for chunks
            embeddings_data = []
            if self.embedding_engine and chunks:
                await self._embed_chunks(chunks, embeddings_data, language)
            
            # Store in vector database
            vector_ids = []
            if self.vector_engine and embeddings_data:
                vector_ids = await self._store_in_vector_db(embeddings_data, file_info)
            
            # Store in knowledge base
            knowledge_ids = []
            if self.knowledge and chunks:
                knowledge_ids = await self._store_in_knowledge_base(chunks, file_info)
            
            # Extract graph relationships
            graph_nodes = []
            graph_edges = []
            if relationship_extractor:
                try:
                    nodes, edges = await relationship_extractor.extract_relationships(
                        str(file_path), content, language
                    )
                    graph_nodes.extend(nodes)
                    graph_edges.extend(edges)
                except Exception as e:
                    logger.warning(f"Graph extraction failed for {file_path}: {e}")
            
            # Generate quality report
            quality_score = 0.0
            if self.quality_analyzer and chunks:
                quality_score = await self._analyze_chunk_quality(chunks)
            
            result = {
                "indexing": {
                    "file_path": str(file_path),
                    "language": language,
                    "file_size": len(content),
                    "estimated_tokens": int(estimated_tokens),
                    "chunks_created": len(chunks),
                    "embeddings_created": len(embeddings_data),
                    "vector_ids": vector_ids,
                    "knowledge_ids": knowledge_ids,
                    "quality_score": quality_score,
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            if graph_nodes:
                result["graph_nodes"] = graph_nodes
            if graph_edges:
                result["graph_edges"] = graph_edges
            
            return result
            
        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}")
            return {
                "indexing": {
                    "file_path": str(file_path),
                    "error": str(e),
                    "status": "error",
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def _create_advanced_chunks(
        self, 
        content: str, 
        file_path: Path, 
        language: str
    ) -> List[Dict[str, Any]]:
        """Create chunks using enhanced ai framework chunking strategies."""
        all_chunks = []
        
        try:
            # Import adaptive chunking for language-specific optimization
            from .chunking import create_adaptive_chunker
            
            # Create language-specific adaptive chunker
            adaptive_chunker = create_adaptive_chunker(
                language=language,
                content_size=len(content),
                use_case="code_search"
            )
            
            # Primary chunking with adaptive strategy
            primary_result = adaptive_chunker.chunk(content, file_path)
            primary_chunks = self._convert_chunking_result(primary_result, "adaptive")
            all_chunks.extend(primary_chunks)
            
            # Hierarchical chunking for multi-level analysis
            if "hierarchical" in self.chunkers:
                hierarchical_result = self.chunkers["hierarchical"].chunk(content, file_path)
                hierarchical_chunks = self._convert_chunking_result(hierarchical_result, "hierarchical")
                all_chunks.extend(hierarchical_chunks)
            
            # Semantic chunking for better context understanding
            if "semantic" in self.chunkers and self.config.enable_semantic_chunking:
                try:
                    semantic_result = self.chunkers["semantic"].chunk(content, file_path)
                    semantic_chunks = self._convert_chunking_result(semantic_result, "semantic")
                    all_chunks.extend(semantic_chunks)
                except Exception as e:
                    logger.debug(f"Semantic chunking failed for {file_path}: {e}")
            
            # Token-based chunking as baseline
            if "token" in self.chunkers:
                token_result = self.chunkers["token"].chunk(content, file_path)
                token_chunks = self._convert_chunking_result(token_result, "token")
                all_chunks.extend(token_chunks)
            
            # Quality analysis
            if self.config.enable_quality_analysis and hasattr(self, 'analyze_chunking_quality'):
                for chunk in all_chunks:
                    if 'chunking_result' in chunk:
                        quality_analysis = self.analyze_chunking_quality(chunk['chunking_result'])
                        chunk['quality_analysis'] = quality_analysis
                        chunk['quality_score'] = quality_analysis.get('overall_score', 0.5)
            
            # Deduplicate and optimize chunks
            if self.config.enable_deduplication:
                all_chunks = self._deduplicate_enhanced_chunks(all_chunks)
            
            # Optimize context for each chunk
            optimized_chunks = []
            for chunk in all_chunks:
                optimized_chunk = await self._optimize_enhanced_chunk_context(chunk)
                optimized_chunks.append(optimized_chunk)
            
            logger.info(f"Created {len(optimized_chunks)} enhanced chunks from {len(content)} characters")
            return optimized_chunks
            
        except Exception as e:
            logger.error(f"Error creating enhanced chunks: {e}")
            # Fallback to basic chunking
            return await self._fallback_chunking(content, file_path, language)
    
    def _convert_chunking_result(self, chunking_result, chunking_strategy: str) -> List[Dict[str, Any]]:
        """Convert ChunkingResult to the format expected by the indexer."""
        converted_chunks = []
        
        for chunk in chunking_result.chunks:
            converted_chunk = {
                'content': chunk['content'],
                'chunk_type': chunking_strategy,
                'metadata': chunk['metadata'],
                'chunk_info': chunk.get('chunk_info', {}),
                'chunking_result': chunking_result,
                'chunking_strategy': chunking_strategy,
                'quality_score': chunk['metadata'].importance_score,
                'semantic_tags': chunk['metadata'].semantic_tags,
                'language': chunk['metadata'].language,
                'file_path': str(chunk.get('file_path', ''))
            }
            converted_chunks.append(converted_chunk)
        
        return converted_chunks
    
    def _deduplicate_enhanced_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate enhanced chunks based on content similarity."""
        if not chunks:
            return chunks
        
        # Simple content-based deduplication
        seen_contents = set()
        deduplicated = []
        
        for chunk in chunks:
            content_hash = hash(chunk['content'])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                deduplicated.append(chunk)
        
        logger.info(f"Deduplicated {len(chunks)} -> {len(deduplicated)} chunks")
        return deduplicated
    
    async def _optimize_enhanced_chunk_context(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize context for enhanced chunks."""
        try:
            # Use context optimizer from ai framework
            if hasattr(self, 'context_optimizer') and self.context_optimizer:
                optimized_content = self.context_optimizer.optimize_chunk_context(
                    chunk['content'],
                    max_tokens=self.config.context_window
                )
                chunk['optimized_content'] = optimized_content
                chunk['context_optimized'] = True
            
            # Add performance metrics
            chunk['processing_timestamp'] = datetime.now().isoformat()
            chunk['token_count'] = chunk.get('metadata', {}).token_count or len(chunk['content'].split())
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error optimizing chunk context: {e}")
            chunk['context_optimized'] = False
            return chunk
    
    async def _fallback_chunking(self, content: str, file_path: Path, language: str) -> List[Dict[str, Any]]:
        """Fallback chunking using basic ai framework chunking."""
        try:
            from .chunking import EnhancedChunker
            
            fallback_chunker = EnhancedChunker(
                chunker_type='token',
                chunk_size=1024,
                chunk_overlap=128
            )
            
            result = fallback_chunker.chunk(content, file_path)
            return self._convert_chunking_result(result, "fallback")
            
        except Exception as e:
            logger.error(f"Fallback chunking failed: {e}")
            # Ultimate fallback - simple text splitting
            words = content.split()
            chunk_size = 200
            chunks = []
            
            for i in range(0, len(words), chunk_size):
                chunk_content = ' '.join(words[i:i + chunk_size])
                chunks.append({
                    'content': chunk_content,
                    'chunk_type': 'emergency_fallback',
                    'file_path': str(file_path),
                    'language': language,
                    'quality_score': 0.3,
                    'context_optimized': False
                })
            
            return chunks
    
    async def _embed_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        embeddings_data: List[Dict[str, Any]], 
        language: str
    ):
        """Generate embeddings for chunks using code-specific engine."""
        try:
            for chunk in chunks:
                content = chunk.get("content", "")
                if not content.strip():
                    continue
                
                # Use code-specific embedding
                embedding, metadata = await self.embedding_engine.embed_code(
                    code=content,
                    language=language,
                    include_context=True
                )
                
                embeddings_data.append({
                    "content": content,
                    "embedding": embedding,
                    "metadata": {**chunk, **metadata},
                    "chunk_id": chunk.get("chunk_id", f"chunk_{len(embeddings_data)}")
                })
                
        except Exception as e:
            logger.error(f"Error embedding chunks: {e}")
    
    async def _store_in_vector_db(
        self, 
        embeddings_data: List[Dict[str, Any]], 
        file_info: Dict[str, Any]
    ) -> List[str]:
        """Store embeddings in vector database."""
        try:
            vector_ids = []
            
            # Prepare vectors for batch storage
            vectors_batch = []
            for embed_data in embeddings_data:
                vector_id = f"{file_info['relative_path']}_{embed_data['chunk_id']}"
                
                payload = {
                    "content": embed_data["content"],
                    "file_path": file_info["relative_path"],
                    "language": file_info["language"],
                    "chunk_type": embed_data["metadata"].get("chunk_type", "unknown"),
                    "file_size": file_info["size"],
                    **embed_data["metadata"]
                }
                
                vectors_batch.append((vector_id, embed_data["embedding"], payload))
            
            # Store vectors in batch
            if vectors_batch:
                stored_ids = await self.vector_engine.store_vectors_batch(vectors_batch)
                vector_ids.extend(stored_ids)
            
            return vector_ids
            
        except Exception as e:
            logger.error(f"Error storing in vector database: {e}")
            return []
    
    async def _store_in_knowledge_base(
        self, 
        chunks: List[Dict[str, Any]], 
        file_info: Dict[str, Any]
    ) -> List[str]:
        """Store chunks in knowledge base using ai framework."""
        try:
            knowledge_ids = []
            
            for chunk in chunks:
                content = chunk.get("content", "")
                if not content.strip():
                    continue
                
                # Prepare metadata
                metadata = {
                    "file_path": file_info["relative_path"],
                    "language": file_info["language"],
                    "chunk_type": chunk.get("chunk_type", "text"),
                    "file_size": file_info["size"],
                    "indexer_version": "2.0"
                }
                
                # Store using knowledge system
                result = self.knowledge.store(
                    content=content,
                    metadata=metadata
                )
                
                if result:
                    knowledge_ids.extend([r.get("id") for r in result if r.get("id")])
            
            return knowledge_ids
            
        except Exception as e:
            logger.error(f"Error storing in knowledge base: {e}")
            return []
    
    async def _build_graph_index(self, nodes: List, edges: List):
        """Build graph index from extracted relationships."""
        try:
            # Add nodes to graph
            for node in nodes:
                await self.graph_engine.add_node(node)
            
            # Add edges to graph  
            for edge in edges:
                await self.graph_engine.add_edge(edge)
            
            logger.info(f"Built graph index with {len(nodes)} nodes and {len(edges)} edges")
            
        except Exception as e:
            logger.error(f"Error building graph index: {e}")
    
    async def _analyze_chunk_quality(self, chunks: List[Dict[str, Any]]) -> float:
        """Analyze quality of chunks."""
        if not self.quality_analyzer or not chunks:
            return 0.0
        
        try:
            total_score = 0.0
            valid_chunks = 0
            
            for chunk in chunks:
                content = chunk.get("content", "")
                if content.strip():
                    score = self.quality_analyzer.analyze_chunk_quality(chunk)
                    total_score += score
                    valid_chunks += 1
            
            return total_score / max(valid_chunks, 1)
            
        except Exception as e:
            logger.error(f"Error analyzing chunk quality: {e}")
            return 0.0
    
    async def _generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        try:
            return {
                "overall_quality": "high" if self.performance_tracker.metrics.avg_chunk_quality > 0.75 else "medium",
                "chunk_quality_avg": self.performance_tracker.metrics.avg_chunk_quality,
                "deduplication_ratio": self.performance_tracker.metrics.deduplication_ratio,
                "context_utilization": f"{self.performance_tracker.metrics.context_utilization:.1%}",
                "quality_checks_enabled": self.config.enable_quality_analysis
            }
        except Exception as e:
            logger.error(f"Error generating quality report: {e}")
            return {}
    
    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks."""
        seen_content = set()
        unique_chunks = []
        
        for chunk in chunks:
            content = chunk.get("content", "").strip()
            content_hash = hash(content)
            
            if content_hash not in seen_content and content:
                seen_content.add(content_hash)
                unique_chunks.append(chunk)
        
        dedup_ratio = 1.0 - (len(unique_chunks) / max(len(chunks), 1))
        self.performance_tracker.metrics.deduplication_ratio = dedup_ratio
        
        return unique_chunks
    
    async def _optimize_chunk_context(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize chunk for context usage."""
        try:
            content = chunk.get("content", "")
            
            # Use context optimizer to determine optimal size
            optimal_chunks, context_stats = self.context_optimizer.calculate_optimal_context(
                [content], ""
            )
            
            if optimal_chunks:
                chunk["content"] = optimal_chunks[0]
                chunk["context_optimized"] = True
                chunk["context_stats"] = {
                    "utilization": context_stats.utilization_percentage,
                    "compression": context_stats.compression_achieved
                }
            
            return chunk
            
        except Exception as e:
            logger.debug(f"Context optimization failed: {e}")
            return chunk
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored during indexing."""
        ignore_patterns = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.pytest_cache', 'coverage', '.coverage',
            '.idea', '.vscode', 'target', 'bin', 'obj', 'out',
            'logs', 'tmp', 'temp', '.DS_Store', 'Thumbs.db'
        }
        
        # Check if any ignore pattern is in the file path
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in ignore_patterns)
    
    def _calculate_final_metrics(self, result: Dict[str, Any]):
        """Calculate final performance metrics."""
        if self.performance_tracker.metrics.total_time > 0:
            processed_files = result.get("processed_files", 0)
            total_tokens = self.performance_tracker.metrics.total_tokens_input
            
            self.performance_tracker.metrics.files_per_second = processed_files / self.performance_tracker.metrics.total_time
            self.performance_tracker.metrics.tokens_per_second = total_tokens / self.performance_tracker.metrics.total_time
            
            # Context utilization
            if self.performance_tracker.metrics.context_tokens_available > 0:
                self.performance_tracker.metrics.context_utilization = (
                    self.performance_tracker.metrics.context_tokens_used / 
                    self.performance_tracker.metrics.context_tokens_available
                )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            "performance_metrics": {
                "timing": {
                    "total_time": f"{self.performance_tracker.metrics.total_time:.2f}s",
                    "indexing_time": f"{self.performance_tracker.metrics.indexing_time:.2f}s",
                    "embedding_time": f"{self.performance_tracker.metrics.embedding_time:.2f}s",
                    "storage_time": f"{self.performance_tracker.metrics.storage_time:.2f}s"
                },
                "resource_usage": {
                    "peak_memory": f"{self.performance_tracker.metrics.peak_memory_mb:.2f} MB",
                    "avg_memory": f"{self.performance_tracker.metrics.avg_memory_mb:.2f} MB",
                    "cpu_usage": f"{self.performance_tracker.metrics.cpu_usage_percent:.1f}%"
                },
                "throughput": {
                    "files_per_second": f"{self.performance_tracker.metrics.files_per_second:.2f}",
                    "tokens_per_second": f"{self.performance_tracker.metrics.tokens_per_second:.0f}",
                    "chunks_per_second": f"{self.performance_tracker.metrics.chunks_per_second:.2f}"
                }
            },
            "context_optimization": {
                "utilization": f"{self.performance_tracker.metrics.context_utilization:.1%}",
                "compression_ratio": f"{self.performance_tracker.metrics.context_compression_ratio:.2f}",
                "optimal_chunks": self.performance_tracker.metrics.optimal_context_chunks
            },
            "token_statistics": {
                "total_input": self.performance_tracker.metrics.total_tokens_input,
                "total_output": self.performance_tracker.metrics.total_tokens_output,
                "context_used": self.performance_tracker.metrics.context_tokens_used,
                "context_available": self.performance_tracker.metrics.context_tokens_available,
                "efficiency": f"{(self.performance_tracker.metrics.context_tokens_used / max(self.performance_tracker.metrics.context_tokens_available, 1)):.1%}"
            }
        }
        
        # Add engine-specific stats
        if self.embedding_engine:
            summary["embedding_stats"] = self.embedding_engine.get_embedding_stats()
        
        if self.vector_engine:
            summary["vector_stats"] = self.vector_engine.get_search_stats()
        
        return summary
    
    async def search_codebase(
        self,
        query: str,
        search_type: str = "hybrid",  # "text", "vector", "hybrid", "graph"
        languages: Optional[List[str]] = None,
        file_patterns: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search indexed codebase with multiple search strategies."""
        
        try:
            results = {"query": query, "search_type": search_type, "results": []}
            
            if search_type == "text" or search_type == "hybrid":
                # Use knowledge base search
                if self.knowledge:
                    text_results = self.knowledge.search(query, limit=limit)
                    results["results"].extend([
                        {
                            "type": "text",
                            "content": r.get("memory", ""),
                            "score": r.get("score", 0.0),
                            "metadata": r.get("metadata", {})
                        }
                        for r in text_results
                    ])
            
            if search_type == "vector" or search_type == "hybrid":
                # Use vector search
                if self.vector_engine:
                    vector_results = await self.vector_engine.search_by_text(
                        query, limit=limit
                    )
                    results["results"].extend([
                        {
                            "type": "vector",
                            "content": r.payload.get("content", ""),
                            "score": r.score or 0.0,
                            "metadata": r.payload
                        }
                        for r in vector_results
                    ])
            
            if search_type == "graph":
                # Use graph search (would need implementation)
                if self.graph_engine:
                    # Placeholder for graph search
                    results["results"].append({
                        "type": "graph",
                        "content": f"Graph search for '{query}' not fully implemented",
                        "score": 0.0,
                        "metadata": {}
                    })
            
            # Sort by score if hybrid search
            if search_type == "hybrid":
                results["results"].sort(key=lambda x: x["score"], reverse=True)
                results["results"] = results["results"][:limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching codebase: {e}")
            return {"query": query, "error": str(e), "results": []}
