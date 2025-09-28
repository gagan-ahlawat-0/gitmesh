"""
Intelligent File Suggestions API Routes

API endpoints for intelligent file suggestion and auto-addition functionality.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from pydantic import BaseModel

from services.intelligent_file_suggester import (
    get_file_suggester,
    QueryContext,
    SuggestedFile
)
from .dependencies import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/intelligent-suggestions", tags=["intelligent-suggestions"])


class FileSuggestionRequest(BaseModel):
    """Request model for file suggestions."""
    user_query: str
    repository_name: str
    branch: str = "main"
    session_id: str
    conversation_history: List[str] = []
    current_files: List[str] = []
    max_suggestions: int = 10
    auto_add_threshold: float = 0.8


class FileSuggestionResponse(BaseModel):
    """Response model for file suggestions."""
    success: bool
    suggestions: List[Dict[str, Any]]
    auto_added_files: List[str]
    total_suggestions: int
    processing_time_ms: float
    message: str


class SuggestionFeedbackRequest(BaseModel):
    """Request model for suggestion feedback."""
    file_path: str
    accepted: bool
    relevance_score: float
    session_id: str


class SuggestionStatsResponse(BaseModel):
    """Response model for suggestion statistics."""
    total_suggestions: int
    auto_added_files: int
    user_accepted_suggestions: int
    last_suggestion_time: Optional[str]
    most_suggested_file_types: Dict[str, int]
    average_relevance_score: float


@router.post("/suggest", response_model=FileSuggestionResponse)
async def get_file_suggestions(
    request: FileSuggestionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> FileSuggestionResponse:
    """
    Get intelligent file suggestions based on user query and context.
    
    This endpoint analyzes the user's query and conversation history to suggest
    relevant files from the repository that should be added to the chat context.
    """
    start_time = datetime.now()
    
    try:
        user_id = current_user.get("user_id") or current_user.get("id")
        username = current_user.get("username") or current_user.get("login")
        
        logger.info(
            f"Processing file suggestion request for user {username}",
            query=request.user_query[:100],
            repository=request.repository_name,
            current_files_count=len(request.current_files)
        )
        
        # Get file suggester instance
        suggester = get_file_suggester(user_id)
        
        # Create query context
        query_context = QueryContext(
            user_query=request.user_query,
            conversation_history=request.conversation_history,
            current_files=set(request.current_files),
            repository_name=request.repository_name,
            branch=request.branch,
            user_id=user_id,
            session_id=request.session_id
        )
        
        # Get file suggestions
        suggestions = await suggester.suggest_files(
            query_context=query_context,
            max_suggestions=request.max_suggestions,
            auto_add_threshold=request.auto_add_threshold
        )
        
        # Auto-add high-relevance files in background
        auto_added_files = []
        if suggestions:
            background_tasks.add_task(
                _auto_add_files_background,
                suggester,
                suggestions,
                query_context
            )
            
            # Get list of files that will be auto-added
            auto_added_files = [
                s.path for s in suggestions 
                if s.auto_add
            ]
        
        # Convert suggestions to response format
        suggestion_dicts = []
        for suggestion in suggestions:
            suggestion_dicts.append({
                "path": suggestion.path,
                "branch": suggestion.branch,
                "relevance_score": suggestion.relevance_score,
                "reason": suggestion.reason,
                "file_type": suggestion.file_type,
                "size_bytes": suggestion.size_bytes,
                "content_preview": suggestion.content_preview,
                "auto_add": suggestion.auto_add,
                "last_modified": suggestion.last_modified.isoformat() if suggestion.last_modified else None
            })
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return FileSuggestionResponse(
            success=True,
            suggestions=suggestion_dicts,
            auto_added_files=auto_added_files,
            total_suggestions=len(suggestions),
            processing_time_ms=processing_time,
            message=f"Found {len(suggestions)} relevant files, {len(auto_added_files)} will be auto-added"
        )
        
    except Exception as e:
        logger.error(f"Error processing file suggestions: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return FileSuggestionResponse(
            success=False,
            suggestions=[],
            auto_added_files=[],
            total_suggestions=0,
            processing_time_ms=processing_time,
            message=f"Failed to generate suggestions: {str(e)}"
        )


@router.post("/feedback")
async def submit_suggestion_feedback(
    request: SuggestionFeedbackRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Submit feedback on file suggestion quality.
    
    This helps improve future suggestions by learning from user preferences.
    """
    try:
        user_id = current_user.get("user_id") or current_user.get("id")
        
        # Get file suggester instance
        suggester = get_file_suggester(user_id)
        
        # Update feedback
        await suggester.update_suggestion_feedback(
            file_path=request.file_path,
            accepted=request.accepted,
            relevance_score=request.relevance_score
        )
        
        logger.info(
            f"Suggestion feedback submitted",
            file_path=request.file_path,
            accepted=request.accepted,
            score=request.relevance_score
        )
        
        return {
            "success": True,
            "message": "Feedback submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error submitting suggestion feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/stats", response_model=SuggestionStatsResponse)
