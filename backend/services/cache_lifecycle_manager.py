"""
Cache Lifecycle Manager

Automatic cache cleanup and lifecycle management system for Redis cache.
Implements navigation-based cache removal, cache expiration, and memory management
as specified in requirements 5.1, 5.2, 5.3, 5.4, 5.5.

Key Features:
- Automatic cache cleanup on navigation transitions
- Cache expiration and memory management
- Navigation-based cache removal for /hub transitions
- Comprehensive lifecycle tracking and monitoring
"""

import os
import time
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)

# Import dependencies
try:
    from services.optimized_redis_manager import OptimizedRedisManager, get_optimized_redis_manager
    from services.redis_status_integration import get_redis_status_integration
except ImportError as e:
    logger.warning(f"Some imports not available: {e}")
    OptimizedRedisManager = None
    get_optimized_redis_manager = None
    get_redis_status_integration = None


class NavigationEvent(Enum):
    """Navigation event types."""
    ENTER_CONTRIBUTION = "enter_contribution"
    LEAVE_CONTRIBUTION = "leave_contribution"
    ENTER_HUB = "enter_hub"
    LEAVE_HUB = "leave_hub"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class CacheLifecycleState(Enum):
    """Cache lifecycle states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    CLEANING_UP = "cleaning_up"
    CLEANED = "cleaned"


@dataclass
class CacheLifecycleEntry:
    """Cache lifecycle entry with metadata."""
    cache_key: str
    user_id: str
    repo_url: str
    state: CacheLifecycleState
    created_at: datetime
    last_accessed: datetime
    expires_at: Optional[datetime] = None
    cleanup_scheduled_at: Optional[datetime] = None
    access_count: int = 0
    size_bytes: int = 0
    navigation_context: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def should_cleanup(self) -> bool:
        """Check if entry should be cleaned up."""
        return (
            self.state in [CacheLifecycleState.EXPIRED, CacheLifecycleState.EXPIRING] or
            self.is_expired()
        )
    
    def update_access(self):
        """Update access metadata."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, CacheLifecycleState):
                data[key] = value.value
        return data


@dataclass
class NavigationSession:
    """Navigation session tracking."""
    session_id: str
    user_id: str
    current_path: str
    previous_path: Optional[str] = None
    started_at: datetime = None
    last_activity: datetime = None
    active_caches: Set[str] = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
        if self.active_caches is None:
            self.active_caches = set()
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def is_stale(self, max_idle_minutes: int = 30) -> bool:
        """Check if session is stale."""
        idle_time = datetime.now() - self.last_activity
        return idle_time > timedelta(minutes=max_idle_minutes)


