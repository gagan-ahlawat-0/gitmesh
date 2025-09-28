"""
Virtual Codebase Optimizer

Optimized file lookup and retrieval mechanisms with intelligent file caching
based on access patterns. Implements requirements 4.1, 4.2, 4.3, 4.4, 8.4, 9.1, 9.4
for faster file access and reduced cloud storage usage.

Key Features:
- Optimized file lookup and retrieval mechanisms
- Intelligent file caching based on access patterns
- Virtual file system mapping for O(1) file access
- Access pattern analysis and prediction
- Memory-efficient file storage and compression
"""

import os
import time
import json
import logging
import hashlib
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
from enum import Enum
import re

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


class AccessPattern(Enum):
    """File access pattern types."""
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    CLUSTERED = "clustered"
    FREQUENT = "frequent"
    RARE = "rare"


class CacheStrategy(Enum):
    """Caching strategy types."""
    EAGER = "eager"          # Cache immediately
    LAZY = "lazy"            # Cache on first access
    PREDICTIVE = "predictive" # Cache based on patterns
    ADAPTIVE = "adaptive"     # Adapt based on usage


@dataclass
class FileAccessMetrics:
    """File access metrics and patterns."""
    file_path: str
    access_count: int = 0
    last_accessed: datetime = None
    first_accessed: datetime = None
    access_pattern: AccessPattern = AccessPattern.RARE
    cache_hits: int = 0
    cache_misses: int = 0
    total_bytes_served: int = 0
    average_access_interval: float = 0.0
    predicted_next_access: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = datetime.now()
        if self.first_accessed is None:
            self.first_accessed = datetime.now()
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return self.cache_hits / total_requests
    
    def update_access(self, bytes_served: int = 0):
        """Update access metrics."""
        now = datetime.now()
        
        if self.access_count > 0:
            # Update average access interval
            time_since_last = (now - self.last_accessed).total_seconds()
            self.average_access_interval = (
                (self.average_access_interval * (self.access_count - 1) + time_since_last) / 
                self.access_count
            )
        
        self.access_count += 1
        self.last_accessed = now
        self.total_bytes_served += bytes_served
        
        # Update access pattern
        self._update_access_pattern()
        
        # Predict next access
        self._predict_next_access()
    
    def _update_access_pattern(self):
        """Update access pattern based on metrics."""
        if self.access_count < 2:
            self.access_pattern = AccessPattern.RARE
            return
        
        # Determine pattern based on access frequency and intervals
        if self.access_count > 10:
            if self.average_access_interval < 300:  # Less than 5 minutes
                self.access_pattern = AccessPattern.FREQUENT
            elif self.average_access_interval < 3600:  # Less than 1 hour
                self.access_pattern = AccessPattern.CLUSTERED
            else:
                self.access_pattern = AccessPattern.RANDOM
        elif self.access_count > 5:
            self.access_pattern = AccessPattern.CLUSTERED
        else:
            self.access_pattern = AccessPattern.RARE
    
    def _predict_next_access(self):
        """Predict next access time based on patterns."""
        if self.access_count < 2 or self.average_access_interval == 0:
            self.predicted_next_access = None
            return
        
        # Simple prediction based on average interval
        if self.access_pattern in [AccessPattern.FREQUENT, AccessPattern.CLUSTERED]:
            self.predicted_next_access = (
                self.last_accessed + timedelta(seconds=self.average_access_interval)
            )
        else:
            self.predicted_next_access = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, AccessPattern):
                data[key] = value.value
        return data

