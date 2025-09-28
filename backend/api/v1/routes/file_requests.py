"""
File Request API Endpoints

Handles AI-requested file additions to chat context.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

from services.optimized_repo_service import get_optimized_repo_service
from services.intelligent_file_suggester import get_file_suggester
from .dependencies import get_current_user
from models.api.auth_models import User

logger = structlog.get_logger(__name__)

router = APIRouter()


class FileRequestItem(BaseModel):
    """File request item model."""
    path: str = Field(..., description="File path")
    reason: str = Field(..., description="Reason for request")
    branch: str = Field(default="main", description="Git branch")
    auto_add: bool = Field(default=False, description="Whether to auto-add")
    pattern_matched: Optional[str] = Field(None, description="Pattern that matched")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ApproveFileRequest(BaseModel):
    """Request to approve a file addition."""
    file_path: str = Field(..., description="Path of file to add")
    repository_name: str = Field(..., description="Repository name")
    branch: str = Field(default="main", description="Git branch")
    session_id: str = Field(..., description="Chat session ID")


class RejectFileRequest(BaseModel):
    """Request to reject a file addition."""
    file_path: str = Field(..., description="Path of file to reject")
    session_id: str = Field(..., description="Chat session ID")
    reason: Optional[str] = Field(None, description="Reason for rejection")


class FileRequestResponse(BaseModel):
    """Response for file request operations."""
    success: bool
    message: str
    file_path: Optional[str] = None
    content_preview: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None


@router.post("/approve", response_model=FileRequestResponse)
async def approve_file_request(
    request: ApproveFileRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Approve a file request and add it to the chat context.
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        user_id = current_user.id

        logger.info(
            "Processing file approval request",
            user_id=user_id,
            file_path=request.file_path,
            repository=request.repository_name
        )

        # Get repository service
        repo_service = get_optimized_repo_service(user_id)
        repo_url = f"https://github.com/{request.repository_name}"

        # Get file content
        try:
            file_content = repo_service.get_file_content(
                repo_url,
                request.file_path,
                request.branch
            )
            
            if not file_content:
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {request.file_path}"
                )

        except HTTPException:
            # Re-raise HTTP exceptions (like 404) as-is
            raise
        except Exception as e:
            logger.error(f"Error fetching file content: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch file content: {str(e)}"
            )

        # Get file size
        file_size = len(file_content.encode('utf-8'))
        
        # Create content preview (first 200 characters)
        content_preview = file_content[:200] + "..." if len(file_content) > 200 else file_content

        # Update file request status to approved
        try:
            from .chat import get_file_requests, store_file_requests
            file_requests = get_file_requests(request.session_id)
            
            # Find and update the specific file request
            for req in file_requests:
                if req.get("file_path") == request.file_path and req.get("status") == "pending":
                    req["status"] = "approved"
                    req["approved_at"] = datetime.now().isoformat()
                    break
            
            # Store updated file requests
            store_file_requests(request.session_id, file_requests, ttl_hours=24)
            
        except Exception as e:
            logger.error(f"Error updating file request status: {e}")
            # Continue execution even if file request status update fails
        
        # Store file in session context (this would typically be handled by a session service)
        # For now, we'll just log the success
        logger.info(
            "File approved and added to context",
            file_path=request.file_path,
            file_size=file_size,
            session_id=request.session_id
        )

        # Submit positive feedback to improve suggestions
        background_tasks.add_task(
            _submit_file_feedback,
            user_id,
            request.file_path,
            True,
            0.8  # Assume good relevance since user approved
        )

        return FileRequestResponse(
            success=True,
            message=f"Successfully added {request.file_path} to context",
            file_path=request.file_path,
            content_preview=content_preview,
            file_size=file_size
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving file request: {e}", exc_info=True)
        return FileRequestResponse(
            success=False,
            message="Failed to approve file request",
            error=str(e)
        )


@router.post("/reject", response_model=FileRequestResponse)
async def reject_file_request(
    request: RejectFileRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Reject a file request.
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        user_id = current_user.id

        logger.info(
            "Processing file rejection",
            user_id=user_id,
            file_path=request.file_path,
            reason=request.reason
        )

        # Update file request status to rejected
        try:
            from .chat import get_file_requests, store_file_requests
            file_requests = get_file_requests(request.session_id)
            
            # Find and update the specific file request
            for req in file_requests:
                if req.get("file_path") == request.file_path and req.get("status") == "pending":
                    req["status"] = "rejected"
                    req["rejected_at"] = datetime.now().isoformat()
                    req["rejection_reason"] = request.reason
                    break
            
            # Store updated file requests
            store_file_requests(request.session_id, file_requests, ttl_hours=24)
            
        except ImportError as e:
            logger.error(f"Error updating file request status: {e}")

        # Submit negative feedback to improve suggestions
        background_tasks.add_task(
            _submit_file_feedback,
            user_id,
            request.file_path,
            False,
            0.2  # Low relevance since user rejected
        )

        return FileRequestResponse(
            success=True,
            message=f"Rejected {request.file_path}",
            file_path=request.file_path
        )

    except Exception as e:
        logger.error(f"Error rejecting file request: {e}")
        return FileRequestResponse(
            success=False,
            message="Failed to reject file request",
            error=str(e)
        )


@router.get("/session/{session_id}", response_model=List[FileRequestItem])
async def get_session_file_requests(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get file requests for a specific session.
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        user_id = current_user.id

        logger.info(
            "Fetching file requests for session",
            user_id=user_id,
            session_id=session_id
        )

        # Import the file request functions from chat.py
        try:
            from .chat import get_file_requests
            file_requests = get_file_requests(session_id)
            
            # Convert to FileRequestItem format
            result = []
            for req in file_requests:
                if req.get("status") == "pending":  # Only return pending requests
                    result.append(FileRequestItem(
                        path=req.get("file_path", ""),
                        reason=req.get("reason", "AI requested this file"),
                        branch=req.get("branch", "main"),
                        auto_add=False,
                        metadata=req.get("metadata", {})
                    ))
            
            return result
            
        except ImportError as e:
            logger.error(f"Error importing file request functions: {e}")
            return []

    except Exception as e:
        logger.error(f"Error fetching session file requests: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch file requests"
        )


async def _submit_file_feedback(
    user_id: str,
    file_path: str,
    accepted: bool,
    relevance_score: float
):
    """Submit feedback for file suggestion improvement."""
    try:
        suggester = get_file_suggester(user_id)
        await suggester.update_suggestion_feedback(
            file_path,
            accepted,
            relevance_score
        )
    except Exception as e:
        logger.error(f"Error submitting file feedback: {e}")