async def get_suggestion_stats(
    current_user: dict = Depends(get_current_user)
) -> SuggestionStatsResponse:
    """
    Get user's file suggestion statistics.
    
    Returns information about suggestion usage and effectiveness.
    """
    try:
        user_id = current_user.get("user_id") or current_user.get("id")
        
        # Get file suggester instance
        suggester = get_file_suggester(user_id)
        
        # Get statistics
        stats = await suggester.get_suggestion_stats()
        
        return SuggestionStatsResponse(
            total_suggestions=stats.get('total_suggestions', 0),
            auto_added_files=stats.get('auto_added_files', 0),
            user_accepted_suggestions=stats.get('user_accepted_suggestions', 0),
            last_suggestion_time=stats.get('last_suggestion_time'),
            most_suggested_file_types=stats.get('most_suggested_file_types', {}),
            average_relevance_score=stats.get('average_relevance_score', 0.0)
        )
        
    except Exception as e:
        logger.error(f"Error getting suggestion stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestion stats: {str(e)}"
        )


@router.post("/manual-suggest")
async def manual_file_suggestion(
    repository_name: str,
    branch: str = "main",
    file_pattern: str = "",
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Manually trigger file suggestions based on repository structure.
    
    Useful for exploring repository contents without a specific query.
    """
    try:
        user_id = current_user.get("user_id") or current_user.get("id")
        
        # Get file suggester instance
        suggester = get_file_suggester(user_id)
        
        # Create a generic query context for exploration
        query_context = QueryContext(
            user_query=f"explore {file_pattern}" if file_pattern else "explore repository",
            conversation_history=[],
            current_files=set(),
            repository_name=repository_name,
            branch=branch,
            user_id=user_id,
            session_id=f"manual-{datetime.now().timestamp()}"
        )
        
        # Get suggestions
        suggestions = await suggester.suggest_files(
            query_context=query_context,
            max_suggestions=20,
            auto_add_threshold=0.9  # Higher threshold for manual exploration
        )
        
        # Group suggestions by file type
        suggestions_by_type = {}
        for suggestion in suggestions:
            file_type = suggestion.file_type
            if file_type not in suggestions_by_type:
                suggestions_by_type[file_type] = []
            
            suggestions_by_type[file_type].append({
                "path": suggestion.path,
                "relevance_score": suggestion.relevance_score,
                "reason": suggestion.reason,
                "size_bytes": suggestion.size_bytes
            })
        
        return {
            "success": True,
            "repository_name": repository_name,
            "branch": branch,
            "total_files": len(suggestions),
            "suggestions_by_type": suggestions_by_type,
            "message": f"Found {len(suggestions)} files for exploration"
        }
        
    except Exception as e:
        logger.error(f"Error in manual file suggestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get manual suggestions: {str(e)}"
        )


async def _auto_add_files_background(
    suggester,
    suggestions: List[SuggestedFile],
    query_context: QueryContext
):
    """Background task to auto-add high-relevance files."""
    try:
        added_files = await suggester.auto_add_files(suggestions, query_context)
        
        if added_files:
            logger.info(
                f"Auto-added {len(added_files)} files to context",
                files=added_files,
                session_id=query_context.session_id
            )
        
    except Exception as e:
        logger.error(f"Error in background auto-add: {e}")


@router.get("/health")
async def get_suggestion_service_health() -> Dict[str, Any]:
    """
    Get health status of the intelligent suggestion service.
    """
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "service": "intelligent_file_suggester",
            "status": "healthy",
            "features": {
                "semantic_analysis": True,
                "auto_addition": True,
                "feedback_learning": True,
                "repository_analysis": True
            },
            "message": "Intelligent file suggestion service is operational"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "service": "intelligent_file_suggester",
            "status": "error",
            "message": f"Service health check failed: {str(e)}"
        }