@
dataclass
class VirtualFile:
    """Virtual file representation with optimized storage."""
    path: str
    content: Optional[str] = None
    compressed_content: Optional[bytes] = None
    size_bytes: int = 0
    language: str = "text"
    encoding: str = "utf-8"
    checksum: str = ""
    cached_at: datetime = None
    expires_at: Optional[datetime] = None
    access_metrics: FileAccessMetrics = None
    
    def __post_init__(self):
        if self.cached_at is None:
            self.cached_at = datetime.now()
        if self.access_metrics is None:
            self.access_metrics = FileAccessMetrics(file_path=self.path)
        if self.content and not self.checksum:
            self.checksum = hashlib.md5(self.content.encode()).hexdigest()
        if self.content and not self.size_bytes:
            self.size_bytes = len(self.content.encode())
    
    def is_expired(self) -> bool:
        """Check if file cache is expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def get_content(self) -> Optional[str]:
        """Get file content, decompressing if necessary."""
        if self.content:
            return self.content
        elif self.compressed_content:
            return self._decompress_content()
        return None
    
    def set_content(self, content: str, compress: bool = True):
        """Set file content with optional compression."""
        self.content = content
        self.size_bytes = len(content.encode())
        self.checksum = hashlib.md5(content.encode()).hexdigest()
        
        if compress and len(content) > 1024:  # Compress files larger than 1KB
            self.compressed_content = self._compress_content(content)
            self.content = None  # Clear uncompressed content to save memory
    
    def _compress_content(self, content: str) -> bytes:
        """Compress content using gzip."""
        try:
            import gzip
            return gzip.compress(content.encode(self.encoding))
        except Exception as e:
            logger.warning(f"Failed to compress content for {self.path}: {e}")
            return content.encode(self.encoding)
    
    def _decompress_content(self) -> Optional[str]:
        """Decompress content using gzip."""
        try:
            import gzip
            return gzip.decompress(self.compressed_content).decode(self.encoding)
        except Exception as e:
            logger.error(f"Failed to decompress content for {self.path}: {e}")
            return None
    
    def update_access(self):
        """Update access metrics."""
        self.access_metrics.update_access(self.size_bytes)


class VirtualCodebaseOptimizer:
    """
    Virtual Codebase Optimizer for faster file access and intelligent caching.
    
    Implements optimized file lookup, retrieval mechanisms, and intelligent
    caching based on access patterns as specified in the cosmos optimization requirements.
    """
    
    def __init__(
        self,
        redis_manager: Optional[OptimizedRedisManager] = None,
        max_memory_mb: int = 100,
        compression_threshold: int = 1024,
        cache_ttl_seconds: int = 3600,
        max_files_in_memory: int = 1000
    ):
        """
        Initialize VirtualCodebaseOptimizer.
        
        Args:
            redis_manager: OptimizedRedisManager instance
            max_memory_mb: Maximum memory usage in MB
            compression_threshold: Compress files larger than this size
            cache_ttl_seconds: Default cache TTL in seconds
            max_files_in_memory: Maximum files to keep in memory
        """
        self.redis_manager = redis_manager or get_optimized_redis_manager()
        self.max_memory_mb = max_memory_mb
        self.compression_threshold = compression_threshold
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_files_in_memory = max_files_in_memory
        
        # Virtual file system
        self._virtual_files: Dict[str, VirtualFile] = {}
        self._file_index: Dict[str, Set[str]] = defaultdict(set)  # repo_key -> file_paths
        self._access_patterns: Dict[str, FileAccessMetrics] = {}
        
        # Caching strategies
        self._cache_strategies: Dict[str, CacheStrategy] = {}
        self._prefetch_queue: List[Tuple[str, str]] = []  # (repo_key, file_path)
        
        # Performance tracking
        self._performance_metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "bytes_served": 0,
            "compression_ratio": 0.0,
            "average_response_time": 0.0
        }
        
        # Status integration
        self.status_integration = get_redis_status_integration() if get_redis_status_integration else None
        
        # Background tasks
        self._optimization_task = None
        self._prefetch_task = None
        self._start_background_tasks()
        
        logger.info("VirtualCodebaseOptimizer initialized successfully")
    
    def _start_background_tasks(self):
        """Start background optimization tasks."""
        try:
            # Start optimization task
            self._optimization_task = asyncio.create_task(self._optimization_loop())
            
            # Start prefetch task
            self._prefetch_task = asyncio.create_task(self._prefetch_loop())
            
            logger.info("Virtual codebase optimization tasks started")
            
        except Exception as e:
            logger.warning(f"Failed to start background tasks: {e}")
    
    async def _optimization_loop(self):
        """Background optimization loop."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._optimize_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(60)
    
    async def _prefetch_loop(self):
        """Background prefetch loop."""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                await self._process_prefetch_queue()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in prefetch loop: {e}")
                await asyncio.sleep(30)
    
    async def initialize_repository(
        self,
        repo_key: str,
        repo_url: str,
        file_list: List[str],
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    ) -> Dict[str, Any]:
        """
        Initialize virtual codebase for a repository.
        
        Args:
            repo_key: Repository cache key
            repo_url: Repository URL
            file_list: List of file paths in the repository
            strategy: Caching strategy to use
            
        Returns:
            Initialization results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Initializing virtual codebase for {repo_key} with {len(file_list)} files")
            
            # Start status tracking
            operation_id = None
            if self.status_integration:
                operation_id = await self.status_integration.start_cache_operation(
                    operation_type="virtual_init",
                    cache_key=repo_key,
                    description=f"Initializing virtual codebase for {repo_url}"
                )
            
            # Set caching strategy
            self._cache_strategies[repo_key] = strategy
            
            # Initialize file index
            self._file_index[repo_key] = set(file_list)
            
            # Initialize access patterns for files
            for file_path in file_list:
                full_key = f"{repo_key}:{file_path}"
                if full_key not in self._access_patterns:
                    self._access_patterns[full_key] = FileAccessMetrics(file_path=file_path)
            
            # Determine initial files to cache based on strategy
            initial_cache_files = self._select_initial_cache_files(repo_key, file_list, strategy)
            
            # Pre-cache important files
            cached_count = 0
            for file_path in initial_cache_files:
                try:
                    await self._cache_file_content(repo_key, file_path)
                    cached_count += 1
                    
                    # Update progress
                    if self.status_integration and operation_id:
                        progress = (cached_count / len(initial_cache_files)) * 100
                        await self.status_integration.update_cache_progress(
                            operation_type="virtual_init",
                            cache_key=repo_key,
                            operation_id=operation_id,
                            progress=progress,
                            message=f"Cached {cached_count}/{len(initial_cache_files)} files"
                        )
                        
                except Exception as e:
                    logger.warning(f"Failed to pre-cache file {file_path}: {e}")
            
            elapsed_time = time.time() - start_time
            
            result = {
                "repo_key": repo_key,
                "total_files": len(file_list),
                "cached_files": cached_count,
                "strategy": strategy.value,
                "initialization_time": elapsed_time
            }
            
            # Complete status tracking
            if self.status_integration and operation_id:
                await self.status_integration.complete_cache_operation(
                    operation_type="virtual_init",
                    cache_key=repo_key,
                    operation_id=operation_id,
                    result=result
                )
            
            logger.info(f"Virtual codebase initialized for {repo_key}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to initialize virtual codebase for {repo_key}: {e}")
            
            if self.status_integration and operation_id:
                await self.status_integration.fail_cache_operation(
                    operation_type="virtual_init",
                    cache_key=repo_key,
                    operation_id=operation_id,
                    error=str(e)
                )
            
            raise  
  
    async def get_file_content(
        self,
        repo_key: str,
        file_path: str,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Get file content with optimized lookup and caching.
        
        Args:
            repo_key: Repository cache key
            file_path: File path within repository
            use_cache: Whether to use cached content
            
        Returns:
            File content or None if not found
        """
        start_time = time.time()
        full_key = f"{repo_key}:{file_path}"
        
        try:
            self._performance_metrics["total_requests"] += 1
            
            # Check if file exists in repository
            if repo_key not in self._file_index or file_path not in self._file_index[repo_key]:
                logger.debug(f"File not found in index: {file_path}")
                return None
            
            # Check virtual file cache first
            if use_cache and full_key in self._virtual_files:
                virtual_file = self._virtual_files[full_key]
                
                if not virtual_file.is_expired():
                    content = virtual_file.get_content()
                    if content:
                        # Update access metrics
                        virtual_file.update_access()
                        self._update_access_pattern(full_key)
                        
                        # Update performance metrics
                        self._performance_metrics["cache_hits"] += 1
                        self._performance_metrics["bytes_served"] += len(content)
                        
                        elapsed_time = time.time() - start_time
                        self._update_average_response_time(elapsed_time)
                        
                        logger.debug(f"Virtual cache hit: {file_path}")
                        return content
            
            # Cache miss - fetch from Redis/source
            self._performance_metrics["cache_misses"] += 1
            
            content = await self._fetch_file_content(repo_key, file_path)
            
            if content:
                # Cache the content
                await self._cache_file_content(repo_key, file_path, content)
                
                # Update access patterns
                self._update_access_pattern(full_key)
                
                # Schedule related files for prefetch
                await self._schedule_prefetch(repo_key, file_path)
                
                # Update performance metrics
                self._performance_metrics["bytes_served"] += len(content)
                
                elapsed_time = time.time() - start_time
                self._update_average_response_time(elapsed_time)
                
                logger.debug(f"File content fetched and cached: {file_path}")
                return content
            
            logger.warning(f"File content not found: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting file content for {file_path}: {e}")
            return None
    
    async def list_files(
        self,
        repo_key: str,
        pattern: Optional[str] = None,
        language: Optional[str] = None
    ) -> List[str]:
        """
        List files in repository with optional filtering.
        
        Args:
            repo_key: Repository cache key
            pattern: File pattern to match
            language: Programming language filter
            
        Returns:
            List of matching file paths
        """
        try:
            if repo_key not in self._file_index:
                logger.warning(f"Repository not found in index: {repo_key}")
                return []
            
            files = list(self._file_index[repo_key])
            
            # Apply pattern filter
            if pattern:
                import fnmatch
                files = [f for f in files if fnmatch.fnmatch(f.lower(), pattern.lower())]
            
            # Apply language filter
            if language:
                files = [f for f in files if self._detect_language(f) == language.lower()]
            
            return sorted(files)
            
        except Exception as e:
            logger.error(f"Error listing files for {repo_key}: {e}")
            return []
    
    def _select_initial_cache_files(
        self,
        repo_key: str,
        file_list: List[str],
        strategy: CacheStrategy
    ) -> List[str]:
        """
        Select initial files to cache based on strategy.
        
        Args:
            repo_key: Repository cache key
            file_list: List of all files
            strategy: Caching strategy
            
        Returns:
            List of files to cache initially
        """
        try:
            if strategy == CacheStrategy.EAGER:
                # Cache all small files immediately
                return [f for f in file_list if self._estimate_file_size(f) < 10240]  # < 10KB
            
            elif strategy == CacheStrategy.LAZY:
                # Cache only essential files
                essential_files = [
                    f for f in file_list 
                    if any(f.lower().endswith(ext) for ext in ['.md', '.txt', '.json', '.yaml', '.yml'])
                ]
                return essential_files[:10]  # Limit to 10 files
            
            elif strategy == CacheStrategy.PREDICTIVE:
                # Cache files likely to be accessed based on patterns
                important_files = []
                
                # Common important files
                priority_patterns = [
                    r'readme\.(md|txt)$',
                    r'package\.json$',
                    r'requirements\.txt$',
                    r'setup\.py$',
                    r'main\.(py|js|ts|java|cpp|c)$',
                    r'index\.(py|js|ts|html)$',
                    r'app\.(py|js|ts)$'
                ]
                
                for pattern in priority_patterns:
                    for file_path in file_list:
                        if re.search(pattern, file_path.lower()):
                            important_files.append(file_path)
                
                return important_files[:20]  # Limit to 20 files
            
            elif strategy == CacheStrategy.ADAPTIVE:
                # Start with predictive, adapt based on usage
                return self._select_initial_cache_files(repo_key, file_list, CacheStrategy.PREDICTIVE)
            
            return []
            
        except Exception as e:
            logger.error(f"Error selecting initial cache files: {e}")
            return []
    
    async def _cache_file_content(
        self,
        repo_key: str,
        file_path: str,
        content: Optional[str] = None
    ):
        """
        Cache file content in virtual file system.
        
        Args:
            repo_key: Repository cache key
            file_path: File path
            content: File content (if None, will fetch)
        """
        try:
            full_key = f"{repo_key}:{file_path}"
            
            # Fetch content if not provided
            if content is None:
                content = await self._fetch_file_content(repo_key, file_path)
                if not content:
                    return
            
            # Check memory limits
            await self._ensure_memory_limits()
            
            # Create virtual file
            virtual_file = VirtualFile(
                path=file_path,
                language=self._detect_language(file_path),
                expires_at=datetime.now() + timedelta(seconds=self.cache_ttl_seconds)
            )
            
            # Set content with compression
            virtual_file.set_content(content, compress=len(content) > self.compression_threshold)
            
            # Store in virtual file system
            self._virtual_files[full_key] = virtual_file
            
            logger.debug(f"Cached file content: {file_path} ({len(content)} bytes)")
            
        except Exception as e:
            logger.error(f"Error caching file content for {file_path}: {e}")
    
    async def _fetch_file_content(self, repo_key: str, file_path: str) -> Optional[str]:
        """
        Fetch file content from Redis cache.
        
        Args:
            repo_key: Repository cache key
            file_path: File path
            
        Returns:
            File content or None
        """
        try:
            # Use Redis manager to get cached context
            context_data = await self.redis_manager.get_cached_context(
                cache_key=repo_key,
                query=file_path,
                max_results=1
            )
            
            if context_data and "content" in context_data:
                return context_data["content"]
            
            # Fallback: try to get from repository data
            # This would integrate with existing repository services
            logger.debug(f"File content not found in cache: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching file content for {file_path}: {e}")
            return None
    
    def _update_access_pattern(self, full_key: str):
        """
        Update access pattern for a file.
        
        Args:
            full_key: Full file key (repo_key:file_path)
        """
        try:
            if full_key not in self._access_patterns:
                file_path = full_key.split(":", 1)[1]
                self._access_patterns[full_key] = FileAccessMetrics(file_path=file_path)
            
            metrics = self._access_patterns[full_key]
            metrics.update_access()
            
        except Exception as e:
            logger.error(f"Error updating access pattern for {full_key}: {e}")
    
    async def _schedule_prefetch(self, repo_key: str, file_path: str):
        """
        Schedule related files for prefetch based on access patterns.
        
        Args:
            repo_key: Repository cache key
            file_path: Currently accessed file path
        """
        try:
            # Find related files to prefetch
            related_files = self._find_related_files(repo_key, file_path)
            
            # Add to prefetch queue
            for related_file in related_files:
                if (repo_key, related_file) not in self._prefetch_queue:
                    self._prefetch_queue.append((repo_key, related_file))
            
        except Exception as e:
            logger.error(f"Error scheduling prefetch for {file_path}: {e}")
    
    def _find_related_files(self, repo_key: str, file_path: str) -> List[str]:
        """
        Find files related to the current file for prefetching.
        
        Args:
            repo_key: Repository cache key
            file_path: Current file path
            
        Returns:
            List of related file paths
        """
        try:
            related_files = []
            
            if repo_key not in self._file_index:
                return related_files
            
            # Get directory and filename
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(filename)[0]
            
            # Find files in same directory
            for other_file in self._file_index[repo_key]:
                if other_file == file_path:
                    continue
                
                other_dir = os.path.dirname(other_file)
                other_name = os.path.splitext(os.path.basename(other_file))[0]
                
                # Same directory
                if other_dir == directory:
                    related_files.append(other_file)
                
                # Similar names (test files, etc.)
                elif name_without_ext in other_name or other_name in name_without_ext:
                    related_files.append(other_file)
            
            # Limit to top 5 related files
            return related_files[:5]
            
        except Exception as e:
            logger.error(f"Error finding related files for {file_path}: {e}")
            return [] 
   
    async def _process_prefetch_queue(self):
        """Process the prefetch queue."""
        try:
            if not self._prefetch_queue:
                return
            
            # Process up to 5 files per batch
            batch_size = min(5, len(self._prefetch_queue))
            
            for _ in range(batch_size):
                if not self._prefetch_queue:
                    break
                
                repo_key, file_path = self._prefetch_queue.pop(0)
                full_key = f"{repo_key}:{file_path}"
                
                # Skip if already cached
                if full_key in self._virtual_files:
                    continue
                
                # Prefetch the file
                try:
                    await self._cache_file_content(repo_key, file_path)
                    logger.debug(f"Prefetched file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to prefetch file {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing prefetch queue: {e}")
    
    async def _optimize_cache(self):
        """Optimize cache by removing unused files and updating strategies."""
        try:
            logger.debug("Optimizing virtual codebase cache")
            
            current_time = datetime.now()
            removed_count = 0
            
            # Remove expired files
            expired_keys = [
                key for key, vfile in self._virtual_files.items()
                if vfile.is_expired()
            ]
            
            for key in expired_keys:
                del self._virtual_files[key]
                removed_count += 1
            
            # Remove least recently used files if memory is high
            if len(self._virtual_files) > self.max_files_in_memory:
                # Sort by last access time
                sorted_files = sorted(
                    self._virtual_files.items(),
                    key=lambda x: x[1].access_metrics.last_accessed
                )
                
                # Remove oldest 20%
                remove_count = len(sorted_files) // 5
                for key, _ in sorted_files[:remove_count]:
                    del self._virtual_files[key]
                    removed_count += 1
            
            # Update caching strategies based on access patterns
            self._update_caching_strategies()
            
            if removed_count > 0:
                logger.info(f"Cache optimization completed: removed {removed_count} files")
            
        except Exception as e:
            logger.error(f"Error optimizing cache: {e}")
    
    def _update_caching_strategies(self):
        """Update caching strategies based on access patterns."""
        try:
            for repo_key, strategy in self._cache_strategies.items():
                if strategy != CacheStrategy.ADAPTIVE:
                    continue
                
                # Analyze access patterns for this repository
                repo_patterns = [
                    metrics for key, metrics in self._access_patterns.items()
                    if key.startswith(f"{repo_key}:")
                ]
                
                if not repo_patterns:
                    continue
                
                # Calculate average access frequency
                avg_access_count = sum(p.access_count for p in repo_patterns) / len(repo_patterns)
                
                # Update strategy based on usage
                if avg_access_count > 10:
                    self._cache_strategies[repo_key] = CacheStrategy.EAGER
                elif avg_access_count > 5:
                    self._cache_strategies[repo_key] = CacheStrategy.PREDICTIVE
                else:
                    self._cache_strategies[repo_key] = CacheStrategy.LAZY
            
        except Exception as e:
            logger.error(f"Error updating caching strategies: {e}")
    
    async def _ensure_memory_limits(self):
        """Ensure memory usage stays within limits."""
        try:
            # Estimate current memory usage
            total_size = sum(
                vfile.size_bytes for vfile in self._virtual_files.values()
            )
            
            max_size_bytes = self.max_memory_mb * 1024 * 1024
            
            if total_size > max_size_bytes:
                # Remove files to free memory
                sorted_files = sorted(
                    self._virtual_files.items(),
                    key=lambda x: (x[1].access_metrics.access_count, x[1].access_metrics.last_accessed)
                )
                
                # Remove least used files until under limit
                for key, vfile in sorted_files:
                    del self._virtual_files[key]
                    total_size -= vfile.size_bytes
                    
                    if total_size <= max_size_bytes * 0.8:  # 80% of limit
                        break
                
                logger.info(f"Memory limit enforced: freed {(max_size_bytes - total_size) / 1024 / 1024:.1f} MB")
            
        except Exception as e:
            logger.error(f"Error ensuring memory limits: {e}")
    
    def _detect_language(self, file_path: str) -> str:
        """
        Detect programming language from file extension.
        
        Args:
            file_path: File path
            
        Returns:
            Language name
        """
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sh': 'bash',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.sql': 'sql'
        }
        
        _, ext = os.path.splitext(file_path.lower())
        return extension_map.get(ext, 'text')
    
    def _estimate_file_size(self, file_path: str) -> int:
        """
        Estimate file size based on extension and name.
        
        Args:
            file_path: File path
            
        Returns:
            Estimated size in bytes
        """
        # Simple heuristic based on file type
        language = self._detect_language(file_path)
        
        size_estimates = {
            'python': 2000,
            'javascript': 1500,
            'typescript': 1800,
            'java': 2500,
            'cpp': 3000,
            'c': 2000,
            'html': 1000,
            'css': 800,
            'markdown': 1200,
            'json': 500,
            'yaml': 300,
            'text': 500
        }
        
        return size_estimates.get(language, 1000)
    
    def _update_average_response_time(self, response_time: float):
        """Update average response time with exponential moving average."""
        alpha = 0.1  # Smoothing factor
        current_avg = self._performance_metrics["average_response_time"]
        
        if current_avg == 0:
            self._performance_metrics["average_response_time"] = response_time
        else:
            self._performance_metrics["average_response_time"] = (
                alpha * response_time + (1 - alpha) * current_avg
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        try:
            # Calculate additional metrics
            total_requests = self._performance_metrics["total_requests"]
            cache_hits = self._performance_metrics["cache_hits"]
            
            hit_rate = cache_hits / total_requests if total_requests > 0 else 0.0
            
            # Calculate compression ratio
            total_original_size = sum(vfile.size_bytes for vfile in self._virtual_files.values())
            total_compressed_size = sum(
                len(vfile.compressed_content) if vfile.compressed_content else vfile.size_bytes
                for vfile in self._virtual_files.values()
            )
            
            compression_ratio = (
                1.0 - (total_compressed_size / total_original_size)
                if total_original_size > 0 else 0.0
            )
            
            # Memory usage
            memory_usage_mb = total_original_size / (1024 * 1024)
            
            return {
                "performance": {
                    **self._performance_metrics,
                    "hit_rate": hit_rate,
                    "compression_ratio": compression_ratio
                },
                "cache_stats": {
                    "total_files_cached": len(self._virtual_files),
                    "total_repositories": len(self._file_index),
                    "memory_usage_mb": memory_usage_mb,
                    "max_memory_mb": self.max_memory_mb,
                    "prefetch_queue_size": len(self._prefetch_queue)
                },
                "access_patterns": {
                    "total_tracked_files": len(self._access_patterns),
                    "frequent_files": len([
                        p for p in self._access_patterns.values()
                        if p.access_pattern == AccessPattern.FREQUENT
                    ]),
                    "rare_files": len([
                        p for p in self._access_patterns.values()
                        if p.access_pattern == AccessPattern.RARE
                    ])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}
    
    async def cleanup_repository(self, repo_key: str) -> Dict[str, Any]:
        """
        Clean up virtual codebase for a repository.
        
        Args:
            repo_key: Repository cache key
            
        Returns:
            Cleanup results
        """
        try:
            logger.info(f"Cleaning up virtual codebase for {repo_key}")
            
            # Remove virtual files
            files_removed = 0
            keys_to_remove = [key for key in self._virtual_files.keys() if key.startswith(f"{repo_key}:")]
            
            for key in keys_to_remove:
                del self._virtual_files[key]
                files_removed += 1
            
            # Remove from file index
            if repo_key in self._file_index:
                del self._file_index[repo_key]
            
            # Remove access patterns
            patterns_removed = 0
            pattern_keys_to_remove = [key for key in self._access_patterns.keys() if key.startswith(f"{repo_key}:")]
            
            for key in pattern_keys_to_remove:
                del self._access_patterns[key]
                patterns_removed += 1
            
            # Remove caching strategy
            if repo_key in self._cache_strategies:
                del self._cache_strategies[repo_key]
            
            # Remove from prefetch queue
            self._prefetch_queue = [
                (rkey, fpath) for rkey, fpath in self._prefetch_queue
                if rkey != repo_key
            ]
            
            result = {
                "repo_key": repo_key,
                "files_removed": files_removed,
                "patterns_removed": patterns_removed
            }
            
            logger.info(f"Virtual codebase cleanup completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning up virtual codebase for {repo_key}: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close and cleanup resources."""
        try:
            # Cancel background tasks
            if self._optimization_task:
                self._optimization_task.cancel()
            if self._prefetch_task:
                self._prefetch_task.cancel()
            
            # Perform final optimization
            await self._optimize_cache()
            
            logger.info("VirtualCodebaseOptimizer closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing VirtualCodebaseOptimizer: {e}")


# Global instance management
_virtual_optimizer_instance: Optional[VirtualCodebaseOptimizer] = None


def get_virtual_codebase_optimizer() -> VirtualCodebaseOptimizer:
    """
    Get the global VirtualCodebaseOptimizer instance.
    
    Returns:
        VirtualCodebaseOptimizer instance
    """
    global _virtual_optimizer_instance
    
    if _virtual_optimizer_instance is None:
        _virtual_optimizer_instance = VirtualCodebaseOptimizer()
    
    return _virtual_optimizer_instance


async def cleanup_virtual_optimizer():
    """Cleanup the global virtual optimizer instance."""
    global _virtual_optimizer_instance
    
    if _virtual_optimizer_instance:
        await _virtual_optimizer_instance.close()
        _virtual_optimizer_instance = None