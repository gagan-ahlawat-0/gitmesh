"""
Auto-initialization service for detecting page navigation and triggering gitingest.
Implements automatic repository caching when users visit /contribution pages.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import structlog
import re

logger = structlog.get_logger(__name__)

@dataclass
class InitializationStatus:
    """Status of auto-initialization process."""
    session_id: str
    repository_url: str
    user_id: str
    status: str  # 'initializing', 'ready', 'error', 'cancelled'
    progress: float  # 0.0 to 1.0
    message: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    gitingest_session_id: Optional[str] = None

@dataclass
class NavigationEvent:
    """Navigation event data."""
    user_id: str
    from_page: str
    to_page: str
    repository_url: Optional[str] = None
    repository_owner: Optional[str] = None
    repository_name: Optional[str] = None
    branch: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class AutoInitService:
    """Service to detect page navigation and automatically initialize repository caching."""
    
    def __init__(self):
        self._active_sessions: Dict[str, InitializationStatus] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> list of session_ids
        self._contribution_page_pattern = re.compile(r'^/contribution/([^/]+)/([^/]+)(?:/([^/]+))?/?$')
        
    def _extract_repository_info(self, page_url: str) -> Optional[Dict[str, str]]:
        """Extract repository information from contribution page URL."""
        match = self._contribution_page_pattern.match(page_url)
        if match:
            owner, repo, branch = match.groups()
            return {
                'owner': owner,
                'repo': repo,
                'branch': branch or 'main',
                'repository_url': f"https://github.com/{owner}/{repo}",
                'repository_name': f"{owner}/{repo}"
            }
        return None
    
    def _is_contribution_page(self, page_url: str) -> bool:
        """Check if the page URL is a contribution page."""
        return bool(self._contribution_page_pattern.match(page_url))
    
    async def on_page_visit(self, user_id: str, page_url: str, from_page: str = None) -> Optional[str]:
        """
        Handle page visit and trigger auto-initialization if needed.
        
        Args:
            user_id: User identifier
            page_url: Current page URL
            from_page: Previous page URL (optional)
            
        Returns:
            Session ID if initialization was triggered, None otherwise
        """
        try:
            # Check if this is a contribution page
            if not self._is_contribution_page(page_url):
                logger.debug(f"Page {page_url} is not a contribution page, skipping auto-init")
                return None
            
            # Extract repository information
            repo_info = self._extract_repository_info(page_url)
            if not repo_info:
                logger.warning(f"Could not extract repository info from {page_url}")
                return None
            
            repository_url = repo_info['repository_url']
            
            # Check if we already have an active session for this user and repository
            existing_session = self._find_active_session(user_id, repository_url)
            if existing_session:
                logger.info(f"Found existing session {existing_session} for {repository_url}")
                return existing_session
            
            # Create navigation event
            nav_event = NavigationEvent(
                user_id=user_id,
                from_page=from_page or '',
                to_page=page_url,
                repository_url=repository_url,
                repository_owner=repo_info['owner'],
                repository_name=repo_info['repo'],
                branch=repo_info['branch']
            )
            
            # Start auto-initialization
            session_id = await self._start_initialization(nav_event)
            
            logger.info(f"Started auto-initialization session {session_id} for {repository_url}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error in on_page_visit: {e}")
            return None
    
    def _find_active_session(self, user_id: str, repository_url: str) -> Optional[str]:
        """Find active initialization session for user and repository."""
        user_sessions = self._user_sessions.get(user_id, [])
        for session_id in user_sessions:
            session = self._active_sessions.get(session_id)
            if (session and 
                session.repository_url == repository_url and 
                session.status in ['initializing', 'ready']):
                return session_id
        return None
    
    async def _start_initialization(self, nav_event: NavigationEvent) -> str:
        """Start the initialization process."""
        session_id = str(uuid.uuid4())
        
        # Create initialization status
        init_status = InitializationStatus(
            session_id=session_id,
            repository_url=nav_event.repository_url,
            user_id=nav_event.user_id,
            status='initializing',
            progress=0.0,
            message='Starting repository initialization...',
            started_at=datetime.now()
        )
        
        # Store session
        self._active_sessions[session_id] = init_status
        
        # Add to user sessions
        if nav_event.user_id not in self._user_sessions:
            self._user_sessions[nav_event.user_id] = []
        self._user_sessions[nav_event.user_id].append(session_id)
        
        # Start background initialization
        asyncio.create_task(self._run_initialization(session_id, nav_event))
        
        return session_id
    
    async def _run_initialization(self, session_id: str, nav_event: NavigationEvent):
        """Run the initialization process in background."""
        try:
            session = self._active_sessions.get(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return
            
            # Update progress: Starting
            session.progress = 0.1
            session.message = "Initializing GitIngest service..."
            
            # Import GitIngest manager
            try:
                from services.gitingest_manager import GitIngestManager
                gitingest_manager = GitIngestManager()
            except ImportError:
                # Fallback to existing services
                logger.warning("GitIngestManager not available, using fallback")
                await self._fallback_initialization(session_id, nav_event)
                return
            
            # Start GitIngest process
            session.progress = 0.3
            session.message = "Starting repository processing..."
            
            gitingest_session_id = await gitingest_manager.start_processing(
                repository_url=nav_event.repository_url,
                user_id=nav_event.user_id,
                branch=nav_event.branch
            )
            
            session.gitingest_session_id = gitingest_session_id
            session.progress = 0.5
            session.message = "Processing repository files..."
            
            # Monitor GitIngest progress
            await self._monitor_gitingest_progress(session_id, gitingest_manager, gitingest_session_id)
            
        except Exception as e:
            logger.error(f"Error in initialization for session {session_id}: {e}")
            session = self._active_sessions.get(session_id)
            if session:
                session.status = 'error'
                session.error_message = str(e)
                session.completed_at = datetime.now()
                session.message = f"Initialization failed: {str(e)}"
    
    async def _monitor_gitingest_progress(self, session_id: str, gitingest_manager, gitingest_session_id: str):
        """Monitor GitIngest progress and update session status."""
        session = self._active_sessions.get(session_id)
        if not session:
            return
        
        max_wait_time = 300  # 5 minutes
        check_interval = 2   # 2 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                # Check GitIngest status
                gitingest_status = await gitingest_manager.get_status(gitingest_session_id)
                
                if gitingest_status.status == 'completed':
                    session.status = 'ready'
                    session.progress = 1.0
                    session.message = 'Repository ready for chat'
                    session.completed_at = datetime.now()
                    logger.info(f"Initialization completed for session {session_id}")
                    break
                elif gitingest_status.status == 'error':
                    session.status = 'error'
                    session.error_message = gitingest_status.error_message
                    session.completed_at = datetime.now()
                    session.message = f"GitIngest failed: {gitingest_status.error_message}"
                    logger.error(f"GitIngest failed for session {session_id}: {gitingest_status.error_message}")
                    break
                else:
                    # Update progress
                    session.progress = 0.5 + (gitingest_status.progress * 0.5)
                    session.message = f"Processing: {gitingest_status.message}"
                
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
            except Exception as e:
                logger.error(f"Error monitoring GitIngest progress: {e}")
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
        
        # Timeout handling
        if elapsed_time >= max_wait_time and session.status == 'initializing':
            session.status = 'error'
            session.error_message = 'Initialization timeout'
            session.completed_at = datetime.now()
            session.message = 'Initialization timed out'
            logger.warning(f"Initialization timeout for session {session_id}")
    
    async def _fallback_initialization(self, session_id: str, nav_event: NavigationEvent):
        """Fallback initialization using existing services."""
        session = self._active_sessions.get(session_id)
        if not session:
            return
        
        try:
            # Use existing repository services as fallback
            session.progress = 0.5
            session.message = "Using fallback initialization..."
            
            # Try to use existing Redis repo manager
            try:
                from services.redis_repo_manager import RedisRepoManager
                repo_manager = RedisRepoManager()
                
                # Initialize repository cache
                cache_key = await repo_manager.initialize_repository_cache(
                    nav_event.repository_url,
                    nav_event.user_id
                )
                
                session.progress = 1.0
                session.status = 'ready'
                session.message = 'Repository ready for chat (fallback mode)'
                session.completed_at = datetime.now()
                
                logger.info(f"Fallback initialization completed for session {session_id}")
                
            except Exception as e:
                logger.error(f"Fallback initialization failed: {e}")
                session.status = 'error'
                session.error_message = f"Fallback initialization failed: {str(e)}"
                session.completed_at = datetime.now()
                session.message = f"Initialization failed: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in fallback initialization: {e}")
            session.status = 'error'
            session.error_message = str(e)
            session.completed_at = datetime.now()
            session.message = f"Initialization failed: {str(e)}"
    
    async def get_initialization_status(self, session_id: str) -> Optional[InitializationStatus]:
        """Get the status of an initialization session."""
        return self._active_sessions.get(session_id)
    
    async def cancel_initialization(self, session_id: str) -> bool:
        """Cancel an ongoing initialization."""
        session = self._active_sessions.get(session_id)
        if not session:
            return False
        
        if session.status == 'initializing':
            session.status = 'cancelled'
            session.completed_at = datetime.now()
            session.message = 'Initialization cancelled by user'
            
            # Try to cancel GitIngest if available
            if session.gitingest_session_id:
                try:
                    from services.gitingest_manager import GitIngestManager
                    gitingest_manager = GitIngestManager()
                    await gitingest_manager.cancel_processing(session.gitingest_session_id)
                except Exception as e:
                    logger.warning(f"Could not cancel GitIngest session: {e}")
            
            logger.info(f"Cancelled initialization session {session_id}")
            return True
        
        return False
    
    def get_user_sessions(self, user_id: str) -> List[InitializationStatus]:
        """Get all initialization sessions for a user."""
        user_session_ids = self._user_sessions.get(user_id, [])
        return [
            self._active_sessions[session_id] 
            for session_id in user_session_ids 
            if session_id in self._active_sessions
        ]
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up expired sessions."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_sessions = []
        
        for session_id, session in self._active_sessions.items():
            if session.started_at < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            session = self._active_sessions.pop(session_id, None)
            if session:
                # Remove from user sessions
                user_sessions = self._user_sessions.get(session.user_id, [])
                if session_id in user_sessions:
                    user_sessions.remove(session_id)
                
                logger.info(f"Cleaned up expired session {session_id}")
        
        return len(expired_sessions)

# Global service instance
_auto_init_service: Optional[AutoInitService] = None

def get_auto_init_service() -> AutoInitService:
    """Get the global auto-initialization service instance."""
    global _auto_init_service
    if _auto_init_service is None:
        _auto_init_service = AutoInitService()
    return _auto_init_service