class CacheLifecycleManager:
    """
    Cache Lifecycle Manager for automatic cache cleanup and management.
    
    Implements automatic cache cleanup on navigation transitions, cache expiration,
    and memory management as specified in the cosmos optimization requirements.
    """
    
    def __init__(
        self,
        redis_manager: Optional[OptimizedRedisManager] = None,
        default_cache_ttl: int = 3600,  # 1 hour
        cleanup_interval: int = 300,    # 5 minutes
        max_idle_time: int = 1800,      # 30 minutes
        max_cache_size_mb: int = 100    # 100 MB per cache
    ):
        """
        Initialize CacheLifecycleManager.
        
        Args:
            redis_manager: OptimizedRedisManager instance
            default_cache_ttl: Default cache TTL in seconds
            cleanup_interval: Cleanup interval in seconds
            max_idle_time: Maximum idle time before cleanup in seconds
            max_cache_size_mb: Maximum cache size in MB
        """
        self.redis_manager = redis_manager or get_optimized_redis_manager()
        self.default_cache_ttl = default_cache_ttl
        self.cleanup_interval = cleanup_interval
        self.max_idle_time = max_idle_time
        self.max_cache_size_mb = max_cache_size_mb
        
        # Lifecycle tracking
        self._lifecycle_entries: Dict[str, CacheLifecycleEntry] = {}
        self._navigation_sessions: Dict[str, NavigationSession] = {}
        self._cleanup_queue: List[str] = []
        
        # Status integration
        self.status_integration = get_redis_status_integration() if get_redis_status_integration else None
        
        # Background tasks
        self._cleanup_task = None
        self._monitoring_task = None
        self._start_background_tasks()
        
        logger.info("CacheLifecycleManager initialized successfully")
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        try:
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info("Cache lifecycle background tasks started")
            
        except Exception as e:
            logger.warning(f"Failed to start background tasks: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._perform_scheduled_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                await self._monitor_cache_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def register_cache(
        self,
        cache_key: str,
        user_id: str,
        repo_url: str,
        navigation_context: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> CacheLifecycleEntry:
        """
        Register a cache entry for lifecycle management.
        
        Args:
            cache_key: Cache key
            user_id: User identifier
            repo_url: Repository URL
            navigation_context: Navigation context (e.g., "/contribution/repo")
            ttl_seconds: Time to live in seconds
            
        Returns:
            CacheLifecycleEntry instance
        """
        try:
            now = datetime.now()
            ttl = ttl_seconds or self.default_cache_ttl
            
            entry = CacheLifecycleEntry(
                cache_key=cache_key,
                user_id=user_id,
                repo_url=repo_url,
                state=CacheLifecycleState.INITIALIZING,
                created_at=now,
                last_accessed=now,
                expires_at=now + timedelta(seconds=ttl),
                navigation_context=navigation_context
            )
            
            self._lifecycle_entries[cache_key] = entry
            
            logger.info(f"Registered cache for lifecycle management: {cache_key}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to register cache {cache_key}: {e}")
            raise
    
    async def handle_navigation_event(
        self,
        session_id: str,
        user_id: str,
        event: NavigationEvent,
        current_path: str,
        previous_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle navigation events and trigger appropriate cache lifecycle actions.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            event: Navigation event type
            current_path: Current navigation path
            previous_path: Previous navigation path
            
        Returns:
            Dictionary with cleanup results
        """
        try:
            logger.info(f"Handling navigation event: {event.value} for user {user_id}")
            
            # Update or create navigation session
            session = self._navigation_sessions.get(session_id)
            if not session:
                session = NavigationSession(
                    session_id=session_id,
                    user_id=user_id,
                    current_path=current_path,
                    previous_path=previous_path
                )
                self._navigation_sessions[session_id] = session
            else:
                session.previous_path = session.current_path
                session.current_path = current_path
                session.update_activity()
            
            cleanup_results = {
                "event": event.value,
                "session_id": session_id,
                "user_id": user_id,
                "current_path": current_path,
                "previous_path": previous_path,
                "caches_cleaned": [],
                "caches_preserved": []
            }
            
            # Handle specific navigation events
            if event == NavigationEvent.ENTER_HUB:
                # Clean up contribution caches when entering hub
                cleanup_results.update(await self._cleanup_contribution_caches(user_id, session_id))
                
            elif event == NavigationEvent.LEAVE_CONTRIBUTION:
                # Schedule cleanup for contribution cache
                if previous_path and "/contribution/" in previous_path:
                    repo_identifier = self._extract_repo_from_path(previous_path)
                    if repo_identifier:
                        await self._schedule_cache_cleanup(user_id, repo_identifier)
                        cleanup_results["scheduled_cleanup"] = repo_identifier
                
            elif event == NavigationEvent.SESSION_END:
                # Clean up all caches for the session
                cleanup_results.update(await self._cleanup_session_caches(session_id, user_id))
            
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Failed to handle navigation event {event.value}: {e}")
            return {"error": str(e)}
    
    async def _cleanup_contribution_caches(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Clean up contribution-related caches when user navigates to hub.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Cleanup results
        """
        try:
            caches_cleaned = []
            caches_preserved = []
            
            # Find contribution caches for this user
            contribution_caches = [
                entry for entry in self._lifecycle_entries.values()
                if (entry.user_id == user_id and 
                    entry.navigation_context and 
                    "/contribution/" in entry.navigation_context)
            ]
            
            for entry in contribution_caches:
                try:
                    # Check if cache should be preserved (recently accessed)
                    time_since_access = datetime.now() - entry.last_accessed
                    if time_since_access < timedelta(minutes=5):
                        # Recently accessed, preserve for a bit longer
                        entry.state = CacheLifecycleState.EXPIRING
                        entry.expires_at = datetime.now() + timedelta(minutes=10)
                        caches_preserved.append(entry.cache_key)
                        logger.info(f"Preserving recently accessed cache: {entry.cache_key}")
                    else:
                        # Clean up immediately
                        await self._cleanup_cache_entry(entry)
                        caches_cleaned.append(entry.cache_key)
                        
                except Exception as e:
                    logger.error(f"Failed to cleanup cache {entry.cache_key}: {e}")
            
            # Update session
            session = self._navigation_sessions.get(session_id)
            if session:
                session.active_caches.clear()
            
            logger.info(f"Contribution cache cleanup: {len(caches_cleaned)} cleaned, {len(caches_preserved)} preserved")
            
            return {
                "caches_cleaned": caches_cleaned,
                "caches_preserved": caches_preserved
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup contribution caches: {e}")
            return {"error": str(e)}
    
    async def _cleanup_session_caches(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Clean up all caches for a session.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Cleanup results
        """
        try:
            caches_cleaned = []
            
            # Find all caches for this user
            user_caches = [
                entry for entry in self._lifecycle_entries.values()
                if entry.user_id == user_id
            ]
            
            for entry in user_caches:
                try:
                    await self._cleanup_cache_entry(entry)
                    caches_cleaned.append(entry.cache_key)
                except Exception as e:
                    logger.error(f"Failed to cleanup cache {entry.cache_key}: {e}")
            
            # Remove session
            if session_id in self._navigation_sessions:
                del self._navigation_sessions[session_id]
            
            logger.info(f"Session cache cleanup: {len(caches_cleaned)} caches cleaned")
            
            return {"caches_cleaned": caches_cleaned}
            
        except Exception as e:
            logger.error(f"Failed to cleanup session caches: {e}")
            return {"error": str(e)}
    
    async def _schedule_cache_cleanup(self, user_id: str, repo_identifier: str):
        """
        Schedule cache cleanup for a repository.
        
        Args:
            user_id: User identifier
            repo_identifier: Repository identifier
        """
        try:
            # Find cache entries for this repository
            repo_caches = [
                entry for entry in self._lifecycle_entries.values()
                if (entry.user_id == user_id and 
                    repo_identifier in entry.repo_url)
            ]
            
            for entry in repo_caches:
                entry.state = CacheLifecycleState.EXPIRING
                entry.cleanup_scheduled_at = datetime.now() + timedelta(seconds=30)  # 30 second delay
                self._cleanup_queue.append(entry.cache_key)
            
            logger.info(f"Scheduled cleanup for {len(repo_caches)} caches for repo: {repo_identifier}")
            
        except Exception as e:
            logger.error(f"Failed to schedule cache cleanup: {e}")
    
    async def _cleanup_cache_entry(self, entry: CacheLifecycleEntry):
        """
        Clean up a specific cache entry.
        
        Args:
            entry: CacheLifecycleEntry to clean up
        """
        try:
            entry.state = CacheLifecycleState.CLEANING_UP
            
            # Start status tracking
            operation_id = None
            if self.status_integration:
                operation_id = await self.status_integration.start_cache_cleanup(
                    cleanup_type="lifecycle",
                    cache_key=entry.cache_key
                )
            
            # Clean up from Redis
            success = await self.redis_manager.cleanup_repository_cache(entry.cache_key)
            
            if success:
                entry.state = CacheLifecycleState.CLEANED
                
                # Remove from lifecycle tracking
                if entry.cache_key in self._lifecycle_entries:
                    del self._lifecycle_entries[entry.cache_key]
                
                # Complete status tracking
                if self.status_integration and operation_id:
                    await self.status_integration.complete_cache_cleanup(
                        cleanup_type="lifecycle",
                        cache_key=entry.cache_key,
                        operation_id=operation_id,
                        keys_removed=1
                    )
                
                logger.info(f"Successfully cleaned up cache: {entry.cache_key}")
            else:
                logger.error(f"Failed to clean up cache: {entry.cache_key}")
                
                if self.status_integration and operation_id:
                    await self.status_integration.fail_cache_operation(
                        operation_type="cleanup",
                        cache_key=entry.cache_key,
                        operation_id=operation_id,
                        error="Cleanup failed"
                    )
            
        except Exception as e:
            logger.error(f"Error cleaning up cache entry {entry.cache_key}: {e}")
            entry.state = CacheLifecycleState.EXPIRED
    
    async def _perform_scheduled_cleanup(self):
        """Perform scheduled cleanup operations."""
        try:
            current_time = datetime.now()
            cleanup_count = 0
            
            # Process cleanup queue
            while self._cleanup_queue:
                cache_key = self._cleanup_queue.pop(0)
                entry = self._lifecycle_entries.get(cache_key)
                
                if entry and entry.should_cleanup():
                    await self._cleanup_cache_entry(entry)
                    cleanup_count += 1
            
            # Check for expired entries
            expired_entries = [
                entry for entry in self._lifecycle_entries.values()
                if entry.is_expired() or entry.should_cleanup()
            ]
            
            for entry in expired_entries:
                await self._cleanup_cache_entry(entry)
                cleanup_count += 1
            
            # Clean up stale sessions
            stale_sessions = [
                session_id for session_id, session in self._navigation_sessions.items()
                if session.is_stale()
            ]
            
            for session_id in stale_sessions:
                session = self._navigation_sessions[session_id]
                await self._cleanup_session_caches(session_id, session.user_id)
            
            if cleanup_count > 0:
                logger.info(f"Scheduled cleanup completed: {cleanup_count} caches cleaned")
            
        except Exception as e:
            logger.error(f"Error in scheduled cleanup: {e}")
    
    async def _monitor_cache_health(self):
        """Monitor cache health and perform maintenance."""
        try:
            # Check memory usage
            metrics = self.redis_manager.get_performance_metrics()
            redis_info = metrics.get("redis_info", {})
            used_memory = redis_info.get("used_memory", 0)
            
            # Convert to MB
            used_memory_mb = used_memory / (1024 * 1024)
            
            # If memory usage is high, trigger aggressive cleanup
            if used_memory_mb > 500:  # 500 MB threshold
                logger.warning(f"High Redis memory usage: {used_memory_mb:.1f} MB")
                await self._aggressive_cleanup()
            
            # Update entry sizes
            for entry in self._lifecycle_entries.values():
                if entry.state == CacheLifecycleState.ACTIVE:
                    entry.update_access()
            
        except Exception as e:
            logger.error(f"Error in cache health monitoring: {e}")
    
    async def _aggressive_cleanup(self):
        """Perform aggressive cleanup when memory is high."""
        try:
            logger.info("Performing aggressive cache cleanup due to high memory usage")
            
            # Sort entries by last access time (oldest first)
            sorted_entries = sorted(
                self._lifecycle_entries.values(),
                key=lambda x: x.last_accessed
            )
            
            # Clean up oldest 50% of entries
            cleanup_count = len(sorted_entries) // 2
            for entry in sorted_entries[:cleanup_count]:
                await self._cleanup_cache_entry(entry)
            
            logger.info(f"Aggressive cleanup completed: {cleanup_count} caches cleaned")
            
        except Exception as e:
            logger.error(f"Error in aggressive cleanup: {e}")
    
    def _extract_repo_from_path(self, path: str) -> Optional[str]:
        """
        Extract repository identifier from navigation path.
        
        Args:
            path: Navigation path
            
        Returns:
            Repository identifier or None
        """
        try:
            # Extract from paths like "/contribution/owner/repo"
            if "/contribution/" in path:
                parts = path.split("/contribution/")
                if len(parts) > 1:
                    repo_part = parts[1].split("/")[0] if "/" in parts[1] else parts[1]
                    return repo_part
            return None
        except Exception as e:
            logger.error(f"Failed to extract repo from path {path}: {e}")
            return None
    
    def get_lifecycle_status(self) -> Dict[str, Any]:
        """
        Get current lifecycle status and statistics.
        
        Returns:
            Lifecycle status dictionary
        """
        try:
            now = datetime.now()
            
            # Count entries by state
            state_counts = {}
            for state in CacheLifecycleState:
                state_counts[state.value] = 0
            
            for entry in self._lifecycle_entries.values():
                state_counts[entry.state.value] += 1
            
            # Calculate statistics
            total_entries = len(self._lifecycle_entries)
            active_sessions = len(self._navigation_sessions)
            cleanup_queue_size = len(self._cleanup_queue)
            
            # Find oldest and newest entries
            oldest_entry = None
            newest_entry = None
            if self._lifecycle_entries:
                sorted_by_age = sorted(
                    self._lifecycle_entries.values(),
                    key=lambda x: x.created_at
                )
                oldest_entry = sorted_by_age[0].created_at.isoformat()
                newest_entry = sorted_by_age[-1].created_at.isoformat()
            
            return {
                "total_entries": total_entries,
                "active_sessions": active_sessions,
                "cleanup_queue_size": cleanup_queue_size,
                "state_counts": state_counts,
                "oldest_entry": oldest_entry,
                "newest_entry": newest_entry,
                "last_updated": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get lifecycle status: {e}")
            return {"error": str(e)}
    
    async def force_cleanup_user_caches(self, user_id: str) -> Dict[str, Any]:
        """
        Force cleanup of all caches for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Cleanup results
        """
        try:
            user_entries = [
                entry for entry in self._lifecycle_entries.values()
                if entry.user_id == user_id
            ]
            
            caches_cleaned = []
            for entry in user_entries:
                await self._cleanup_cache_entry(entry)
                caches_cleaned.append(entry.cache_key)
            
            # Clean up user sessions
            user_sessions = [
                session_id for session_id, session in self._navigation_sessions.items()
                if session.user_id == user_id
            ]
            
            for session_id in user_sessions:
                del self._navigation_sessions[session_id]
            
            logger.info(f"Force cleanup completed for user {user_id}: {len(caches_cleaned)} caches")
            
            return {
                "user_id": user_id,
                "caches_cleaned": caches_cleaned,
                "sessions_cleaned": len(user_sessions)
            }
            
        except Exception as e:
            logger.error(f"Failed to force cleanup user caches: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close and cleanup resources."""
        try:
            # Cancel background tasks
            if self._cleanup_task:
                self._cleanup_task.cancel()
            if self._monitoring_task:
                self._monitoring_task.cancel()
            
            # Perform final cleanup
            await self._perform_scheduled_cleanup()
            
            logger.info("CacheLifecycleManager closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing CacheLifecycleManager: {e}")


# Global instance management
_lifecycle_manager_instance: Optional[CacheLifecycleManager] = None


def get_cache_lifecycle_manager() -> CacheLifecycleManager:
    """
    Get the global CacheLifecycleManager instance.
    
    Returns:
        CacheLifecycleManager instance
    """
    global _lifecycle_manager_instance
    
    if _lifecycle_manager_instance is None:
        _lifecycle_manager_instance = CacheLifecycleManager()
    
    return _lifecycle_manager_instance


async def cleanup_lifecycle_manager():
    """Cleanup the global lifecycle manager instance."""
    global _lifecycle_manager_instance
    
    if _lifecycle_manager_instance:
        await _lifecycle_manager_instance.close()
        _lifecycle_manager_instance = None