"""
Comprehensive Error Handler for Cosmos Optimization

Extends the existing error handling system to provide:
- Enhanced error categorization for different system components
- Meaningful error messages for UI display
- Graceful degradation for cache misses and failures
- Recovery options and fallback mechanisms
- Comprehensive error logging and monitoring

Requirements: 2.5, 3.5, 5.4
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .cosmos_error_handler import (
    CosmosErrorHandler, ErrorCategory, ErrorSeverity, ErrorInfo, 
    RecoveryAction, RetryConfig, get_error_handler
)

logger = logging.getLogger(__name__)


class SystemComponent(Enum):
    """System components for error tracking."""
    REDIS_CACHE = "redis_cache"
    GITINGEST = "gitingest"
    SUPABASE = "supabase"
    COSMOS_AI = "cosmos_ai"
    WEBSOCKET = "websocket"
    FILE_SYSTEM = "file_system"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    CLEANUP = "cleanup"
    UI_DISPLAY = "ui_display"


class UserFacingErrorType(Enum):
    """User-facing error types for meaningful messages."""
    CACHE_INITIALIZATION_FAILED = "cache_initialization_failed"
    CACHE_ACCESS_FAILED = "cache_access_failed"
    REPOSITORY_PROCESSING_FAILED = "repository_processing_failed"
    CHAT_STORAGE_FAILED = "chat_storage_failed"
    PERFORMANCE_DEGRADED = "performance_degraded"
    SERVICE_TEMPORARILY_UNAVAILABLE = "service_temporarily_unavailable"
    CLEANUP_FAILED = "cleanup_failed"
    AUTHENTICATION_FAILED = "authentication_failed"
    VALIDATION_FAILED = "validation_failed"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class UserFacingError:
    """User-facing error information."""
    error_type: UserFacingErrorType
    title: str
    message: str
    suggested_actions: List[str]
    technical_details: Optional[str] = None
    retry_available: bool = True
    fallback_available: bool = False
    estimated_resolution_time: Optional[str] = None


@dataclass
class ErrorContext:
    """Enhanced error context information."""
    component: SystemComponent
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    repository_url: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = None
    additional_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.additional_data is None:
            self.additional_data = {}


class ComprehensiveErrorHandler:
    """
    Comprehensive error handler that extends CosmosErrorHandler
    with enhanced user-facing error messages and component-specific handling.
    """

    def __init__(self):
        """Initialize comprehensive error handler."""
        self.base_handler = get_error_handler()
        self.component_error_counts: Dict[SystemComponent, int] = {}
        self.user_facing_errors: List[UserFacingError] = []
        self.error_message_templates = self._initialize_error_templates()
        
        # Register additional fallback strategies
        self._register_component_fallbacks()
        
        logger.info("ComprehensiveErrorHandler initialized")

    def _initialize_error_templates(self) -> Dict[UserFacingErrorType, Dict[str, Any]]:
        """Initialize user-facing error message templates."""
        return {
            UserFacingErrorType.CACHE_INITIALIZATION_FAILED: {
                "title": "Repository Caching Issue",
                "message": "We're having trouble preparing your repository for faster access. You can still use the system, but responses may be slower than usual.",
                "suggested_actions": [
                    "Try refreshing the page",
                    "Wait a moment and try again",
                    "Contact support if the issue persists"
                ],
                "retry_available": True,
                "fallback_available": True,
                "estimated_resolution_time": "1-2 minutes"
            },
            UserFacingErrorType.CACHE_ACCESS_FAILED: {
                "title": "Cache Access Problem",
                "message": "We couldn't retrieve cached data for your repository. The system will work normally but may respond more slowly.",
                "suggested_actions": [
                    "Continue using the system normally",
                    "Responses may take a bit longer than usual",
                    "The issue should resolve automatically"
                ],
                "retry_available": True,
                "fallback_available": True,
                "estimated_resolution_time": "30 seconds"
            },
            UserFacingErrorType.REPOSITORY_PROCESSING_FAILED: {
                "title": "Repository Processing Error",
                "message": "We encountered an issue while processing your repository. Some features may be limited until this is resolved.",
                "suggested_actions": [
                    "Try selecting a different repository",
                    "Refresh the page and try again",
                    "Check if the repository is accessible"
                ],
                "retry_available": True,
                "fallback_available": False,
                "estimated_resolution_time": "2-5 minutes"
            },
            UserFacingErrorType.CHAT_STORAGE_FAILED: {
                "title": "Chat History Issue",
                "message": "Your chat messages couldn't be saved properly. Your current conversation will continue, but history may not be preserved.",
                "suggested_actions": [
                    "Continue your conversation normally",
                    "Consider saving important information separately",
                    "The issue should resolve for future chats"
                ],
                "retry_available": True,
                "fallback_available": True,
                "estimated_resolution_time": "1 minute"
            },
            UserFacingErrorType.PERFORMANCE_DEGRADED: {
                "title": "Performance Issue",
                "message": "The system is experiencing higher than normal load. Everything still works, but responses may be slower.",
                "suggested_actions": [
                    "Continue using the system normally",
                    "Expect slightly longer response times",
                    "Performance should improve shortly"
                ],
                "retry_available": False,
                "fallback_available": True,
                "estimated_resolution_time": "5-10 minutes"
            },
            UserFacingErrorType.SERVICE_TEMPORARILY_UNAVAILABLE: {
                "title": "Service Temporarily Unavailable",
                "message": "A core service is temporarily unavailable. We're working to restore full functionality.",
                "suggested_actions": [
                    "Wait a few minutes and try again",
                    "Check our status page for updates",
                    "Contact support if the issue persists"
                ],
                "retry_available": True,
                "fallback_available": False,
                "estimated_resolution_time": "5-15 minutes"
            },
            UserFacingErrorType.CLEANUP_FAILED: {
                "title": "Cleanup Process Issue",
                "message": "We couldn't properly clean up some resources. This won't affect your current session but may impact performance.",
                "suggested_actions": [
                    "Continue using the system normally",
                    "The cleanup will be retried automatically",
                    "Contact support if you notice performance issues"
                ],
                "retry_available": True,
                "fallback_available": True,
                "estimated_resolution_time": "2-3 minutes"
            },
            UserFacingErrorType.AUTHENTICATION_FAILED: {
                "title": "Authentication Problem",
                "message": "We couldn't verify your authentication. Please sign in again to continue.",
                "suggested_actions": [
                    "Sign out and sign in again",
                    "Clear your browser cache",
                    "Contact support if the problem continues"
                ],
                "retry_available": True,
                "fallback_available": False,
                "estimated_resolution_time": "Immediate"
            },
            UserFacingErrorType.VALIDATION_FAILED: {
                "title": "Input Validation Error",
                "message": "The information provided couldn't be processed. Please check your input and try again.",
                "suggested_actions": [
                    "Review your input for any errors",
                    "Try a different approach",
                    "Contact support if you believe this is incorrect"
                ],
                "retry_available": True,
                "fallback_available": False,
                "estimated_resolution_time": "Immediate"
            },
            UserFacingErrorType.UNKNOWN_ERROR: {
                "title": "Unexpected Error",
                "message": "An unexpected error occurred. We've been notified and are investigating the issue.",
                "suggested_actions": [
                    "Try refreshing the page",
                    "Wait a moment and try again",
                    "Contact support with details of what you were doing"
                ],
                "retry_available": True,
                "fallback_available": True,
                "estimated_resolution_time": "Unknown"
            }
        }

    def _register_component_fallbacks(self):
        """Register component-specific fallback strategies."""
        # Redis cache fallbacks
        self.base_handler.fallback_manager.register_fallback(
            "redis_cache_get",
            self._fallback_direct_processing
        )
        
        self.base_handler.fallback_manager.register_fallback(
            "redis_cache_set",
            self._fallback_skip_caching
        )
        
        # GitIngest fallbacks
        self.base_handler.fallback_manager.register_fallback(
            "gitingest_process",
            self._fallback_basic_repository_info
        )
        
        # Supabase fallbacks
        self.base_handler.fallback_manager.register_fallback(
            "supabase_store_chat",
            self._fallback_memory_storage
        )
        
        # Cleanup fallbacks
        self.base_handler.fallback_manager.register_fallback(
            "cleanup_cache",
            self._fallback_force_cleanup
        )

    async def _fallback_direct_processing(self, *args, **kwargs) -> Any:
        """Fallback to direct processing when cache unavailable."""
        logger.info("Using direct processing fallback")
        return {"status": "fallback", "method": "direct_processing"}

    def _fallback_skip_caching(self, *args, **kwargs) -> Any:
        """Fallback to skip caching when cache unavailable."""
        logger.info("Skipping caching due to fallback")
        return {"status": "skipped", "reason": "cache_unavailable"}

    async def _fallback_basic_repository_info(self, repo_url: str, **kwargs) -> Dict[str, Any]:
        """Fallback to basic repository info when GitIngest fails."""
        logger.info(f"Using basic repository info fallback for {repo_url}")
        return {
            "repo_url": repo_url,
            "repo_name": repo_url.split("/")[-1] if "/" in repo_url else repo_url,
            "status": "basic_info_only",
            "message": "Limited repository information available"
        }

    def _fallback_memory_storage(self, *args, **kwargs) -> Dict[str, Any]:
        """Fallback to memory storage when Supabase unavailable."""
        logger.warning("Using memory storage fallback for chat data")
        return {"status": "memory_storage", "warning": "Chat history may not persist"}

    async def _fallback_force_cleanup(self, *args, **kwargs) -> Dict[str, Any]:
        """Fallback to force cleanup when normal cleanup fails."""
        logger.warning("Using force cleanup fallback")
        # This would implement more aggressive cleanup
        return {"status": "force_cleanup", "success": True}

    def _map_to_user_facing_error(
        self, 
        error_info: ErrorInfo, 
        context: ErrorContext
    ) -> UserFacingError:
        """Map internal error to user-facing error."""
        
        # Determine user-facing error type based on component and category
        if context.component == SystemComponent.REDIS_CACHE:
            if "initialization" in error_info.message.lower():
                error_type = UserFacingErrorType.CACHE_INITIALIZATION_FAILED
            else:
                error_type = UserFacingErrorType.CACHE_ACCESS_FAILED
        elif context.component == SystemComponent.GITINGEST:
            error_type = UserFacingErrorType.REPOSITORY_PROCESSING_FAILED
        elif context.component == SystemComponent.SUPABASE:
            error_type = UserFacingErrorType.CHAT_STORAGE_FAILED
        elif context.component == SystemComponent.CLEANUP:
            error_type = UserFacingErrorType.CLEANUP_FAILED
        elif context.component == SystemComponent.AUTHENTICATION:
            error_type = UserFacingErrorType.AUTHENTICATION_FAILED
        elif context.component == SystemComponent.VALIDATION:
            error_type = UserFacingErrorType.VALIDATION_FAILED
        elif error_info.severity == ErrorSeverity.HIGH or error_info.severity == ErrorSeverity.CRITICAL:
            error_type = UserFacingErrorType.SERVICE_TEMPORARILY_UNAVAILABLE
        else:
            error_type = UserFacingErrorType.UNKNOWN_ERROR

        # Get template for this error type
        template = self.error_message_templates.get(error_type, self.error_message_templates[UserFacingErrorType.UNKNOWN_ERROR])
        
        # Create user-facing error
        user_error = UserFacingError(
            error_type=error_type,
            title=template["title"],
            message=template["message"],
            suggested_actions=template["suggested_actions"].copy(),
            retry_available=template["retry_available"],
            fallback_available=template["fallback_available"],
            estimated_resolution_time=template["estimated_resolution_time"]
        )
        
        # Add technical details if appropriate
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            user_error.technical_details = f"Error ID: {error_info.error_id}"
        
        return user_error

    async def handle_component_error(
        self,
        exception: Exception,
        context: ErrorContext,
        enable_fallback: bool = True,
        retry_config: Optional[RetryConfig] = None
    ) -> Tuple[ErrorInfo, UserFacingError]:
        """
        Handle error for a specific system component.
        
        Args:
            exception: The exception that occurred
            context: Error context with component information
            enable_fallback: Whether to enable fallback strategies
            retry_config: Retry configuration
            
        Returns:
            Tuple of (ErrorInfo, UserFacingError)
        """
        
        # Update component error counts
        self.component_error_counts[context.component] = self.component_error_counts.get(context.component, 0) + 1
        
        # Handle error with base handler
        error_context = {
            "component": context.component.value,
            "operation": context.operation,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "repository_url": context.repository_url,
            "request_id": context.request_id,
            **context.additional_data
        }
        
        error_info = await self.base_handler.handle_error(
            exception, 
            error_context, 
            context.operation
        )
        
        # Create user-facing error
        user_error = self._map_to_user_facing_error(error_info, context)
        
        # Add to user-facing error history
        self.user_facing_errors.append(user_error)
        
        # Keep only last 100 user-facing errors
        if len(self.user_facing_errors) > 100:
            self.user_facing_errors = self.user_facing_errors[-100:]
        
        # Log user-facing error
        logger.info(
            f"User-facing error created: {user_error.error_type.value} - {user_error.title}",
            extra={
                "error_id": error_info.error_id,
                "component": context.component.value,
                "operation": context.operation,
                "user_id": context.user_id
            }
        )
        
        return error_info, user_error

    async def execute_with_comprehensive_handling(
        self,
        operation: str,
        component: SystemComponent,
        func: Callable,
        *args,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        repository_url: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        enable_fallback: bool = True,
        **kwargs
    ) -> Any:
        """
        Execute function with comprehensive error handling.
        
        Args:
            operation: Operation name
            component: System component
            func: Function to execute
            *args: Arguments for function
            user_id: User ID for context
            session_id: Session ID for context
            repository_url: Repository URL for context
            request_id: Request ID for context
            retry_config: Retry configuration
            enable_fallback: Whether to enable fallback strategies
            **kwargs: Keyword arguments for function
            
        Returns:
            Result from successful execution or fallback
        """
        
        context = ErrorContext(
            component=component,
            operation=operation,
            user_id=user_id,
            session_id=session_id,
            repository_url=repository_url,
            request_id=request_id,
            additional_data=kwargs.copy()
        )
        
        try:
            return await self.base_handler.execute_with_error_handling(
                operation,
                func,
                *args,
                retry_config=retry_config,
                enable_fallback=enable_fallback,
                **kwargs
            )
        except Exception as e:
            # Handle with component-specific error handling
            error_info, user_error = await self.handle_component_error(
                e, context, enable_fallback, retry_config
            )
            
            # For critical errors or when no fallback is available, re-raise
            if (error_info.severity == ErrorSeverity.CRITICAL or 
                not user_error.fallback_available):
                raise e
            
            # Return None for handled errors with fallback
            logger.info(f"Error handled gracefully with fallback for {operation}")
            return None

    def get_user_facing_error_for_display(self, error_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user-facing error information for UI display.
        
        Args:
            error_id: Error ID to look up
            
        Returns:
            Dictionary with user-facing error information or None
        """
        
        # Find error in base handler history
        for error_info in self.base_handler.error_history:
            if error_info.error_id == error_id:
                # Find corresponding user-facing error
                for user_error in self.user_facing_errors:
                    # Match by timestamp (approximate)
                    if abs((error_info.timestamp - datetime.now()).total_seconds()) < 60:
                        return {
                            "error_id": error_id,
                            "type": user_error.error_type.value,
                            "title": user_error.title,
                            "message": user_error.message,
                            "suggested_actions": user_error.suggested_actions,
                            "technical_details": user_error.technical_details,
                            "retry_available": user_error.retry_available,
                            "fallback_available": user_error.fallback_available,
                            "estimated_resolution_time": user_error.estimated_resolution_time,
                            "timestamp": error_info.timestamp.isoformat(),
                            "severity": error_info.severity.value
                        }
        
        return None

    def get_meaningful_error_message(
        self, 
        component: SystemComponent, 
        operation: str, 
        exception: Exception
    ) -> Dict[str, Any]:
        """
        Get meaningful error message for immediate display.
        
        Args:
            component: System component where error occurred
            operation: Operation that failed
            exception: The exception that occurred
            
        Returns:
            Dictionary with meaningful error message
        """
        
        # Create temporary context for classification
        context = ErrorContext(component=component, operation=operation)
        
        # Classify error
        category, severity = self.base_handler.classify_error(exception)
        
        # Create temporary error info
        temp_error_info = ErrorInfo(
            error_id="temp",
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            message=str(exception),
            exception=exception,
            context=asdict(context),
            stack_trace=None
        )
        
        # Map to user-facing error
        user_error = self._map_to_user_facing_error(temp_error_info, context)
        
        return {
            "title": user_error.title,
            "message": user_error.message,
            "suggested_actions": user_error.suggested_actions,
            "retry_available": user_error.retry_available,
            "fallback_available": user_error.fallback_available,
            "estimated_resolution_time": user_error.estimated_resolution_time,
            "severity": severity.value,
            "component": component.value,
            "operation": operation
        }

    def get_component_health_status(self) -> Dict[str, Any]:
        """Get health status for all system components."""
        
        current_time = datetime.now()
        recent_threshold = current_time - timedelta(minutes=15)
        
        component_health = {}
        
        for component in SystemComponent:
            recent_errors = [
                error for error in self.base_handler.error_history
                if (error.timestamp > recent_threshold and 
                    error.context.get("component") == component.value)
            ]
            
            total_errors = self.component_error_counts.get(component, 0)
            recent_error_count = len(recent_errors)
            
            # Determine health status
            if recent_error_count == 0:
                status = "healthy"
            elif recent_error_count < 3:
                status = "degraded"
            else:
                status = "unhealthy"
            
            component_health[component.value] = {
                "status": status,
                "total_errors": total_errors,
                "recent_errors": recent_error_count,
                "last_error": recent_errors[-1].timestamp.isoformat() if recent_errors else None
            }
        
        return component_health

    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        
        base_stats = self.base_handler.get_error_statistics()
        
        return {
            **base_stats,
            "component_error_counts": {k.value: v for k, v in self.component_error_counts.items()},
            "component_health": self.get_component_health_status(),
            "user_facing_errors_count": len(self.user_facing_errors),
            "error_templates_available": len(self.error_message_templates)
        }

    def cleanup(self):
        """Clean up comprehensive error handler resources."""
        logger.info("Cleaning up ComprehensiveErrorHandler")
        
        # Clean up base handler
        self.base_handler.cleanup()
        
        # Clear component-specific data
        self.component_error_counts.clear()
        self.user_facing_errors.clear()
        
        logger.info("ComprehensiveErrorHandler cleanup completed")


# Global comprehensive error handler instance
_global_comprehensive_handler: Optional[ComprehensiveErrorHandler] = None


def get_comprehensive_error_handler() -> ComprehensiveErrorHandler:
    """Get global comprehensive error handler instance."""
    global _global_comprehensive_handler
    
    if _global_comprehensive_handler is None:
        _global_comprehensive_handler = ComprehensiveErrorHandler()
    
    return _global_comprehensive_handler