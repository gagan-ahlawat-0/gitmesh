"""
Auto-initialization API routes.
Handles page navigation detection and automatic repository initialization.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

from .dependencies import get_current_user
from models.api.auth_models import User

logger = structlog.get_logger(__name__)
router = APIRouter()

# Request/Response models
class PageVisitRequest(BaseModel):
    page_url: str
    from_page: Optional[str] = None
    user_id: Optional[str] = None

class InitializationStatusResponse(BaseModel):
    session_id: str
    repository_url: str
    user_id: str
    status: str
    progress: float
    message: str
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

class CancelInitializationRequest(BaseModel):
    session_id: str

# Import services with fallback
try:
    from services.auto_init_service import get_auto_init_service
    AUTO_INIT_AVAILABLE = True
except ImportError:
    AUTO_INIT_AVAILABLE = False
    get_auto_init_service = None

try:
    from services.gitingest_manager import get_gitingest_manager
    GITINGEST_AVAILABLE = True
except ImportError:
    GITINGEST_AVAILABLE = False
    get_gitingest_manager = None

try:
    from services.preloading_service import get_preloading_service
    PRELOADING_AVAILABLE = True
except ImportError:
    PRELOADING_AVAILABLE = False
    get_preloading_service = None

@router.post("/page-visit")
async def handle_page_visit(
    request: PageVisitRequest,
    current_user: User = Depends(get_current_user)
):
    """Handle page visit and trigger auto-initialization if needed."""
    try:
        user_id = request.user_id or current_user.id
        
        logger.info(f"Page visit: {request.page_url} from {request.from_page} for user {user_id}")
        
        if not AUTO_INIT_AVAILABLE:
            return JSONResponse(content={
                "session_id": None,
                "auto_init_triggered": False,
                "message": "Auto-initialization service not available",
                "success": False
            })
        
        # Get auto-init service
        auto_init_service = get_auto_init_service()
        
        # Handle page visit
        session_id = await auto_init_service.on_page_visit(
            user_id=user_id,
            page_url=request.page_url,
            from_page=request.from_page
        )
        
        if session_id:
            # Get initial status
            status = await auto_init_service.get_initialization_status(session_id)
            
            return JSONResponse(content={
                "session_id": session_id,
                "auto_init_triggered": True,
                "status": {
                    "session_id": status.session_id,
                    "repository_url": status.repository_url,
                    "status": status.status,
                    "progress": status.progress,
                    "message": status.message,
                    "started_at": status.started_at.isoformat()
                } if status else None,
                "message": "Auto-initialization started",
                "success": True
            })
        else:
            return JSONResponse(content={
                "session_id": None,
                "auto_init_triggered": False,
                "message": "No auto-initialization needed for this page",
                "success": True
            })
            
    except Exception as e:
        logger.error(f"Error handling page visit: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "session_id": None,
                "auto_init_triggered": False,
                "message": f"Error handling page visit: {str(e)}",
                "success": False
            }
        )

@router.get("/status/{session_id}")
async def get_initialization_status(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of an initialization session."""
    try:
        if not AUTO_INIT_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Auto-initialization service not available",
                    "success": False
                }
            )
        
        # Get auto-init service
        auto_init_service = get_auto_init_service()
        
        # Get status
        status = await auto_init_service.get_initialization_status(session_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Initialization session not found")
        
        # Check if user has access to this session
        if status.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return JSONResponse(content={
            "status": {
                "session_id": status.session_id,
                "repository_url": status.repository_url,
                "user_id": status.user_id,
                "status": status.status,
                "progress": status.progress,
                "message": status.message,
                "started_at": status.started_at.isoformat(),
                "completed_at": status.completed_at.isoformat() if status.completed_at else None,
                "error_message": status.error_message,
                "gitingest_session_id": status.gitingest_session_id
            },
            "success": True
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting initialization status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error getting status: {str(e)}",
                "success": False
            }
        )

@router.post("/cancel")
async def cancel_initialization(
    request: CancelInitializationRequest,
    current_user: User = Depends(get_current_user)
):
    """Cancel an ongoing initialization."""
    try:
        if not AUTO_INIT_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "cancelled": False,
                    "error": "Auto-initialization service not available",
                    "success": False
                }
            )
        
        # Get auto-init service
        auto_init_service = get_auto_init_service()
        
        # Get status to check user access
        status = await auto_init_service.get_initialization_status(request.session_id)
        if not status:
            raise HTTPException(status_code=404, detail="Initialization session not found")
        
        if status.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Cancel initialization
        cancelled = await auto_init_service.cancel_initialization(request.session_id)
        
        return JSONResponse(content={
            "cancelled": cancelled,
            "message": "Initialization cancelled" if cancelled else "Could not cancel initialization",
            "success": cancelled
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling initialization: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "cancelled": False,
                "error": f"Error cancelling initialization: {str(e)}",
                "success": False
            }
        )

