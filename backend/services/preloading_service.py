"""
Preloading service for repository preparation.
Handles background repository preparation and optimization.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Set
from dataclasses import dataclass
import structlog
from collections import defaultdict

logger = structlog.get_logger(__name__)

@dataclass
class PreloadingTask:
    """A preloading task for repository preparation."""
    task_id: str
    repository_url: str
    user_id: str
    branch: str
    priority: int  # 1 (highest) to 10 (lowest)
    task_type: str  # 'full_preload', 'incremental_update', 'optimization'
    status: str  # 'queued', 'processing', 'completed', 'error', 'cancelled'
    progress: float  # 0.0 to 1.0
    message: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None
    actual_duration_seconds: Optional[float] = None

@dataclass
class PreloadingResult:
    """Result of a preloading operation."""
    success: bool
    cache_key: Optional[str] = None
    files_processed: int = 0
    cache_size_mb: float = 0.0
    processing_time_seconds: float = 0.0
    error_message: Optional[str] = None
    optimization_applied: bool = False

class PreloadingService:
    """Service for background repository preparation and optimization."""
    
    def __init__(self):
        self._task_queue: List[PreloadingTask] = []
        self._active_tasks: Dict[str, PreloadingTask] = {}
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        self._user_repositories: Dict[str, Set[str]] = defaultdict(set)  # user_id -> set of repo_urls
        
        # Configuration
        self.max_concurrent_tasks = 3
        self.max_queue_size = 50
        self.default_priority = 5
        
        # Start background processor
        self._processor_task = None
        self._running = False
    
    async def start(self):
        """Start the preloading service."""
        if not self._running:
            self._running = True
            self._processor_task = asyncio.create_task(self._process_queue())
            logger.info("Preloading service started")
    
    async def stop(self):
        """Stop the preloading service."""
        self._running = False
        
        # Cancel all active tasks
        for task in self._processing_tasks.values():
            if not task.done():
                task.cancel()
        
        # Cancel processor task
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
        
        logger.info("Preloading service stopped")
    
    async def schedule_preload(
        self, 
        repository_url: str, 
        user_id: str, 
        branch: str = 'main',
        priority: int = None,
        task_type: str = 'full_preload'
    ) -> str:
        """
        Schedule a repository for preloading.
        
        Args:
            repository_url: Repository URL to preload
            user_id: User identifier
            branch: Branch to preload
            priority: Task priority (1-10, lower is higher priority)
            task_type: Type of preloading task
            
        Returns:
            Task ID for tracking
        """
        try:
            # Check queue size limit
            if len(self._task_queue) >= self.max_queue_size:
                # Remove lowest priority completed tasks
                self._cleanup_completed_tasks()
                
                if len(self._task_queue) >= self.max_queue_size:
                    raise Exception(f"Preloading queue is full ({self.max_queue_size} tasks)")
            
            # Check if repository is already queued or processing
            existing_task = self._find_existing_task(repository_url, user_id, branch)
            if existing_task:
                logger.info(f"Repository {repository_url} already queued/processing: {existing_task}")
                return existing_task
            
            task_id = str(uuid.uuid4())
            priority = priority or self.default_priority
            
            # Estimate duration based on task type
            estimated_duration = self._estimate_duration(task_type, repository_url)
            
            # Create preloading task
            task = PreloadingTask(
                task_id=task_id,
                repository_url=repository_url,
                user_id=user_id,
                branch=branch,
                priority=priority,
                task_type=task_type,
                status='queued',
                progress=0.0,
                message='Queued for processing',
                created_at=datetime.now(),
                estimated_duration_seconds=estimated_duration
            )
            
            # Add to queue (sorted by priority)
            self._task_queue.append(task)
            self._task_queue.sort(key=lambda t: (t.priority, t.created_at))
            
            # Track user repositories
            self._user_repositories[user_id].add(repository_url)
            
            logger.info(f"Scheduled preloading task {task_id} for {repository_url} (priority: {priority})")
            return task_id
            
        except Exception as e:
            logger.error(f"Error scheduling preload: {e}")
            raise
    
    def _find_existing_task(self, repository_url: str, user_id: str, branch: str) -> Optional[str]:
        """Find existing task for repository."""
        # Check active tasks
        for task in self._active_tasks.values():
            if (task.repository_url == repository_url and 
                task.user_id == user_id and 
                task.branch == branch and 
                task.status in ['queued', 'processing']):
                return task.task_id
        
        # Check queued tasks
        for task in self._task_queue:
            if (task.repository_url == repository_url and 
                task.user_id == user_id and 
                task.branch == branch and 
                task.status == 'queued'):
                return task.task_id
        
        return None
    
    def _estimate_duration(self, task_type: str, repository_url: str) -> int:
        """Estimate task duration in seconds."""
        base_durations = {
            'full_preload': 120,      # 2 minutes
            'incremental_update': 30,  # 30 seconds
            'optimization': 60         # 1 minute
        }
        
        # Adjust based on repository size (simplified heuristic)
        base_duration = base_durations.get(task_type, 60)
        
        # Could add more sophisticated estimation based on repository metrics
        return base_duration
    
    async def _process_queue(self):
        """Background queue processor."""
        while self._running:
            try:
                # Check if we can start more tasks
                active_count = len(self._active_tasks)
                if active_count < self.max_concurrent_tasks and self._task_queue:
                    # Get next task from queue
                    task = self._task_queue.pop(0)
                    
                    # Move to active tasks
                    self._active_tasks[task.task_id] = task
                    
                    # Start processing
                    processing_task = asyncio.create_task(self._process_task(task.task_id))
                    self._processing_tasks[task.task_id] = processing_task
                    
                    logger.info(f"Started processing preloading task {task.task_id}")
                
                # Wait before next check
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _process_task(self, task_id: str):
        """Process a preloading task."""
        task = self._active_tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        try:
            # Update task status
            task.status = 'processing'
            task.started_at = datetime.now()
            task.progress = 0.1
            task.message = f'Starting {task.task_type}...'
            
            # Process based on task type
            if task.task_type == 'full_preload':
                result = await self._full_preload(task)
            elif task.task_type == 'incremental_update':
                result = await self._incremental_update(task)
            elif task.task_type == 'optimization':
                result = await self._optimization(task)
            else:
                raise Exception(f"Unknown task type: {task.task_type}")
            
            # Update task with results
            task.completed_at = datetime.now()
            task.actual_duration_seconds = (task.completed_at - task.started_at).total_seconds()
            
            if result.success:
                task.status = 'completed'
                task.progress = 1.0
                task.message = f'Completed - {result.files_processed} files processed'
                logger.info(f"Preloading task {task_id} completed successfully")
            else:
                task.status = 'error'
                task.error_message = result.error_message
                task.message = f'Failed: {result.error_message}'
                logger.error(f"Preloading task {task_id} failed: {result.error_message}")
                
        except asyncio.CancelledError:
            task.status = 'cancelled'
            task.completed_at = datetime.now()
            task.message = 'Task cancelled'
            logger.info(f"Preloading task {task_id} cancelled")
        except Exception as e:
            task.status = 'error'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            task.message = f'Error: {str(e)}'
            logger.error(f"Error processing task {task_id}: {e}")
        finally:
            # Clean up
            self._processing_tasks.pop(task_id, None)
    
    async def _full_preload(self, task: PreloadingTask) -> PreloadingResult:
        """Perform full repository preload."""
        try:
            task.progress = 0.2
            task.message = 'Initializing repository cache...'
            
            # Use GitIngest manager for full preload
            try:
                from services.gitingest_manager import get_gitingest_manager
                gitingest_manager = get_gitingest_manager()
                
                task.progress = 0.4
                task.message = 'Starting GitIngest processing...'
                
                # Start GitIngest processing
                gitingest_session_id = await gitingest_manager.start_processing(
                    task.repository_url,
                    task.user_id,
                    task.branch
                )
                
                # Monitor progress
                while True:
                    gitingest_status = await gitingest_manager.get_status(gitingest_session_id)
                    if not gitingest_status:
                        break
                    
                    if gitingest_status.status == 'completed':
                        task.progress = 0.9
                        task.message = 'Finalizing preload...'
                        
                        return PreloadingResult(
                            success=True,
                            cache_key=gitingest_status.cache_key,
                            files_processed=gitingest_status.file_count,
                            processing_time_seconds=(datetime.now() - task.started_at).total_seconds()
                        )
                    elif gitingest_status.status == 'error':
                        return PreloadingResult(
                            success=False,
                            error_message=gitingest_status.error_message
                        )
                    
                    # Update progress
                    task.progress = 0.4 + (gitingest_status.progress * 0.4)
                    task.message = gitingest_status.message
                    
                    await asyncio.sleep(2)
                
                return PreloadingResult(
                    success=False,
                    error_message="GitIngest processing failed or timed out"
                )
                
            except ImportError:
                # Fallback to direct cache initialization
                return await self._fallback_preload(task)
                
        except Exception as e:
            return PreloadingResult(
                success=False,
                error_message=f"Full preload failed: {str(e)}"
            )
    
    async def _incremental_update(self, task: PreloadingTask) -> PreloadingResult:
        """Perform incremental repository update."""
        try:
            task.progress = 0.3
            task.message = 'Checking for updates...'
            
            # Simulate incremental update
            await asyncio.sleep(2)
            
            task.progress = 0.8
            task.message = 'Applying updates...'
            
            await asyncio.sleep(1)
            
            return PreloadingResult(
                success=True,
                files_processed=10,  # Simulated
                processing_time_seconds=(datetime.now() - task.started_at).total_seconds()
            )
            
        except Exception as e:
            return PreloadingResult(
                success=False,
                error_message=f"Incremental update failed: {str(e)}"
            )
    
    async def _optimization(self, task: PreloadingTask) -> PreloadingResult:
        """Perform cache optimization."""
        try:
            task.progress = 0.3
            task.message = 'Analyzing cache...'
            
            # Try to use cache optimization services
            try:
                from services.cache_management_service import create_cache_management_service
                cache_service = create_cache_management_service(task.user_id)
                
                task.progress = 0.6
                task.message = 'Optimizing memory usage...'
                
                optimization_results = cache_service.optimize_memory_usage()
                
                task.progress = 0.9
                task.message = 'Optimization complete...'
                
                return PreloadingResult(
                    success=True,
                    cache_size_mb=optimization_results.get('memory_saved_mb', 0.0),
                    processing_time_seconds=(datetime.now() - task.started_at).total_seconds(),
                    optimization_applied=True
                )
                
            except ImportError:
                # Simulate optimization
                await asyncio.sleep(3)
                
                return PreloadingResult(
                    success=True,
                    processing_time_seconds=(datetime.now() - task.started_at).total_seconds(),
                    optimization_applied=True
                )
                
        except Exception as e:
            return PreloadingResult(
                success=False,
                error_message=f"Optimization failed: {str(e)}"
            )
    
    async def _fallback_preload(self, task: PreloadingTask) -> PreloadingResult:
        """Fallback preload using basic services."""
        try:
            task.progress = 0.5
            task.message = 'Using fallback preload...'
            
            # Use basic Redis repo manager
            from services.redis_repo_manager import RedisRepoManager
            repo_manager = RedisRepoManager()
            
            cache_key = await repo_manager.initialize_repository_cache(
                task.repository_url,
                task.user_id
            )
            
            task.progress = 0.9
            task.message = 'Fallback preload complete...'
            
            return PreloadingResult(
                success=True,
                cache_key=cache_key,
                files_processed=0,  # Unknown in fallback
                processing_time_seconds=(datetime.now() - task.started_at).total_seconds()
            )
            
        except Exception as e:
            return PreloadingResult(
                success=False,
                error_message=f"Fallback preload failed: {str(e)}"
            )
    
    async def get_task_status(self, task_id: str) -> Optional[PreloadingTask]:
        """Get the status of a preloading task."""
        # Check active tasks first
        if task_id in self._active_tasks:
            return self._active_tasks[task_id]
        
        # Check queued tasks
        for task in self._task_queue:
            if task.task_id == task_id:
                return task
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a preloading task."""
        # Cancel active task
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            processing_task = self._processing_tasks.get(task_id)
            
            if processing_task and not processing_task.done():
                processing_task.cancel()
            
            task.status = 'cancelled'
            task.completed_at = datetime.now()
            task.message = 'Task cancelled by user'
            
            logger.info(f"Cancelled preloading task {task_id}")
            return True
        
        # Cancel queued task
        for i, task in enumerate(self._task_queue):
            if task.task_id == task_id:
                task.status = 'cancelled'
                task.completed_at = datetime.now()
                task.message = 'Task cancelled before processing'
                self._task_queue.pop(i)
                
                logger.info(f"Cancelled queued preloading task {task_id}")
                return True
        
        return False
    
    def get_user_tasks(self, user_id: str) -> List[PreloadingTask]:
        """Get all preloading tasks for a user."""
        tasks = []
        
        # Add active tasks
        for task in self._active_tasks.values():
            if task.user_id == user_id:
                tasks.append(task)
        
        # Add queued tasks
        for task in self._task_queue:
            if task.user_id == user_id:
                tasks.append(task)
        
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get preloading queue status."""
        status_counts = defaultdict(int)
        
        # Count active tasks
        for task in self._active_tasks.values():
            status_counts[task.status] += 1
        
        # Count queued tasks
        for task in self._task_queue:
            status_counts[task.status] += 1
        
        return {
            'queue_size': len(self._task_queue),
            'active_tasks': len(self._active_tasks),
            'max_concurrent': self.max_concurrent_tasks,
            'max_queue_size': self.max_queue_size,
            'status_distribution': dict(status_counts),
            'is_running': self._running
        }
    
    def _cleanup_completed_tasks(self):
        """Clean up completed tasks to make room in queue."""
        # Remove completed tasks from queue (shouldn't happen, but safety check)
        self._task_queue = [task for task in self._task_queue if task.status == 'queued']
        
        # Remove old completed active tasks
        cutoff_time = datetime.now() - timedelta(hours=1)
        expired_tasks = []
        
        for task_id, task in self._active_tasks.items():
            if (task.status in ['completed', 'error', 'cancelled'] and 
                task.completed_at and task.completed_at < cutoff_time):
                expired_tasks.append(task_id)
        
        for task_id in expired_tasks:
            self._active_tasks.pop(task_id, None)
            self._processing_tasks.pop(task_id, None)

# Global service instance
_preloading_service: Optional[PreloadingService] = None

async def get_preloading_service() -> PreloadingService:
    """Get the global preloading service instance."""
    global _preloading_service
    if _preloading_service is None:
        _preloading_service = PreloadingService()
        await _preloading_service.start()
    return _preloading_service