"""
Performance Metrics API Routes

API endpoints for monitoring and analyzing performance optimization metrics.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
import logging
from datetime import datetime

# Import services
from services.performance_optimization_service import get_performance_service
from services.optimized_repo_cache import get_optimized_repo_cache
from services.metrics_collection_service import get_metrics_collector

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/performance", tags=["performance-metrics"])

# Get service instances
performance_service = get_performance_service()
repo_cache = get_optimized_repo_cache()
metrics_collector = get_metrics_collector()


@router.get("/metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """
    Get comprehensive performance metrics.
    
    Returns detailed metrics about caching, connection pools,
    request batching, and system performance.
    """
    try:
        # Get metrics from performance service
        perf_metrics = performance_service.get_performance_metrics()
        
        # Get repository cache statistics
        cache_stats = repo_cache.get_cache_statistics()
        
        # Combine all metrics
        combined_metrics = {
            "timestamp": datetime.now().isoformat(),
            "performance_optimization": perf_metrics,
            "repository_cache": cache_stats,
            "system_health": {
                "status": "healthy",
                "uptime_seconds": 0,  # Would be calculated from service start time
                "memory_usage_mb": 0,  # Would be from system monitoring
            }
        }
        
        return combined_metrics
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/cache/stats")
async def get_cache_statistics() -> Dict[str, Any]:
    """
    Get detailed cache statistics.
    
    Returns information about cache hit rates, sizes, and efficiency.
    """
    try:
        cache_stats = repo_cache.get_cache_statistics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cache_statistics": cache_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}"
        )


@router.get("/connection-pools")
async def get_connection_pool_stats() -> Dict[str, Any]:
    """
    Get connection pool statistics.
    
    Returns information about Redis connection pools and their usage.
    """
    try:
        pool_stats = performance_service.connection_pool_manager.get_pool_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "connection_pools": pool_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting connection pool stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection pool stats: {str(e)}"
        )


@router.post("/cache/warm")
async def warm_repository_cache(
    repositories: Optional[list] = None
) -> Dict[str, Any]:
    """
    Warm the repository cache with specified repositories.
    
    Args:
        repositories: List of repository names to warm (optional)
        
    Returns:
        Results of cache warming operation
    """
    try:
        if repositories is None:
            # Use default popular repositories
            repositories = [
                "microsoft/vscode",
                "facebook/react",
                "tensorflow/tensorflow",
                "kubernetes/kubernetes",
                "nodejs/node"
            ]
        
        # Warm cache
        results = await repo_cache.warm_repository_cache(repositories)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "warming_results": results,
            "total_repositories": len(repositories),
            "successful_warmings": sum(1 for success in results.values() if success),
            "failed_warmings": sum(1 for success in results.values() if not success)
        }
        
    except Exception as e:
        logger.error(f"Error warming repository cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to warm repository cache: {str(e)}"
        )


@router.delete("/cache/invalidate/{repo_name}")
async def invalidate_repository_cache(
    repo_name: str,
    branch: str = "main"
) -> Dict[str, Any]:
    """
    Invalidate cache for a specific repository.
    
    Args:
        repo_name: Repository name (owner/repo format)
        branch: Branch name (default: main)
        
    Returns:
        Result of cache invalidation
    """
    try:
        success = await repo_cache.invalidate_repository(repo_name, branch)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "repository": repo_name,
            "branch": branch,
            "invalidated": success,
            "message": f"Cache invalidated for {repo_name}:{branch}" if success else "Failed to invalidate cache"
        }
        
    except Exception as e:
        logger.error(f"Error invalidating repository cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate repository cache: {str(e)}"
        )


@router.get("/health")
async def get_performance_health() -> Dict[str, Any]:
    """
    Get performance system health status.
    
    Returns health information about caching, connection pools, and optimization services.
    """
    try:
        # Check Redis connection health
        redis_client = performance_service.get_redis_client()
        redis_healthy = False
        
        try:
            redis_client.ping()
            redis_healthy = True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
        
        # Get basic metrics
        metrics = performance_service.get_performance_metrics()
        cache_stats = repo_cache.get_cache_statistics()
        
        # Determine overall health
        overall_health = "healthy"
        issues = []
        
        if not redis_healthy:
            overall_health = "degraded"
            issues.append("Redis connection issues")
        
        # Check cache hit rate
        hit_rate = metrics.get("cache_metrics", {}).get("hit_rate", 0)
        if hit_rate < 50:  # Less than 50% hit rate
            if overall_health == "healthy":
                overall_health = "warning"
            issues.append("Low cache hit rate")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": overall_health,
            "issues": issues,
            "components": {
                "redis": "healthy" if redis_healthy else "unhealthy",
                "cache": "healthy" if hit_rate >= 50 else "warning",
                "connection_pools": "healthy"  # Would check pool health
            },
            "metrics_summary": {
                "cache_hit_rate": hit_rate,
                "total_requests": metrics.get("request_metrics", {}).get("total_requests", 0),
                "avg_response_time_ms": metrics.get("request_metrics", {}).get("avg_response_time_ms", 0),
                "cached_repositories": cache_stats.get("cache_stats", {}).get("cached_repositories", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance health: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "error",
            "issues": [f"Health check failed: {str(e)}"],
            "components": {},
            "metrics_summary": {}
        }


@router.post("/optimize/repository/{repo_name}")
async def optimize_repository_performance(
    repo_name: str,
    branch: str = "main",
    priority: int = 5
) -> Dict[str, Any]:
    """
    Optimize performance for a specific repository.
    
    Args:
        repo_name: Repository name (owner/repo format)
        branch: Branch name (default: main)
        priority: Cache priority (1-10, higher = more important)
        
    Returns:
        Result of optimization operation
    """
    try:
        # Update repository metadata with higher priority
        repo_key = f"{repo_name}:{branch}"
        
        if repo_key in repo_cache._repo_metadata:
            repo_cache._repo_metadata[repo_key].cache_priority = priority
            repo_cache._repo_metadata[repo_key].calculate_prefetch_score()
        
        # Warm cache for this repository
        warm_results = await repo_cache.warm_repository_cache([repo_name])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "repository": repo_name,
            "branch": branch,
            "priority": priority,
            "cache_warmed": warm_results.get(repo_name, False),
            "message": f"Optimization applied for {repo_name}:{branch}"
        }
        
    except Exception as e:
        logger.error(f"Error optimizing repository performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize repository performance: {str(e)}"
        )


@router.get("/benchmarks")
async def run_performance_benchmarks() -> Dict[str, Any]:
    """
    Run performance benchmarks and return results.
    
    Returns benchmark results for various performance components.
    """
    try:
        import time
        import asyncio
        
        benchmarks = {}
        
        # Cache performance benchmark
        cache_start = time.time()
        
        # Test cache operations
        test_data = {"benchmark": "test_data", "timestamp": time.time()}
        cache_key = performance_service.generate_query_hash("benchmark_test")
        
        await performance_service.cache_response(cache_key, test_data)
        cached_result = await performance_service.get_cached_response(cache_key)
        
        cache_time = (time.time() - cache_start) * 1000
        benchmarks["cache_roundtrip_ms"] = cache_time
        benchmarks["cache_success"] = cached_result is not None
        
        # Redis connection benchmark
        redis_start = time.time()
        
        redis_client = performance_service.get_redis_client()
        redis_client.ping()
        
        redis_time = (time.time() - redis_start) * 1000
        benchmarks["redis_ping_ms"] = redis_time
        
        # Batch operation benchmark
        batch_start = time.time()
        
        batch_ops = [
            {"method": "set", "args": [f"bench_key_{i}", f"bench_value_{i}"]}
            for i in range(10)
        ]
        
        await performance_service.batch_redis_operations(batch_ops)
        
        batch_time = (time.time() - batch_start) * 1000
        benchmarks["batch_operations_ms"] = batch_time
        
        return {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": benchmarks,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error running performance benchmarks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run performance benchmarks: {str(e)}"
        )


@router.get("/realtime/{session_id}")
async def get_realtime_metrics(session_id: str) -> Dict[str, Any]:
    """
    Get real-time performance metrics for a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Real-time metrics including token usage, latency, cache performance, and error rates
    """
    try:
        metrics = await metrics_collector.get_real_time_metrics(session_id)
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get real-time metrics: {str(e)}"
        )


@router.post("/realtime/{session_id}/latency")
async def record_latency_metric(
    session_id: str,
    request_id: str,
    latency_ms: float,
    operation_type: str = "chat_request",
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Record a latency metric for a session.
    
    Args:
        session_id: Session identifier
        request_id: Request identifier
        latency_ms: Latency in milliseconds
        operation_type: Type of operation (default: chat_request)
        success: Whether the operation was successful
        metadata: Additional metadata
        
    Returns:
        Confirmation of metric recording
    """
    try:
        await metrics_collector.record_request_latency(
            session_id=session_id,
            request_id=request_id,
            latency_ms=latency_ms,
            operation_type=operation_type,
            success=success,
            metadata=metadata
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "request_id": request_id,
            "latency_ms": latency_ms,
            "recorded": True
        }
        
    except Exception as e:
        logger.error(f"Error recording latency metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record latency metric: {str(e)}"
        )


