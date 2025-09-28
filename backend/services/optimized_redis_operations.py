"""
Optimized Redis Operations Service

Provides highly optimized Redis operations with minimal memory usage,
intelligent caching strategies, and performance monitoring.
"""

import asyncio
import json
import zlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
import structlog
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from config.performance_config import get_performance_config

logger = structlog.get_logger(__name__)


class RedisCompressionManager:
    """Manages compression and decompression of Redis values."""
    
    @staticmethod
    def should_compress(data: bytes, threshold: int = 1024) -> bool:
        """Determine if data should be compressed based on size."""
        return len(data) >= threshold
    
    @staticmethod
    def compress_data(data: str) -> bytes:
        """Compress string data using zlib."""
        return zlib.compress(data.encode('utf-8'))
    
    @staticmethod
    def decompress_data(data: bytes) -> str:
        """Decompress bytes data using zlib."""
        return zlib.decompress(data).decode('utf-8')
    
    @staticmethod
    def encode_value(value: Any, compress: bool = True) -> Tuple[bytes, bool]:
        """Encode and optionally compress a value for Redis storage."""
        json_str = json.dumps(value, separators=(',', ':'))  # Compact JSON
        json_bytes = json_str.encode('utf-8')
        
        if compress and RedisCompressionManager.should_compress(json_bytes):
            compressed = zlib.compress(json_bytes)
            return compressed, True
        
        return json_bytes, False
    
    @staticmethod
    def decode_value(data: bytes, is_compressed: bool) -> Any:
        """Decode and optionally decompress a value from Redis."""
        if is_compressed:
            decompressed = zlib.decompress(data)
            return json.loads(decompressed.decode('utf-8'))
        
        return json.loads(data.decode('utf-8'))


class RedisMemoryOptimizer:
    """Optimizes Redis memory usage through intelligent key management."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.performance_config = get_performance_config()
    
    async def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize Redis memory usage by cleaning up expired and unused keys."""
        start_time = time.perf_counter()
        
        # Get memory info before optimization
        memory_info_before = await self.redis_client.info('memory')
        used_memory_before = memory_info_before.get('used_memory', 0)
        
        optimization_results = {
            "memory_before_mb": used_memory_before / (1024 * 1024),
            "expired_keys_removed": 0,
            "large_keys_optimized": 0,
            "memory_saved_mb": 0.0,
            "optimization_time_ms": 0.0
        }
        
        try:
            # Remove expired keys
            expired_count = await self._remove_expired_keys()
            optimization_results["expired_keys_removed"] = expired_count
            
            # Optimize large keys
            large_keys_count = await self._optimize_large_keys()
            optimization_results["large_keys_optimized"] = large_keys_count
            
            # Get memory info after optimization
            memory_info_after = await self.redis_client.info('memory')
            used_memory_after = memory_info_after.get('used_memory', 0)
            
            memory_saved = (used_memory_before - used_memory_after) / (1024 * 1024)
            optimization_results["memory_saved_mb"] = max(0, memory_saved)
            
            end_time = time.perf_counter()
            optimization_results["optimization_time_ms"] = (end_time - start_time) * 1000
            
            logger.info("Redis memory optimization completed",
                       memory_saved_mb=optimization_results["memory_saved_mb"],
                       expired_keys=expired_count,
                       large_keys_optimized=large_keys_count,
                       duration_ms=optimization_results["optimization_time_ms"])
            
            return optimization_results
            
        except Exception as e:
            logger.error("Redis memory optimization failed", error=str(e))
            optimization_results["error"] = str(e)
            return optimization_results
    
    async def _remove_expired_keys(self) -> int:
        """Remove expired keys to free up memory."""
        expired_count = 0
        
        try:
            # Get all keys with TTL information
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(cursor, count=100)
                
                if keys:
                    # Check TTL for each key
                    pipeline = self.redis_client.pipeline()
                    for key in keys:
                        pipeline.ttl(key)
                    
                    ttls = await pipeline.execute()
                    
                    # Remove keys that are expired or have very short TTL
                    expired_keys = []
                    for key, ttl in zip(keys, ttls):
                        if ttl == -2:  # Key doesn't exist (expired)
                            expired_keys.append(key)
                        elif 0 < ttl < 60:  # Key expires in less than 1 minute
                            expired_keys.append(key)
                    
                    if expired_keys:
                        await self.redis_client.delete(*expired_keys)
                        expired_count += len(expired_keys)
                
                if cursor == 0:
                    break
            
            return expired_count
            
        except Exception as e:
            logger.warning("Error removing expired keys", error=str(e))
            return expired_count
    
    async def _optimize_large_keys(self) -> int:
        """Optimize large keys by recompressing or restructuring them."""
        optimized_count = 0
        max_key_size = self.performance_config.redis_config.max_key_size
        
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(cursor, count=50)
                
                if keys:
                    # Check size of each key
                    pipeline = self.redis_client.pipeline()
                    for key in keys:
                        pipeline.memory_usage(key)
                    
                    try:
                        sizes = await pipeline.execute()
                        
                        for key, size in zip(keys, sizes):
                            if size and size > max_key_size:
                                # Try to optimize large key
                                if await self._optimize_single_key(key, size):
                                    optimized_count += 1
                    
                    except Exception as e:
                        # MEMORY USAGE command might not be available in all Redis versions
                        logger.debug("Memory usage command not available", error=str(e))
                        break
                
                if cursor == 0:
                    break
            
            return optimized_count
            
        except Exception as e:
            logger.warning("Error optimizing large keys", error=str(e))
            return optimized_count
    
    async def _optimize_single_key(self, key: str, current_size: int) -> bool:
        """Optimize a single large key."""
        try:
            # Get the key value
            value = await self.redis_client.get(key)
            if not value:
                return False
            
            # Try to recompress the value
            try:
                # Assume it's JSON data
                data = json.loads(value)
                compressed_data, is_compressed = RedisCompressionManager.encode_value(data, compress=True)
                
                if len(compressed_data) < current_size * 0.8:  # At least 20% reduction
                    # Store the recompressed data with compression flag
                    await self.redis_client.set(f"{key}:compressed", compressed_data)
                    await self.redis_client.set(f"{key}:meta", json.dumps({"compressed": is_compressed}))
                    await self.redis_client.delete(key)
                    
                    logger.debug("Optimized large key",
                               key=key,
                               original_size=current_size,
                               new_size=len(compressed_data),
                               reduction_percent=(current_size - len(compressed_data)) / current_size * 100)
                    
                    return True
            
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Not JSON data, skip optimization
                pass
            
            return False
            
        except Exception as e:
            logger.warning("Error optimizing single key", key=key, error=str(e))
            return False