@router.get("/user-sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user)
):
    """Get all initialization sessions for the current user."""
    try:
        if not AUTO_INIT_AVAILABLE:
            return JSONResponse(content={
                "sessions": [],
                "message": "Auto-initialization service not available",
                "success": False
            })
        
        # Get auto-init service
        auto_init_service = get_auto_init_service()
        
        # Get user sessions
        sessions = auto_init_service.get_user_sessions(current_user.id)
        
        # Convert to response format
        session_data = []
        for session in sessions:
            session_data.append({
                "session_id": session.session_id,
                "repository_url": session.repository_url,
                "status": session.status,
                "progress": session.progress,
                "message": session.message,
                "started_at": session.started_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "error_message": session.error_message
            })
        
        return JSONResponse(content={
            "sessions": session_data,
            "count": len(session_data),
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "sessions": [],
                "error": f"Error getting user sessions: {str(e)}",
                "success": False
            }
        )

@router.get("/gitingest-status/{session_id}")
async def get_gitingest_status(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get GitIngest status for a session."""
    try:
        if not GITINGEST_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "GitIngest service not available",
                    "success": False
                }
            )
        
        # Get GitIngest manager
        gitingest_manager = get_gitingest_manager()
        
        # Get status
        status = await gitingest_manager.get_status(session_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="GitIngest session not found")
        
        # Check user access
        if status.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return JSONResponse(content={
            "status": {
                "session_id": status.session_id,
                "repository_url": status.repository_url,
                "user_id": status.user_id,
                "branch": status.branch,
                "status": status.status,
                "progress": status.progress,
                "message": status.message,
                "started_at": status.started_at.isoformat(),
                "completed_at": status.completed_at.isoformat() if status.completed_at else None,
                "error_message": status.error_message,
                "file_count": status.file_count,
                "processed_files": status.processed_files,
                "cache_key": status.cache_key
            },
            "success": True
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GitIngest status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error getting GitIngest status: {str(e)}",
                "success": False
            }
        )

@router.get("/preloading-queue")
async def get_preloading_queue_status(
    current_user: User = Depends(get_current_user)
):
    """Get preloading queue status."""
    try:
        if not PRELOADING_AVAILABLE:
            return JSONResponse(content={
                "queue_status": {
                    "queue_size": 0,
                    "active_tasks": 0,
                    "is_running": False,
                    "error": "Preloading service not available"
                },
                "user_tasks": [],
                "success": False
            })
        
        # Get preloading service
        preloading_service = await get_preloading_service()
        
        # Get queue status
        queue_status = preloading_service.get_queue_status()
        
        # Get user tasks
        user_tasks = preloading_service.get_user_tasks(current_user.id)
        
        # Convert tasks to response format
        task_data = []
        for task in user_tasks:
            task_data.append({
                "task_id": task.task_id,
                "repository_url": task.repository_url,
                "branch": task.branch,
                "priority": task.priority,
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error_message": task.error_message,
                "estimated_duration_seconds": task.estimated_duration_seconds,
                "actual_duration_seconds": task.actual_duration_seconds
            })
        
        return JSONResponse(content={
            "queue_status": queue_status,
            "user_tasks": task_data,
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Error getting preloading queue status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "queue_status": {},
                "user_tasks": [],
                "error": f"Error getting queue status: {str(e)}",
                "success": False
            }
        )

@router.get("/health")
async def get_auto_init_health():
    """Get auto-initialization service health status."""
    try:
        health_status = {
            "auto_init_service": AUTO_INIT_AVAILABLE,
            "gitingest_manager": GITINGEST_AVAILABLE,
            "preloading_service": PRELOADING_AVAILABLE,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get detailed status if services are available
        if AUTO_INIT_AVAILABLE:
            auto_init_service = get_auto_init_service()
            # Could add service-specific health checks here
        
        if GITINGEST_AVAILABLE:
            gitingest_manager = get_gitingest_manager()
            health_status["gitingest_stats"] = gitingest_manager.get_statistics()
        
        if PRELOADING_AVAILABLE:
            preloading_service = await get_preloading_service()
            health_status["preloading_queue"] = preloading_service.get_queue_status()
        
        overall_healthy = AUTO_INIT_AVAILABLE and GITINGEST_AVAILABLE
        
        return JSONResponse(content={
            "healthy": overall_healthy,
            "services": health_status,
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Error getting auto-init health: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "healthy": False,
                "error": f"Health check failed: {str(e)}",
                "success": False
            }
        )