@router.post("/realtime/{session_id}/tokens")
async def record_token_usage(
    session_id: str,
    request_id: str,
    input_tokens: int,
    output_tokens: int,
    model_name: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record token usage for a session.
    
    Args:
        session_id: Session identifier
        request_id: Request identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model_name: Name of the AI model used
        user_id: User identifier (optional)
        
    Returns:
        Token usage data with cost estimate
    """
    try:
        token_data = await metrics_collector.record_token_usage(
            session_id=session_id,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
            user_id=user_id
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "request_id": request_id,
            "token_data": token_data.to_dict(),
            "recorded": True
        }
        
    except Exception as e:
        logger.error(f"Error recording token usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record token usage: {str(e)}"
        )


@router.post("/realtime/{session_id}/cache")
async def record_cache_metrics(
    session_id: str,
    operation: str,
    hit_rate: float,
    response_time_ms: float,
    cache_size_mb: float,
    eviction_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Record cache performance metrics for a session.
    
    Args:
        session_id: Session identifier
        operation: Cache operation type
        hit_rate: Cache hit rate (0.0 to 1.0)
        response_time_ms: Cache response time in milliseconds
        cache_size_mb: Cache size in megabytes
        eviction_count: Number of cache evictions
        metadata: Additional metadata
        
    Returns:
        Confirmation of metric recording
    """
    try:
        await metrics_collector.record_cache_metrics(
            session_id=session_id,
            operation=operation,
            hit_rate=hit_rate,
            response_time_ms=response_time_ms,
            cache_size_mb=cache_size_mb,
            eviction_count=eviction_count,
            metadata=metadata
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "operation": operation,
            "hit_rate": hit_rate,
            "response_time_ms": response_time_ms,
            "recorded": True
        }
        
    except Exception as e:
        logger.error(f"Error recording cache metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record cache metrics: {str(e)}"
        )


@router.get("/realtime/{session_id}/summary")
async def get_session_metrics_summary(session_id: str) -> Dict[str, Any]:
    """
    Get a summary of all metrics for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Summary of session metrics including averages and totals
    """
    try:
        # Get real-time metrics
        metrics = await metrics_collector.get_real_time_metrics(session_id)
        
        # Get additional summary data
        token_summary = await metrics_collector.token_tracker.get_session_token_usage(session_id)
        avg_latency = await metrics_collector.latency_monitor.get_average_latency(session_id=session_id)
        latency_percentiles = await metrics_collector.latency_monitor.get_latency_percentiles(session_id=session_id)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "summary": {
                "token_usage": token_summary,
                "latency": {
                    "average_ms": avg_latency,
                    "percentiles": latency_percentiles
                },
                "current_metrics": metrics
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting session metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session metrics summary: {str(e)}"
        )