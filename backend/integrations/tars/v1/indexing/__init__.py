"""
TARS v1 Advanced Codebase Indexing System
==========================================

State-of-the-Art codebase indexing for 2025 with:
✅ Enhanced ai framework chunking integration (Chonkie)
✅ Multiple chunking strategies (token, sentence, semantic, etc.)
✅ Hierarchical multi-level chunking with context preservation
✅ Advanced embedding models (Jina Code V2, UniXcoder, etc.)
✅ Quantized vector search with Qdrant Cloud
✅ Graph-based code intelligence with Supabase PostgreSQL
✅ Real-time performance & context tracking
✅ Production-ready scalability & optimization

Built on the ai framework with Supabase PostgreSQL and Qdrant Cloud.
Uses ai.knowledge.Chunking with Chonkie library for optimal chunking.
"""

# Core indexing system
from .core import (
    CodebaseIndexer,
    IndexingConfig,
    PerformanceTracker,
    PerformanceMetrics,
    TokenStats,
    ContextStats,
    ContextOptimizer
)

# Advanced chunking strategies using ai framework
from .chunking import (
    ChunkMetadata,
    ChunkingResult,
    EnhancedChunker,
    HierarchicalChunker,
    create_adaptive_chunker,
    create_multi_strategy_chunker,
    optimize_chunker_for_search,
    analyze_chunking_quality
)

# Embedding engine with code specialization
from .embedding import (
    AdvancedEmbeddingEngine,
    CodeSpecificEmbeddingEngine,
    EmbeddingConfig,
    EmbeddingStats,
    EmbeddingCache
)

# Vector database with quantized search
from .vector import (
    AdvancedVectorEngine,
    CodeVectorEngine,
    VectorSearchConfig,
    VectorRecord,
    SearchStats,
    VectorSearchCache
)

# Graph-based code intelligence
from .graph import (
    GraphIntelligenceEngine,
    CodeRelationshipExtractor,
    GraphConfig,
    GraphNode,
    GraphEdge,
    GraphStats,
    GraphCache
)

# Main exports for easy usage
__all__ = [
    # Core system
    'CodebaseIndexer',
    'IndexingConfig',
    'PerformanceTracker',
    'ContextOptimizer',
    
    # Chunking
    'EnhancedChunker',
    'HierarchicalChunker',
    'create_adaptive_chunker',
    'create_multi_strategy_chunker',
    'analyze_chunking_quality',
    
    # Embedding
    'AdvancedEmbeddingEngine',
    'CodeSpecificEmbeddingEngine',
    'EmbeddingConfig',
    
    # Vector search
    'AdvancedVectorEngine',
    'CodeVectorEngine', 
    'VectorSearchConfig',
    
    # Graph intelligence
    'GraphIntelligenceEngine',
    'CodeRelationshipExtractor',
    'GraphConfig',
    
    # Data structures
    'PerformanceMetrics',
    'TokenStats', 
    'ContextStats',
    'ChunkMetadata',
    'ChunkingResult',
    'VectorRecord',
    'GraphNode',
    'GraphEdge'
]

# Version and metadata
__version__ = "2.0.0"
__author__ = "TARS AI"
__description__ = "State-of-the-Art Codebase Indexing for 2025"

# Feature flags
FEATURES = {
    "hybrid_indexing": True,
    "hierarchical_chunking": True,
    "ast_parsing": True,
    "semantic_embeddings": True,
    "quantized_vectors": True,
    "graph_intelligence": True,
    "context_optimization": True,
    "performance_tracking": True,
    "quality_analysis": True,
    "multi_language": True,
    "production_ready": True
}

def get_version():
    """Get version information."""
    return {
        "version": __version__,
        "description": __description__, 
        "features": FEATURES,
        "ai_framework": "integrated",
        "databases": ["Supabase PostgreSQL", "Qdrant Cloud"],
        "embedding_models": [
            "jina-code-v2",
            "qodo-embed-1", 
            "unicoder",
            "graphcodebert",
            "voyagecode3"
        ]
    }

