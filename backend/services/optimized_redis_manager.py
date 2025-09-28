"""
Optimized Redis Manager

Enhanced Redis cache management system with intelligent caching strategies,
storage footprint optimization, and performance monitoring. Implements the
requirements for task 4.1 of the cosmos optimization spec.

Key Features:
- Intelligent caching strategies for faster lookups
- Storage footprint optimization methods
- Enhanced performance with connection pooling
- Comprehensive error handling and monitoring
- Integration with existing Redis infrastructure
"""

import os
import time
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from urllib.parse import urlparse

try:
    import redis
    from redis.connection import ConnectionPool
    from redis.exceptions import ConnectionError, TimeoutError, RedisError
except ImportError:
    raise ImportError("Redis package is required. Install with: pip install redis")

# Configure logging
logger = logging.getLogger(__name__)

# Import existing components
try:
    from integrations.cosmos.v1.cosmos.redis_cache import SmartRedisCache
    from integrations.cosmos.v1.cosmos.config import get_config
    from services.redis_status_integration import get_redis_status_integration
except ImportError as e:
    logger.warning(f"Some imports not available: {e}")
    SmartRedisCache = None
    get_config = None
    get_redis_status_integration = None


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    cache_hits: int = 0
    cache_misses: int = 0
    total_requests: int = 0
    average_response_time: float = 0.0
    storage_size_bytes: int = 0
    last_updated: datetime = None
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.last_updated:
            data['last_updated'] = self.last_updated.isoformat()
        return data


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if not self.ttl_seconds:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def update_access(self):
        """Update access metadata."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class OptimizedRedisManager:
    """
    Optimized Redis Manager with enhanced performance and intelligent caching.
    
    Implements intelligent caching strategies, storage optimization, and
    comprehensive performance monitoring as specified in requirements
    4.1, 4.2, 4.3, 4.4, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_connections: int = 20,
        socket_timeout: float = 30.0,
        socket_connect_timeout: float = 30.0,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30
    ):
        """
        Initialize OptimizedRedisManager.
        
        Args:
            redis_url: Redis connection URL
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            health_check_interval: Health check interval in seconds
        """
        self.redis_url = redis_url or os.getenv('REDIS_URL')
        if not self.redis_url:
            raise ValueError("Redis URL is required")
        
        # Connection configuration
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval
        
        # Initialize connection pool
        self._connection_pool = None
        self._redis_client = None
        self._initialize_connection_pool()
        
        # Cache management
        self._cache_metrics = CacheMetrics()
        self._local_cache: Dict[str, CacheEntry] = {}
        self._cache_keys: Set[str] = set()
        
        # Performance optimization settings
        self.pipeline_batch_size = 100
        self.compression_threshold = 1024  # Compress data larger than 1KB
        self.max_local_cache_size = 1000  # Maximum local cache entries
        
        # Status integration
        self.status_integration = get_redis_status_integration() if get_redis_status_integration else None
        
        # Background tasks
        self._cleanup_task = None
        self._health_check_task = None
        self._start_background_tasks()
        
        logger.info("OptimizedRedisManager initialized successfully")
    
    def _initialize_connection_pool(self):
        """Initialize Redis connection pool with optimized settings."""
        try:
            # Parse Redis URL for SSL configuration
            parsed_url = urlparse(self.redis_url)
            ssl_enabled = parsed_url.scheme == 'rediss'
            
            # Create connection pool
            self._connection_pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                health_check_interval=self.health_check_interval,
                ssl_cert_reqs=None if ssl_enabled else None,
                decode_responses=True
            )
            
            # Create Redis client
            self._redis_client = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            self._redis_client.ping()
            logger.info("Redis connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection pool: {e}")
            raise
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        try:
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("Background tasks started successfully")
            
        except Exception as e:
            logger.warning(f"Failed to start background tasks: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop for cache maintenance."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def initialize_repository_cache(
        self,
        repo_url: str,
        user_id: str,
        force_refresh: bool = False
    ) -> str:
        """
        Initialize repository cache with intelligent caching strategy.
        
        Args:
            repo_url: Repository URL
            user_id: User identifier
            force_refresh: Force refresh from source
            
        Returns:
            Cache key for the repository
        """
        start_time = time.time()
        cache_key = self._generate_cache_key(repo_url, user_id)
        
        try:
            # Start status tracking
            operation_id = None
            if self.status_integration:
                operation_id = await self.status_integration.start_cache_operation(
                    operation_type="initialize",
                    cache_key=cache_key,
                    description=f"Initializing cache for {repo_url}"
                )
            
            # Check if cache already exists and is valid
            if not force_refresh:
                existing_data = await self._get_cached_data(cache_key)
                if existing_data:
                    logger.info(f"Repository cache already exists: {cache_key}")
                    
                    if self.status_integration and operation_id:
                        await self.status_integration.complete_cache_operation(
                            operation_type="initialize",
                            cache_key=cache_key,
                            operation_id=operation_id,
                            result={"status": "cache_hit", "cache_key": cache_key}
                        )
                    
                    return cache_key
            
            # Initialize new cache entry
            cache_data = {
                "repo_url": repo_url,
                "user_id": user_id,
                "initialized_at": datetime.now().isoformat(),
                "status": "initializing",
                "metadata": {
                    "cache_key": cache_key,
                    "version": "1.0"
                }
            }
            
            # Store initial cache entry
            await self._set_cached_data(cache_key, cache_data, ttl=3600)  # 1 hour TTL
            
            # Update metrics
            self._cache_metrics.total_requests += 1
            self._cache_metrics.cache_misses += 1
            
            # Complete status tracking
            if self.status_integration and operation_id:
                await self.status_integration.complete_cache_operation(
                    operation_type="initialize",
                    cache_key=cache_key,
                    operation_id=operation_id,
                    result={"status": "initialized", "cache_key": cache_key},
                    cache_size=len(json.dumps(cache_data))
                )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Repository cache initialized: {cache_key} in {elapsed_time:.2f}s")
            
            return cache_key
            
        except Exception as e:
            logger.error(f"Failed to initialize repository cache: {e}")
            
            if self.status_integration and operation_id:
                await self.status_integration.fail_cache_operation(
                    operation_type="initialize",
                    cache_key=cache_key,
                    operation_id=operation_id,
                    error=str(e)
                )
            
            raise
    
    async def get_cached_context(
        self,
        cache_key: str,
        query: str,
        max_results: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached context with intelligent lookup strategies.
        
        Args:
            cache_key: Cache key
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            Cached context data or None
        """
        start_time = time.time()
        
        try:
            # Generate context key
            context_key = f"{cache_key}:context:{hash(query)}"
            
            # Check local cache first
            local_entry = self._local_cache.get(context_key)
            if local_entry and not local_entry.is_expired():
                local_entry.update_access()
                self._cache_metrics.cache_hits += 1
                self._cache_metrics.total_requests += 1
                
                elapsed_time = time.time() - start_time
                self._update_average_response_time(elapsed_time)
                
                logger.debug(f"Context cache hit (local): {context_key}")
                return local_entry.data
            
            # Check Redis cache
            cached_data = await self._get_cached_data(context_key)
            if cached_data:
                # Store in local cache for faster future access
                self._store_in_local_cache(context_key, cached_data)
                
                self._cache_metrics.cache_hits += 1
                self._cache_metrics.total_requests += 1
                
                elapsed_time = time.time() - start_time
                self._update_average_response_time(elapsed_time)
                
                logger.debug(f"Context cache hit (Redis): {context_key}")
                return cached_data
            
            # Cache miss
            self._cache_metrics.cache_misses += 1
            self._cache_metrics.total_requests += 1
            
            logger.debug(f"Context cache miss: {context_key}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached context: {e}")
            return None
    
    async def cleanup_repository_cache(self, cache_key: str) -> bool:
        """
        Clean up repository cache with optimized removal.
        
        Args:
            cache_key: Cache key to clean up
            
        Returns:
            True if successful
        """
        try:
            # Start status tracking
            operation_id = None
            if self.status_integration:
                operation_id = await self.status_integration.start_cache_cleanup(
                    cleanup_type="repository",
                    cache_key=cache_key
                )
            
            # Get all related keys
            pattern = f"{cache_key}*"
            keys_to_delete = []
            
            # Use SCAN for efficient key discovery
            cursor = 0
            while True:
                cursor, keys = self._redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                keys_to_delete.extend(keys)
                if cursor == 0:
                    break
            
            if keys_to_delete:
                # Use pipeline for efficient batch deletion
                pipe = self._redis_client.pipeline()
                for key in keys_to_delete:
                    pipe.delete(key)
                pipe.execute()
                
                # Clean up local cache
                local_keys_to_remove = [
                    key for key in self._local_cache.keys()
                    if key.startswith(cache_key)
                ]
                for key in local_keys_to_remove:
                    del self._local_cache[key]
                
                # Update cache keys set
                self._cache_keys.discard(cache_key)
                
                logger.info(f"Cleaned up {len(keys_to_delete)} cache entries for {cache_key}")
            
            # Complete status tracking
            if self.status_integration and operation_id:
                await self.status_integration.complete_cache_cleanup(
                    cleanup_type="repository",
                    cache_key=cache_key,
                    operation_id=operation_id,
                    keys_removed=len(keys_to_delete)
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup repository cache {cache_key}: {e}")
            
            if self.status_integration and operation_id:
                await self.status_integration.fail_cache_operation(
                    operation_type="cleanup",
                    cache_key=cache_key,
                    operation_id=operation_id,
                    error=str(e)
                )
            
            return False
    
    async def optimize_storage_footprint(self, cache_key: str) -> Dict[str, Any]:
        """
        Optimize storage footprint for a cache entry.
        
        Args:
            cache_key: Cache key to optimize
            
        Returns:
            Optimization results
        """
        try:
            # Start status tracking
            operation_id = None
            if self.status_integration:
                operation_id = await self.status_integration.start_memory_optimization(
                    cache_key=cache_key
                )
            
            optimization_results = {
                "cache_key": cache_key,
                "original_size": 0,
                "optimized_size": 0,
                "compression_ratio": 0.0,
                "keys_optimized": 0,
                "keys_removed": 0
            }
            
            # Get all related keys
            pattern = f"{cache_key}*"
            keys_to_optimize = []
            
            cursor = 0
            while True:
                cursor, keys = self._redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                keys_to_optimize.extend(keys)
                if cursor == 0:
                    break
            
            # Optimize each key
            pipe = self._redis_client.pipeline()
            for key in keys_to_optimize:
                try:
                    # Get current data
                    data = self._redis_client.get(key)
                    if data:
                        original_size = len(data)
                        optimization_results["original_size"] += original_size
                        
                        # Apply compression if data is large enough
                        if original_size > self.compression_threshold:
                            compressed_data = self._compress_data(data)
                            if len(compressed_data) < original_size:
                                pipe.set(key, compressed_data)
                                optimization_results["optimized_size"] += len(compressed_data)
                                optimization_results["keys_optimized"] += 1
                            else:
                                optimization_results["optimized_size"] += original_size
                        else:
                            optimization_results["optimized_size"] += original_size
                
                except Exception as e:
                    logger.warning(f"Failed to optimize key {key}: {e}")
            
            # Execute optimizations
            if optimization_results["keys_optimized"] > 0:
                pipe.execute()
            
            # Calculate compression ratio
            if optimization_results["original_size"] > 0:
                optimization_results["compression_ratio"] = (
                    1.0 - optimization_results["optimized_size"] / optimization_results["original_size"]
                )
            
            # Complete status tracking
            if self.status_integration and operation_id:
                await self.status_integration.complete_memory_optimization(
                    cache_key=cache_key,
                    operation_id=operation_id,
                    bytes_saved=optimization_results["original_size"] - optimization_results["optimized_size"]
                )
            
            logger.info(f"Storage optimization completed for {cache_key}: {optimization_results}")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Failed to optimize storage footprint for {cache_key}: {e}")
            
            if self.status_integration and operation_id:
                await self.status_integration.fail_cache_operation(
                    operation_type="optimization",
                    cache_key=cache_key,
                    operation_id=operation_id,
                    error=str(e)
                )
            
            return {"error": str(e)}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        try:
            # Update storage size
            self._update_storage_metrics()
            
            # Get Redis info
            redis_info = self._redis_client.info()
            
            return {
                "cache_metrics": self._cache_metrics.to_dict(),
                "redis_info": {
                    "used_memory": redis_info.get("used_memory", 0),
                    "used_memory_human": redis_info.get("used_memory_human", "0B"),
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "total_commands_processed": redis_info.get("total_commands_processed", 0),
                    "keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "keyspace_misses": redis_info.get("keyspace_misses", 0)
                },
                "local_cache": {
                    "size": len(self._local_cache),
                    "max_size": self.max_local_cache_size
                },
                "connection_pool": {
                    "max_connections": self.max_connections,
                    "created_connections": self._connection_pool.created_connections
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}
    
    async def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from Redis cache with error handling."""
        try:
            data = self._redis_client.get(key)
            if data:
                # Try to decompress if needed
                try:
                    return self._decompress_data(data)
                except:
                    # If decompression fails, return as-is
                    return json.loads(data) if isinstance(data, str) else data
            return None
        except Exception as e:
            logger.error(f"Failed to get cached data for key {key}: {e}")
            return None
    
    async def _set_cached_data(self, key: str, data: Any, ttl: Optional[int] = None):
        """Set data in Redis cache with compression and error handling."""
        try:
            # Serialize data
            serialized_data = json.dumps(data)
            
            # Compress if data is large enough
            if len(serialized_data) > self.compression_threshold:
                serialized_data = self._compress_data(serialized_data)
            
            # Set in Redis
            if ttl:
                self._redis_client.setex(key, ttl, serialized_data)
            else:
                self._redis_client.set(key, serialized_data)
            
            # Track cache key
            self._cache_keys.add(key)
            
        except Exception as e:
            logger.error(f"Failed to set cached data for key {key}: {e}")
            raise
    
    def _generate_cache_key(self, repo_url: str, user_id: str) -> str:
        """Generate cache key for repository."""
        # Extract repo name from URL
        parsed_url = urlparse(repo_url)
        repo_path = parsed_url.path.strip('/').replace('.git', '')
        
        # Create cache key
        cache_key = f"repo:{repo_path}:user:{user_id}"
        return cache_key
    
    def _store_in_local_cache(self, key: str, data: Any):
        """Store data in local cache with size management."""
        try:
            # Remove oldest entries if cache is full
            if len(self._local_cache) >= self.max_local_cache_size:
                # Remove least recently used entries
                sorted_entries = sorted(
                    self._local_cache.items(),
                    key=lambda x: x[1].last_accessed
                )
                for old_key, _ in sorted_entries[:10]:  # Remove 10 oldest
                    del self._local_cache[old_key]
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                data=data,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size_bytes=len(json.dumps(data)) if data else 0
            )
            
            self._local_cache[key] = entry
            
        except Exception as e:
            logger.error(f"Failed to store in local cache: {e}")
    
    def _compress_data(self, data: str) -> str:
        """Compress data using gzip."""
        try:
            import gzip
            import base64
            
            compressed = gzip.compress(data.encode('utf-8'))
            return base64.b64encode(compressed).decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to compress data: {e}")
            return data
    
    def _decompress_data(self, data: str) -> Any:
        """Decompress data using gzip."""
        try:
            import gzip
            import base64
            
            # Try to decompress
            compressed_bytes = base64.b64decode(data.encode('utf-8'))
            decompressed = gzip.decompress(compressed_bytes).decode('utf-8')
            return json.loads(decompressed)
        except:
            # If decompression fails, try to parse as regular JSON
            return json.loads(data)
    
    def _update_average_response_time(self, response_time: float):
        """Update average response time with exponential moving average."""
        alpha = 0.1  # Smoothing factor
        if self._cache_metrics.average_response_time == 0:
            self._cache_metrics.average_response_time = response_time
        else:
            self._cache_metrics.average_response_time = (
                alpha * response_time + 
                (1 - alpha) * self._cache_metrics.average_response_time
            )
    
    def _update_storage_metrics(self):
        """Update storage size metrics."""
        try:
            # Calculate local cache size
            local_size = sum(
                entry.size_bytes for entry in self._local_cache.values()
            )
            
            # Get Redis memory usage (approximate)
            redis_info = self._redis_client.info()
            redis_memory = redis_info.get("used_memory", 0)
            
            self._cache_metrics.storage_size_bytes = local_size + redis_memory
            self._cache_metrics.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to update storage metrics: {e}")
    
    async def _perform_cleanup(self):
        """Perform periodic cache cleanup."""
        try:
            logger.debug("Performing cache cleanup")
            
            # Clean up expired local cache entries
            expired_keys = [
                key for key, entry in self._local_cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._local_cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired local cache entries")
            
            # Update metrics
            self._update_storage_metrics()
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    async def _perform_health_check(self):
        """Perform health check on Redis connection."""
        try:
            # Test Redis connection
            self._redis_client.ping()
            logger.debug("Redis health check passed")
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            # Try to reconnect
            try:
                self._initialize_connection_pool()
                logger.info("Redis connection pool reinitialized")
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to Redis: {reconnect_error}")
    
    async def close(self):
        """Close connections and cleanup resources."""
        try:
            # Cancel background tasks
            if self._cleanup_task:
                self._cleanup_task.cancel()
            if self._health_check_task:
                self._health_check_task.cancel()
            
            # Close connection pool
            if self._connection_pool:
                self._connection_pool.disconnect()
            
            logger.info("OptimizedRedisManager closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing OptimizedRedisManager: {e}")


# Global instance management
_redis_manager_instance: Optional[OptimizedRedisManager] = None


def get_optimized_redis_manager() -> OptimizedRedisManager:
    """
    Get the global OptimizedRedisManager instance.
    
    Returns:
        OptimizedRedisManager instance
    """
    global _redis_manager_instance
    
    if _redis_manager_instance is None:
        _redis_manager_instance = OptimizedRedisManager()
    
    return _redis_manager_instance


async def cleanup_redis_manager():
    """Cleanup the global Redis manager instance."""
    global _redis_manager_instance
    
    if _redis_manager_instance:
        await _redis_manager_instance.close()
        _redis_manager_instance = None