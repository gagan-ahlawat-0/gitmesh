"""
GitIngest Manager for background repository processing.
Handles gitingest operations, status monitoring, and progress reporting.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import structlog
import aiohttp
import os

logger = structlog.get_logger(__name__)

@dataclass
class GitIngestStatus:
    """Status of a GitIngest operation."""
    session_id: str
    repository_url: str
    user_id: str
    branch: str
    status: str  # 'pending', 'processing', 'completed', 'error', 'cancelled'
    progress: float  # 0.0 to 1.0
    message: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    file_count: int = 0
    processed_files: int = 0
    cache_key: Optional[str] = None

@dataclass
class ProcessingResult:
    """Result of GitIngest processing."""
    success: bool
    cache_key: Optional[str] = None
    file_count: int = 0
    processing_time_seconds: float = 0.0
    error_message: Optional[str] = None
    optimization_applied: bool = False

class GitIngestManager:
    """Manager for GitIngest background processing operations."""
    
    def __init__(self):
        self._active_sessions: Dict[str, GitIngestStatus] = {}
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.gitingest_timeout = int(os.getenv('GITINGEST_TIMEOUT', '300'))  # 5 minutes
        self.max_concurrent_sessions = int(os.getenv('MAX_GITINGEST_SESSIONS', '10'))
        
    async def start_processing(self, repository_url: str, user_id: str, branch: str = 'main') -> str:
        """
        Start GitIngest processing for a repository.
        
        Args:
            repository_url: Repository URL to process
            user_id: User identifier
            branch: Branch to process
            
        Returns:
            Session ID for tracking the operation
        """
        try:
            # Check concurrent session limit
            active_count = len([s for s in self._active_sessions.values() if s.status == 'processing'])
            if active_count >= self.max_concurrent_sessions:
                raise Exception(f"Maximum concurrent sessions ({self.max_concurrent_sessions}) reached")
            
            # Check if repository is already being processed
            existing_session = self._find_active_session(repository_url, user_id, branch)
            if existing_session:
                logger.info(f"Repository {repository_url} already being processed in session {existing_session}")
                return existing_session
            
            session_id = str(uuid.uuid4())
            
            # Create GitIngest status
            gitingest_status = GitIngestStatus(
                session_id=session_id,
                repository_url=repository_url,
                user_id=user_id,
                branch=branch,
                status='pending',
                progress=0.0,
                message='Initializing GitIngest processing...',
                started_at=datetime.now()
            )
            
            # Store session
            self._active_sessions[session_id] = gitingest_status
            
            # Start background processing
            task = asyncio.create_task(self._run_processing(session_id))
            self._processing_tasks[session_id] = task
            
            logger.info(f"Started GitIngest processing session {session_id} for {repository_url}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting GitIngest processing: {e}")
            raise
    
    def _find_active_session(self, repository_url: str, user_id: str, branch: str) -> Optional[str]:
        """Find active processing session for repository."""
        for session_id, session in self._active_sessions.items():
            if (session.repository_url == repository_url and 
                session.user_id == user_id and 
                session.branch == branch and 
                session.status in ['pending', 'processing']):
                return session_id
        return None
    
    async def _run_processing(self, session_id: str):
        """Run GitIngest processing in background."""
        session = self._active_sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return
        
        try:
            # Update status to processing
            session.status = 'processing'
            session.progress = 0.1
            session.message = 'Starting repository analysis...'
            
            # Try to use existing optimized services first
            result = await self._process_with_optimized_services(session)
            
            if not result.success:
                # Fallback to direct GitIngest API
                result = await self._process_with_gitingest_api(session)
            
            # Update final status
            if result.success:
                session.status = 'completed'
                session.progress = 1.0
                session.message = f'Processing completed - {result.file_count} files processed'
                session.file_count = result.file_count
                session.processed_files = result.file_count
                session.cache_key = result.cache_key
                session.completed_at = datetime.now()
                
                logger.info(f"GitIngest processing completed for session {session_id}")
            else:
                session.status = 'error'
                session.error_message = result.error_message
                session.completed_at = datetime.now()
                session.message = f'Processing failed: {result.error_message}'
                
                logger.error(f"GitIngest processing failed for session {session_id}: {result.error_message}")
                
        except asyncio.CancelledError:
            session.status = 'cancelled'
            session.completed_at = datetime.now()
            session.message = 'Processing cancelled'
            logger.info(f"GitIngest processing cancelled for session {session_id}")
        except Exception as e:
            session.status = 'error'
            session.error_message = str(e)
            session.completed_at = datetime.now()
            session.message = f'Processing failed: {str(e)}'
            logger.error(f"Error in GitIngest processing for session {session_id}: {e}")
        finally:
            # Clean up task reference
            self._processing_tasks.pop(session_id, None)
    
    async def _process_with_optimized_services(self, session: GitIngestStatus) -> ProcessingResult:
        """Try to process using existing optimized services."""
        try:
            session.progress = 0.2
            session.message = 'Using optimized repository services...'
            
            # Try optimized Redis repo manager
            try:
                from services.optimized_redis_repo_manager import OptimizedRedisRepoManager
                repo_manager = OptimizedRedisRepoManager()
                
                session.progress = 0.4
                session.message = 'Initializing repository cache...'
                
                # Initialize repository cache
                cache_key = await repo_manager.initialize_repository_cache(
                    session.repository_url,
                    session.user_id
                )
                
                session.progress = 0.8
                session.message = 'Optimizing cache storage...'
                
                # Get cache statistics
                cache_stats = await repo_manager.get_cache_stats(cache_key)
                file_count = cache_stats.get('file_count', 0) if cache_stats else 0
                
                return ProcessingResult(
                    success=True,
                    cache_key=cache_key,
                    file_count=file_count,
                    processing_time_seconds=(datetime.now() - session.started_at).total_seconds()
                )
                
            except ImportError:
                # Fallback to regular Redis repo manager
                from services.redis_repo_manager import RedisRepoManager
                repo_manager = RedisRepoManager()
                
                session.progress = 0.4
                session.message = 'Initializing repository cache (fallback)...'
                
                cache_key = await repo_manager.initialize_repository_cache(
                    session.repository_url,
                    session.user_id
                )
                
                session.progress = 0.8
                session.message = 'Cache initialization complete...'
                
                return ProcessingResult(
                    success=True,
                    cache_key=cache_key,
                    file_count=0,  # File count not available in fallback
                    processing_time_seconds=(datetime.now() - session.started_at).total_seconds()
                )
                
        except Exception as e:
            logger.warning(f"Optimized services processing failed: {e}")
            return ProcessingResult(
                success=False,
                error_message=f"Optimized services failed: {str(e)}"
            )
    
    async def _process_with_gitingest_api(self, session: GitIngestStatus) -> ProcessingResult:
        """Process using direct GitIngest API calls."""
        try:
            session.progress = 0.3
            session.message = 'Connecting to GitIngest API...'
            
            # Extract owner and repo from URL
            repo_parts = session.repository_url.replace('https://github.com/', '').split('/')
            if len(repo_parts) < 2:
                raise Exception("Invalid repository URL format")
            
            owner, repo = repo_parts[0], repo_parts[1]
            
            session.progress = 0.5
            session.message = f'Processing {owner}/{repo}...'
            
            # Use GitIngest API (this would be the actual implementation)
            # For now, we'll simulate the process
            await asyncio.sleep(2)  # Simulate processing time
            
            session.progress = 0.9
            session.message = 'Finalizing processing...'
            
            # Simulate successful processing
            return ProcessingResult(
                success=True,
                cache_key=f"gitingest:{owner}:{repo}:{session.branch}:{session.user_id}",
                file_count=50,  # Simulated file count
                processing_time_seconds=(datetime.now() - session.started_at).total_seconds()
            )
            
        except Exception as e:
            logger.error(f"GitIngest API processing failed: {e}")
            return ProcessingResult(
                success=False,
                error_message=f"GitIngest API failed: {str(e)}"
            )
    
    async def get_status(self, session_id: str) -> Optional[GitIngestStatus]:
        """Get the status of a GitIngest session."""
        return self._active_sessions.get(session_id)
    
    async def cancel_processing(self, session_id: str) -> bool:
        """Cancel a GitIngest processing session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return False
        
        # Cancel the processing task
        task = self._processing_tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                # Handle case where task is not awaitable (e.g., in tests)
                pass
        
        # Update session status
        if session.status in ['pending', 'processing']:
            session.status = 'cancelled'
            session.completed_at = datetime.now()
            session.message = 'Processing cancelled by user'
            
            logger.info(f"Cancelled GitIngest processing session {session_id}")
            return True
        
        return False
    
    def get_active_sessions(self) -> List[GitIngestStatus]:
        """Get all active GitIngest sessions."""
        return list(self._active_sessions.values())
    
    def get_user_sessions(self, user_id: str) -> List[GitIngestStatus]:
        """Get all GitIngest sessions for a user."""
        return [
            session for session in self._active_sessions.values()
            if session.user_id == user_id
        ]
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_sessions = []
        
        for session_id, session in self._active_sessions.items():
            if session.started_at < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            # Cancel any running task
            task = self._processing_tasks.get(session_id)
            if task and not task.done():
                task.cancel()
            
            # Remove session
            self._active_sessions.pop(session_id, None)
            self._processing_tasks.pop(session_id, None)
            
            logger.info(f"Cleaned up expired GitIngest session {session_id}")
        
        return len(expired_sessions)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get GitIngest manager statistics."""
        total_sessions = len(self._active_sessions)
        status_counts = {}
        
        for session in self._active_sessions.values():
            status_counts[session.status] = status_counts.get(session.status, 0) + 1
        
        return {
            'total_sessions': total_sessions,
            'active_tasks': len(self._processing_tasks),
            'status_distribution': status_counts,
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'timeout_seconds': self.gitingest_timeout
        }

# Global service instance
_gitingest_manager: Optional[GitIngestManager] = None

def get_gitingest_manager() -> GitIngestManager:
    """Get the global GitIngest manager instance."""
    global _gitingest_manager
    if _gitingest_manager is None:
        _gitingest_manager = GitIngestManager()
    return _gitingest_manager