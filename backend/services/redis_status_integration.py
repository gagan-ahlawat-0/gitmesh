"""
Redis Cache Status Integration

Integrates Redis cache operations with the status broadcasting system to provide
real-time visibility into cache operations, memory usage, and performance metrics.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

import structlog

from .status_broadcaster import get_status_broadcaster, OperationType
from .operation_tracker import get_operation_tracker

logger = structlog.get_logger(__name__)


class RedisCacheStatusIntegration:
    """
    Integrates Redis cache operations with status broadcasting.
    
    Provides real-time status updates for cache operations including
    data storage, retrieval, cleanup, and memory optimization.
    """
    
    def __init__(self):
        self.status_broadcaster = get_status_broadcaster()
        self.operation_tracker = get_operation_tracker()
        
        # Track active cache operations
        self.active_operations: Dict[str, str] = {}  # operation_key -> operation_id
    
    async def start_cache_operation(
        self,
        operation_type: str,
        cache_key: str,
        description: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        estimated_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking a Redis cache operation.
        
        Args:
            operation_type: Type of cache operation (store, retrieve, cleanup, etc.)
            cache_key: Redis cache key being operated on
            description: Human-readable description
            session_id: Optional session ID
            user_id: Optional user ID
            estimated_size: Optional estimated data size in bytes
            metadata: Optional additional metadata
            
        Returns:
            str: Operation ID for tracking
        """
        try:
            # Create operation key for tracking
            operation_key = f"{operation_type}:{cache_key}"
            
            # Prepare metadata
            operation_metadata = {
                "cache_operation_type": operation_type,
                "cache_key": cache_key,
                "estimated_size": estimated_size,
                "started_at": datetime.now().isoformat()
            }
            if metadata:
                operation_metadata.update(metadata)
            
            # Start operation tracking
            operation_id = await self.operation_tracker.start_operation(
                operation_type=OperationType.REDIS_CACHE,
                description=description,
                session_id=session_id,
                user_id=user_id,
                metadata=operation_metadata,
                total_steps=100  # Use percentage-based progress
            )
            
            # Store operation mapping
            self.active_operations[operation_key] = operation_id
            
            logger.info(
                "Redis cache operation started",
                operation_id=operation_id,
                operation_type=operation_type,
                cache_key=cache_key,
                estimated_size=estimated_size
            )
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Error starting Redis cache operation: {e}")
            raise
    
    async def update_cache_progress(
        self,
        operation_type: str,
        cache_key: str,
        progress: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update progress for a cache operation.
        
        Args:
            operation_type: Type of cache operation
            cache_key: Redis cache key
            progress: Progress as percentage (0-100)
            message: Progress message
            details: Optional additional details
            
        Returns:
            bool: True if update was successful
        """
        try:
            operation_key = f"{operation_type}:{cache_key}"
            
            if operation_key not in self.active_operations:
                logger.warning(f"No active cache operation for key: {operation_key}")
                return False
            
            operation_id = self.active_operations[operation_key]
            
            # Update progress
            success = await self.operation_tracker.update_progress(
                operation_id=operation_id,
                current=progress,
                message=message,
                details=details or {}
            )
            
            logger.debug(
                "Redis cache progress updated",
                operation_id=operation_id,
                operation_type=operation_type,
                cache_key=cache_key,
                progress=progress
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating cache progress: {e}")
            return False
    
    async def complete_cache_operation(
        self,
        operation_type: str,
        cache_key: str,
        result: Optional[Dict[str, Any]] = None,
        cache_size: Optional[int] = None,
        operation_time: Optional[float] = None
    ) -> bool:
        """
        Mark a cache operation as completed.
        
        Args:
            operation_type: Type of cache operation
            cache_key: Redis cache key
            result: Optional result data
            cache_size: Optional final cache size in bytes
            operation_time: Optional operation time in seconds
            
        Returns:
            bool: True if completion was successful
        """
        try:
            operation_key = f"{operation_type}:{cache_key}"
            
            if operation_key not in self.active_operations:
                logger.warning(f"No active cache operation for key: {operation_key}")
                return False
            
            operation_id = self.active_operations[operation_key]
            
            # Prepare result data
            operation_result = result or {}
            if cache_size is not None:
                operation_result["cache_size"] = cache_size
                operation_result["cache_size_mb"] = round(cache_size / (1024 * 1024), 2)
            if operation_time is not None:
                operation_result["operation_time"] = operation_time
            
            # Create summary message
            summary = f"Cache {operation_type} completed for {cache_key}"
            if cache_size is not None:
                size_mb = round(cache_size / (1024 * 1024), 2)
                summary += f" ({size_mb} MB)"
            
            # Complete operation
            success = await self.operation_tracker.complete_operation(
                operation_id=operation_id,
                result=operation_result,
                summary=summary
            )
            
            # Remove from active operations
            del self.active_operations[operation_key]
            
            logger.info(
                "Redis cache operation completed",
                operation_id=operation_id,
                operation_type=operation_type,
                cache_key=cache_key,
                cache_size=cache_size,
                operation_time=operation_time
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error completing cache operation: {e}")
            return False
    
    async def fail_cache_operation(
        self,
        operation_type: str,
        cache_key: str,
        error: str,
        error_details: Optional[Dict[str, Any]] = None,
        is_recoverable: bool = True
    ) -> bool:
        """
        Mark a cache operation as failed.
        
        Args:
            operation_type: Type of cache operation
            cache_key: Redis cache key
            error: Error message
            error_details: Optional error details
            is_recoverable: Whether the error is recoverable
            
        Returns:
            bool: True if failure was recorded successfully
        """
        try:
            operation_key = f"{operation_type}:{cache_key}"
            
            if operation_key not in self.active_operations:
                logger.warning(f"No active cache operation for key: {operation_key}")
                return False
            
            operation_id = self.active_operations[operation_key]
            
            # Fail operation
            success = await self.operation_tracker.fail_operation(
                operation_id=operation_id,
                error=error,
                error_details=error_details,
                is_recoverable=is_recoverable
            )
            
            # Remove from active operations
            del self.active_operations[operation_key]
            
            logger.error(
                "Redis cache operation failed",
                operation_id=operation_id,
                operation_type=operation_type,
                cache_key=cache_key,
                error=error,
                is_recoverable=is_recoverable
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error failing cache operation: {e}")
            return False
    
    async def track_cache_cleanup(
        self,
        cleanup_type: str = "expired_keys",
        session_id: Optional[str] = None,
        estimated_keys: Optional[int] = None
    ) -> str:
        """
        Start tracking a cache cleanup operation.
        
        Args:
            cleanup_type: Type of cleanup (expired_keys, memory_optimization, etc.)
            session_id: Optional session ID
            estimated_keys: Optional estimated number of keys to process
            
        Returns:
            str: Operation ID for tracking
        """
        description = f"Redis cache cleanup ({cleanup_type})"
        
        return await self.start_cache_operation(
            operation_type="cleanup",
            cache_key=cleanup_type,
            description=description,
            session_id=session_id,
            estimated_size=estimated_keys,
            metadata={"cleanup_type": cleanup_type}
        )
    
    async def update_cleanup_progress(
        self,
        cleanup_type: str,
        keys_processed: int,
        total_keys: int,
        memory_freed: Optional[int] = None
    ) -> bool:
        """
        Update progress for a cache cleanup operation.
        
        Args:
            cleanup_type: Type of cleanup
            keys_processed: Number of keys processed
            total_keys: Total number of keys to process
            memory_freed: Optional memory freed in bytes
            
        Returns:
            bool: True if update was successful
        """
        progress = (keys_processed / total_keys * 100) if total_keys > 0 else 0
        message = f"Cleaned up {keys_processed}/{total_keys} keys"
        
        details = {
            "keys_processed": keys_processed,
            "total_keys": total_keys
        }
        if memory_freed is not None:
            details["memory_freed"] = memory_freed
            details["memory_freed_mb"] = round(memory_freed / (1024 * 1024), 2)
            message += f" (freed {round(memory_freed / (1024 * 1024), 2)} MB)"
        
        return await self.update_cache_progress(
            operation_type="cleanup",
            cache_key=cleanup_type,
            progress=progress,
            message=message,
            details=details
        )
    
    async def track_memory_optimization(
        self,
        session_id: Optional[str] = None,
        target_memory_mb: Optional[float] = None
    ) -> str:
        """
        Start tracking a memory optimization operation.
        
        Args:
            session_id: Optional session ID
            target_memory_mb: Optional target memory usage in MB
            
        Returns:
            str: Operation ID for tracking
        """
        description = "Redis memory optimization"
        if target_memory_mb:
            description += f" (target: {target_memory_mb} MB)"
        
        return await self.start_cache_operation(
            operation_type="memory_optimization",
            cache_key="system",
            description=description,
            session_id=session_id,
            metadata={"target_memory_mb": target_memory_mb}
        )
    
    async def update_memory_optimization_progress(
        self,
        current_memory_mb: float,
        target_memory_mb: float,
        optimizations_applied: int = 0
    ) -> bool:
        """
        Update progress for memory optimization.
        
        Args:
            current_memory_mb: Current memory usage in MB
            target_memory_mb: Target memory usage in MB
            optimizations_applied: Number of optimizations applied
            
        Returns:
            bool: True if update was successful
        """
        # Calculate progress based on memory reduction
        if current_memory_mb <= target_memory_mb:
            progress = 100.0
            message = f"Memory optimized to {current_memory_mb:.2f} MB (target: {target_memory_mb:.2f} MB)"
        else:
            # Progress based on how much we've reduced memory
            initial_memory = current_memory_mb + (current_memory_mb - target_memory_mb)  # Estimate
            progress = max(0, min(100, ((initial_memory - current_memory_mb) / (initial_memory - target_memory_mb)) * 100))
            message = f"Optimizing memory: {current_memory_mb:.2f} MB (target: {target_memory_mb:.2f} MB)"
        
        details = {
            "current_memory_mb": current_memory_mb,
            "target_memory_mb": target_memory_mb,
            "optimizations_applied": optimizations_applied
        }
        
        return await self.update_cache_progress(
            operation_type="memory_optimization",
            cache_key="system",
            progress=progress,
            message=message,
            details=details
        )
    
    def get_cache_operation_status(
        self,
        operation_type: str,
        cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current status of a cache operation.
        
        Args:
            operation_type: Type of cache operation
            cache_key: Redis cache key
            
        Returns:
            Optional[Dict]: Operation status or None if not found
        """
        operation_key = f"{operation_type}:{cache_key}"
        if operation_key not in self.active_operations:
            return None
        
        operation_id = self.active_operations[operation_key]
        return self.operation_tracker.get_operation_status(operation_id)
    
    def is_cache_operation_active(
        self,
        operation_type: str,
        cache_key: str
    ) -> bool:
        """
        Check if a cache operation is currently active.
        
        Args:
            operation_type: Type of cache operation
            cache_key: Redis cache key
            
        Returns:
            bool: True if operation is active
        """
        operation_key = f"{operation_type}:{cache_key}"
        return operation_key in self.active_operations
    
    def get_active_cache_operations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active cache operations.
        
        Returns:
            Dict: Mapping of operation_key to operation status
        """
        active_ops = {}
        for operation_key, operation_id in self.active_operations.items():
            status = self.operation_tracker.get_operation_status(operation_id)
            if status:
                active_ops[operation_key] = status
        return active_ops
    
    async def update_cache_metrics(
        self,
        operation_type: str,
        cache_key: str,
        cache_hits: Optional[int] = None,
        cache_misses: Optional[int] = None,
        bytes_processed: Optional[int] = None,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update metrics for a cache operation.
        
        Args:
            operation_type: Type of cache operation
            cache_key: Redis cache key
            cache_hits: Optional cache hits count
            cache_misses: Optional cache misses count
            bytes_processed: Optional bytes processed
            custom_metrics: Optional custom metrics
            
        Returns:
            bool: True if update was successful
        """
        try:
            operation_key = f"{operation_type}:{cache_key}"
            
            if operation_key not in self.active_operations:
                return False
            
            operation_id = self.active_operations[operation_key]
            
            await self.operation_tracker.update_metrics(
                operation_id=operation_id,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                bytes_processed=bytes_processed,
                custom_metrics=custom_metrics
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating cache metrics: {e}")
            return False


# Global instance
_redis_integration: Optional[RedisCacheStatusIntegration] = None


def get_redis_status_integration() -> RedisCacheStatusIntegration:
    """Get the global Redis cache status integration instance."""
    global _redis_integration
    if _redis_integration is None:
        _redis_integration = RedisCacheStatusIntegration()
    return _redis_integration