def create_production_indexer(
    qdrant_url: str = None,
    qdrant_api_key: str = None,
    supabase_url: str = None, 
    supabase_key: str = None,
    **kwargs
) -> CodebaseIndexer:
    """
    Create a production-ready codebase indexer with optimal settings.
    
    Args:
        qdrant_url: Qdrant Cloud URL (or from QDRANT_URL env var)
        qdrant_api_key: Qdrant API key (or from QDRANT_API_KEY env var)
        supabase_url: Supabase URL (or from SUPABASE_URL env var)
        supabase_key: Supabase key (or from SUPABASE_ANON_KEY env var)
        **kwargs: Additional configuration options
        
    Returns:
        Configured CodebaseIndexer ready for production use
    """
    config = IndexingConfig(
        # Production embedding model
        embedding_model=kwargs.get("embedding_model", "jina-code-v2"),
        
        # Optimized chunking
        chunk_sizes=kwargs.get("chunk_sizes", [512, 1024, 2048, 4096]),
        enable_semantic_chunking=kwargs.get("enable_semantic_chunking", True),
        enable_ast_chunking=kwargs.get("enable_ast_chunking", True),
        
        # Performance optimization
        max_workers=kwargs.get("max_workers", 16),
        batch_size=kwargs.get("batch_size", 128),
        enable_quantization=kwargs.get("enable_quantization", True),
        cache_size=kwargs.get("cache_size", 50000),
        
        # Quality settings
        min_chunk_quality=kwargs.get("min_chunk_quality", 0.75),
        enable_deduplication=kwargs.get("enable_deduplication", True),
        enable_quality_analysis=kwargs.get("enable_quality_analysis", True),
        
        # Database settings
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        
        # Advanced features
        enable_graph_indexing=kwargs.get("enable_graph_indexing", True),
        enable_vector_search=kwargs.get("enable_vector_search", True),
        enable_hybrid_search=kwargs.get("enable_hybrid_search", True)
    )
    
    return CodebaseIndexer(config)

async def quick_index(
    repo_path: str,
    repo_url: str = None,
    **config_kwargs
) -> dict:
    """
    Quick indexing function for rapid deployment.
    
    Args:
        repo_path: Path to repository to index
        repo_url: Optional repository URL
        **config_kwargs: Configuration overrides
        
    Returns:
        Indexing results with performance metrics
    """
    # Create and initialize indexer
    indexer = create_production_indexer(**config_kwargs)
    await indexer.initialize()
    
    # Index repository
    results = await indexer.index_repository(repo_path, repo_url)
    
    return results

# Export quick functions for convenience
__all__.extend(['create_production_indexer', 'quick_index', 'get_version'])

# Performance and debugging utilities
def get_performance_recommendations(metrics: PerformanceMetrics) -> list:
    """Get performance optimization recommendations based on metrics."""
    recommendations = []
    
    if metrics.context_utilization < 0.7:
        recommendations.append("Consider increasing chunk sizes for better context utilization")
    
    if metrics.avg_chunk_quality < 0.75:
        recommendations.append("Enable quality analysis and increase minimum quality threshold")
    
    if metrics.deduplication_ratio > 0.3:
        recommendations.append("High duplication detected - consider improving deduplication strategy")
    
    if metrics.peak_memory_mb > 4096:
        recommendations.append("High memory usage - consider reducing batch sizes or enabling lazy loading")
    
    if metrics.files_per_second < 1.0:
        recommendations.append("Low throughput - consider increasing max_workers or optimizing chunking")
    
    return recommendations

def optimize_for_language(language: str) -> dict:
    """Get optimized configuration for specific programming languages."""
    
    language_configs = {
        "python": {
            "embedding_model": "jina-code-v2",
            "chunk_sizes": [256, 512, 1024, 2048],
            "enable_ast_chunking": True,
            "enable_semantic_chunking": True
        },
        "javascript": {
            "embedding_model": "jina-code-v2", 
            "chunk_sizes": [512, 1024, 2048],
            "enable_ast_chunking": True,
            "enable_semantic_chunking": True
        },
        "typescript": {
            "embedding_model": "jina-code-v2",
            "chunk_sizes": [512, 1024, 2048, 4096], 
            "enable_ast_chunking": True,
            "enable_semantic_chunking": True
        },
        "java": {
            "embedding_model": "qodo-embed-1",
            "chunk_sizes": [768, 1536, 3072],
            "enable_ast_chunking": True,
            "enable_semantic_chunking": True
        },
        "cpp": {
            "embedding_model": "graphcodebert",
            "chunk_sizes": [1024, 2048, 4096],
            "enable_ast_chunking": False,  # More complex AST
            "enable_semantic_chunking": True
        }
    }
    
    return language_configs.get(language.lower(), language_configs["python"])

# Export utility functions
__all__.extend(['get_performance_recommendations', 'optimize_for_language'])