class OptimizedRedisOperations:
    """Highly optimized Redis operations service."""
    
    def __init__(self, redis_url: str = None):
        self.performance_config = get_performance_config()
        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[ConnectionPool] = None
        self.memory_optimizer: Optional[RedisMemoryOptimizer] = None
        
        # Performance tracking
        self.operation_count = 0
        self.total_latency = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.compression_savings = 0
    
    async def initialize(self) -> bool:
        """Initialize Redis connection with optimized settings."""
        try:
            # Create optimized connection pool
            connection_params = self.performance_config.get_redis_connection_params()
            
            self.connection_pool = ConnectionPool.from_url(
                self.redis_url,
                **connection_params["connection_pool_class_kwargs"]
            )
            
            self.redis_client = redis.Redis(
                connection_pool=self.connection_pool,
                decode_responses=False  # We handle encoding/decoding manually
            )
            
            # Test connection
            await self.redis_client.ping()
            
            # Initialize memory optimizer
            self.memory_optimizer = RedisMemoryOptimizer(self.redis_client)
            
            logger.info("Optimized Redis operations initialized successfully",
                       redis_url=self.redis_url,
                       max_connections=connection_params["max_connections"])
            
            return True
            
        except Exception as e:
            logger.error("Failed to initialize optimized Redis operations", error=str(e))
            return False
    
    async def close(self):
        """Close Redis connections."""
        if self.connection_pool:
            await self.connection_pool.disconnect()
        
        if self.redis_client:
            await self.redis_client.close()
    
    async def set_optimized(self, key: str, value: Any, ttl: Optional[int] = None, 
                           compress: bool = True) -> bool:
        """Set a value with optimal encoding and compression."""
        start_time = time.perf_counter()
        
        try:
            # Encode and optionally compress the value
            encoded_data, is_compressed = RedisCompressionManager.encode_value(value, compress)
            
            # Use pipeline for atomic operations
            pipeline = self.redis_client.pipeline()
            
            # Set the main data
            if ttl:
                pipeline.setex(key, ttl, encoded_data)
            else:
                default_ttl = self.performance_config.redis_config.default_ttl
                pipeline.setex(key, default_ttl, encoded_data)
            
            # Set metadata if compressed
            if is_compressed:
                meta_key = f"{key}:meta"
                meta_data = json.dumps({"compressed": True, "timestamp": time.time()})
                pipeline.setex(meta_key, ttl or default_ttl, meta_data.encode('utf-8'))
                
                # Track compression savings
                original_size = len(json.dumps(value).encode('utf-8'))
                self.compression_savings += original_size - len(encoded_data)
            
            await pipeline.execute()
            
            # Track performance
            latency = (time.perf_counter() - start_time) * 1000
            self.operation_count += 1
            self.total_latency += latency
            
            logger.debug("Optimized Redis SET completed",
                        key=key,
                        compressed=is_compressed,
                        size_bytes=len(encoded_data),
                        latency_ms=latency)
            
            return True
            
        except Exception as e:
            logger.error("Optimized Redis SET failed", key=key, error=str(e))
            return False
    
    async def get_optimized(self, key: str) -> Optional[Any]:
        """Get a value with optimal decoding and decompression."""
        start_time = time.perf_counter()
        
        try:
            # Use pipeline to get data and metadata
            pipeline = self.redis_client.pipeline()
            pipeline.get(key)
            pipeline.get(f"{key}:meta")
            
            results = await pipeline.execute()
            data, meta_data = results
            
            if data is None:
                self.cache_misses += 1
                return None
            
            self.cache_hits += 1
            
            # Check if data is compressed
            is_compressed = False
            if meta_data:
                try:
                    meta = json.loads(meta_data.decode('utf-8'))
                    is_compressed = meta.get("compressed", False)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            
            # Decode the value
            value = RedisCompressionManager.decode_value(data, is_compressed)
            
            # Track performance
            latency = (time.perf_counter() - start_time) * 1000
            self.operation_count += 1
            self.total_latency += latency
            
            logger.debug("Optimized Redis GET completed",
                        key=key,
                        compressed=is_compressed,
                        latency_ms=latency)
            
            return value
            
        except Exception as e:
            logger.error("Optimized Redis GET failed", key=key, error=str(e))
            self.cache_misses += 1
            return None
    
    async def batch_set_optimized(self, items: Dict[str, Any], ttl: Optional[int] = None,
                                 compress: bool = True) -> int:
        """Set multiple values in a single batch operation."""
        start_time = time.perf_counter()
        success_count = 0
        
        try:
            pipeline = self.redis_client.pipeline()
            default_ttl = ttl or self.performance_config.redis_config.default_ttl
            
            for key, value in items.items():
                # Encode and optionally compress each value
                encoded_data, is_compressed = RedisCompressionManager.encode_value(value, compress)
                
                # Add to pipeline
                pipeline.setex(key, default_ttl, encoded_data)
                
                # Add metadata if compressed
                if is_compressed:
                    meta_key = f"{key}:meta"
                    meta_data = json.dumps({"compressed": True, "timestamp": time.time()})
                    pipeline.setex(meta_key, default_ttl, meta_data.encode('utf-8'))
            
            # Execute batch
            results = await pipeline.execute()
            success_count = sum(1 for result in results if result)
            
            # Track performance
            latency = (time.perf_counter() - start_time) * 1000
            self.operation_count += len(items)
            self.total_latency += latency
            
            logger.info("Batch Redis SET completed",
                       items_count=len(items),
                       success_count=success_count,
                       latency_ms=latency)
            
            return success_count
            
        except Exception as e:
            logger.error("Batch Redis SET failed", error=str(e))
            return success_count
    
    async def batch_get_optimized(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values in a single batch operation."""
        start_time = time.perf_counter()
        results = {}
        
        try:
            # Create pipeline for all keys and their metadata
            pipeline = self.redis_client.pipeline()
            
            for key in keys:
                pipeline.get(key)
                pipeline.get(f"{key}:meta")
            
            # Execute batch
            batch_results = await pipeline.execute()
            
            # Process results in pairs (data, metadata)
            for i, key in enumerate(keys):
                data_idx = i * 2
                meta_idx = i * 2 + 1
                
                data = batch_results[data_idx] if data_idx < len(batch_results) else None
                meta_data = batch_results[meta_idx] if meta_idx < len(batch_results) else None
                
                if data is not None:
                    # Check if compressed
                    is_compressed = False
                    if meta_data:
                        try:
                            meta = json.loads(meta_data.decode('utf-8'))
                            is_compressed = meta.get("compressed", False)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass
                    
                    # Decode value
                    try:
                        value = RedisCompressionManager.decode_value(data, is_compressed)
                        results[key] = value
                        self.cache_hits += 1
                    except Exception as e:
                        logger.warning("Failed to decode value", key=key, error=str(e))
                        self.cache_misses += 1
                else:
                    self.cache_misses += 1
            
            # Track performance
            latency = (time.perf_counter() - start_time) * 1000
            self.operation_count += len(keys)
            self.total_latency += latency
            
            logger.debug("Batch Redis GET completed",
                        keys_count=len(keys),
                        found_count=len(results),
                        latency_ms=latency)
            
            return results
            
        except Exception as e:
            logger.error("Batch Redis GET failed", error=str(e))
            return results
    
    async def cleanup_expired_keys(self, pattern: str = "*") -> int:
        """Clean up expired keys matching a pattern."""
        if not self.memory_optimizer:
            return 0
        
        try:
            optimization_results = await self.memory_optimizer.optimize_memory_usage()
            return optimization_results.get("expired_keys_removed", 0)
        except Exception as e:
            logger.error("Failed to cleanup expired keys", error=str(e))
            return 0
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for Redis operations."""
        try:
            # Get Redis info
            info = await self.redis_client.info()
            memory_info = await self.redis_client.info('memory')
            
            # Calculate hit rate
            total_operations = self.cache_hits + self.cache_misses
            hit_rate = self.cache_hits / total_operations if total_operations > 0 else 0.0
            
            # Calculate average latency
            avg_latency = self.total_latency / self.operation_count if self.operation_count > 0 else 0.0
            
            return {
                "redis_info": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_mb": memory_info.get("used_memory", 0) / (1024 * 1024),
                    "used_memory_peak_mb": memory_info.get("used_memory_peak", 0) / (1024 * 1024),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0)
                },
                "operation_stats": {
                    "total_operations": self.operation_count,
                    "cache_hits": self.cache_hits,
                    "cache_misses": self.cache_misses,
                    "hit_rate": hit_rate,
                    "average_latency_ms": avg_latency,
                    "compression_savings_bytes": self.compression_savings
                }
            }
            
        except Exception as e:
            logger.error("Failed to get performance stats", error=str(e))
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check."""
        try:
            start_time = time.perf_counter()
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = {"timestamp": time.time(), "test": True}
            
            # Test SET
            await self.set_optimized(test_key, test_value, ttl=60)
            
            # Test GET
            retrieved_value = await self.get_optimized(test_key)
            
            # Test DELETE
            await self.redis_client.delete(test_key)
            
            latency = (time.perf_counter() - start_time) * 1000
            
            # Get memory info
            memory_info = await self.redis_client.info('memory')
            used_memory_mb = memory_info.get("used_memory", 0) / (1024 * 1024)
            
            # Check memory thresholds
            warning_threshold = self.performance_config.redis_config.memory_warning_threshold_mb
            critical_threshold = self.performance_config.redis_config.memory_critical_threshold_mb
            
            memory_status = "healthy"
            if used_memory_mb >= critical_threshold:
                memory_status = "critical"
            elif used_memory_mb >= warning_threshold:
                memory_status = "warning"
            
            return {
                "status": "healthy",
                "latency_ms": latency,
                "memory_usage_mb": used_memory_mb,
                "memory_status": memory_status,
                "operations_working": retrieved_value == test_value,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global instance
_optimized_redis = None


async def get_optimized_redis() -> OptimizedRedisOperations:
    """Get the global optimized Redis operations instance."""
    global _optimized_redis
    if _optimized_redis is None:
        _optimized_redis = OptimizedRedisOperations()
        await _optimized_redis.initialize()
    
    return _optimized_redis


async def close_optimized_redis():
    """Close the global optimized Redis operations instance."""
    global _optimized_redis
    if _optimized_redis:
        await _optimized_redis.close()
        _optimized_redis = None