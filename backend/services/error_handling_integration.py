"""
Error Handling Integration Service

Integrates comprehensive error handling and fallback mechanisms with the main application:
- Provides API endpoints for error information
- Integrates with existing services
- Handles error recovery and user notifications
- Monitors system health and performance

Requirements: 2.5, 3.5, 5.4
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import asdict
import json

from .comprehensive_error_handler import (
    ComprehensiveErrorHandler,
    SystemComponent,
    ErrorContext,
    get_comprehensive_error_handler
)
from .fallback_mechanisms import (
    FallbackMechanismsService,
    get_fallback_mechanisms_service
)

logger = logging.getLogger(__name__)


class ErrorHandlingIntegration:
    """
    Integration service for error handling and fallback mechanisms.
    
    Provides a unified interface for error handling across the application
    and integrates with existing services.
    """

    def __init__(self):
        """Initialize error handling integration."""
        self.error_handler = get_comprehensive_error_handler()
        self.fallback_service = get_fallback_mechanisms_service()
        self.integration_callbacks: Dict[str, List[Callable]] = {}
        
        logger.info("ErrorHandlingIntegration initialized")

    def register_integration_callback(self, event_type: str, callback: Callable):
        """
        Register callback for integration events.
        
        Args:
            event_type: Type of event (error_occurred, fallback_executed, etc.)
            callback: Callback function to execute
        """
        if event_type not in self.integration_callbacks:
            self.integration_callbacks[event_type] = []
        
        self.integration_callbacks[event_type].append(callback)
        logger.debug(f"Registered callback for event type: {event_type}")

    async def _trigger_callbacks(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger registered callbacks for an event type."""
        if event_type in self.integration_callbacks:
            for callback in self.integration_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_data)
                    else:
                        callback(event_data)
                except Exception as e:
                    logger.error(f"Error in integration callback for {event_type}: {e}")

    async def handle_service_error(
        self,
        component: SystemComponent,
        operation: str,
        error: Exception,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        repository_url: Optional[str] = None,
        request_id: Optional[str] = None,
        **context_data
    ) -> Dict[str, Any]:
        """
        Handle service error with comprehensive error handling and fallbacks.
        
        Args:
            component: System component where error occurred
            operation: Operation that failed
            error: Exception that occurred
            user_id: User ID for context
            session_id: Session ID for context
            repository_url: Repository URL for context
            request_id: Request ID for context
            **context_data: Additional context data
            
        Returns:
            Dictionary with error handling result
        """
        
        # Create error context
        context = ErrorContext(
            component=component,
            operation=operation,
            user_id=user_id,
            session_id=session_id,
            repository_url=repository_url,
            request_id=request_id,
            additional_data=context_data
        )
        
        # Handle error with comprehensive error handler
        error_info, user_error = await self.error_handler.handle_component_error(
            error, context
        )
        
        # Execute fallback mechanisms
        fallback_result = await self.fallback_service.handle_system_failure(
            component, operation, error, context_data
        )
        
        # Prepare result
        result = {
            "error_info": {
                "error_id": error_info.error_id,
                "category": error_info.category.value,
                "severity": error_info.severity.value,
                "timestamp": error_info.timestamp.isoformat()
            },
            "user_error": {
                "type": user_error.error_type.value,
                "title": user_error.title,
                "message": user_error.message,
                "suggested_actions": user_error.suggested_actions,
                "retry_available": user_error.retry_available,
                "fallback_available": user_error.fallback_available,
                "estimated_resolution_time": user_error.estimated_resolution_time
            },
            "fallback_result": fallback_result,
            "context": {
                "component": component.value,
                "operation": operation,
                "user_id": user_id,
                "session_id": session_id,
                "repository_url": repository_url,
                "request_id": request_id
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Trigger integration callbacks
        await self._trigger_callbacks("error_occurred", result)
        
        logger.info(
            f"Handled service error: {error_info.error_id} - {component.value}.{operation}",
            extra={
                "error_id": error_info.error_id,
                "component": component.value,
                "operation": operation,
                "user_id": user_id,
                "fallback_success": fallback_result.get("fallback_result", {}).get("success", False)
            }
        )
        
        return result

    async def execute_with_error_handling(
        self,
        operation: str,
        component: SystemComponent,
        func: Callable,
        *args,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        repository_url: Optional[str] = None,
        request_id: Optional[str] = None,
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
            **kwargs: Keyword arguments for function
            
        Returns:
            Result from function execution or fallback
        """
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            return result
            
        except Exception as e:
            # Handle error with comprehensive error handling
            error_result = await self.handle_service_error(
                component=component,
                operation=operation,
                error=e,
                user_id=user_id,
                session_id=session_id,
                repository_url=repository_url,
                request_id=request_id,
                **kwargs
            )
            
            # Check if fallback was successful
            fallback_success = error_result.get("fallback_result", {}).get("fallback_result", {}).get("success", False)
            
            if fallback_success:
                # Return fallback result
                return error_result["fallback_result"]["fallback_result"]["result"]
            else:
                # Re-raise for critical errors or when no fallback available
                user_error = error_result["user_error"]
                if not user_error["fallback_available"]:
                    raise e
                
                # Return None for handled errors with fallback
                return None

    def get_user_facing_error_info(self, error_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user-facing error information for display.
        
        Args:
            error_id: Error ID to look up
            
        Returns:
            Dictionary with user-facing error information or None
        """
        return self.error_handler.get_user_facing_error_for_display(error_id)

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
            exception: Exception that occurred
            
        Returns:
            Dictionary with meaningful error message
        """
        return self.error_handler.get_meaningful_error_message(component, operation, exception)

    def get_system_health_status(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        return {
            "component_health": self.error_handler.get_component_health_status(),
            "service_dashboard": self.fallback_service.get_service_health_dashboard(),
            "timestamp": datetime.now().isoformat()
        }

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        return self.error_handler.get_comprehensive_statistics()

    def get_active_service_issues(self) -> Dict[str, Any]:
        """Get active service issues for user notification."""
        issues_by_component = {}
        
        for component in SystemComponent:
            notification = self.fallback_service.notification_system.get_user_notification(component)
            if notification:
                issues_by_component[component.value] = notification
        
        return {
            "active_issues": issues_by_component,
            "total_issues": len(issues_by_component),
            "system_status": self.fallback_service.notification_system.get_system_status_summary(),
            "timestamp": datetime.now().isoformat()
        }

    async def retry_failed_operation(
        self,
        error_id: str,
        operation: str,
        component: SystemComponent,
        func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retry a previously failed operation.
        
        Args:
            error_id: ID of the original error
            operation: Operation to retry
            component: System component
            func: Function to retry
            *args: Arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Dictionary with retry result
        """
        
        logger.info(f"Retrying operation {operation} for error {error_id}")
        
        try:
            # Execute with error handling
            result = await self.execute_with_error_handling(
                operation, component, func, *args, **kwargs
            )
            
            # Trigger success callback
            await self._trigger_callbacks("retry_succeeded", {
                "error_id": error_id,
                "operation": operation,
                "component": component.value,
                "result": result
            })
            
            return {
                "success": True,
                "result": result,
                "message": "Operation completed successfully on retry",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            # Trigger failure callback
            await self._trigger_callbacks("retry_failed", {
                "error_id": error_id,
                "operation": operation,
                "component": component.value,
                "error": str(e)
            })
            
            return {
                "success": False,
                "error": str(e),
                "message": "Operation failed again on retry",
                "timestamp": datetime.now().isoformat()
            }

    def resolve_service_issue(self, issue_id: str) -> Dict[str, Any]:
        """
        Manually resolve a service issue.
        
        Args:
            issue_id: ID of the issue to resolve
            
        Returns:
            Dictionary with resolution result
        """
        
        resolved = self.fallback_service.notification_system.resolve_service_issue(issue_id)
        
        if resolved:
            logger.info(f"Manually resolved service issue: {issue_id}")
            return {
                "success": True,
                "message": "Service issue resolved successfully",
                "issue_id": issue_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Service issue not found or already resolved",
                "issue_id": issue_id,
                "timestamp": datetime.now().isoformat()
            }

    def cleanup(self):
        """Clean up error handling integration."""
        logger.info("Cleaning up ErrorHandlingIntegration")
        
        # Clean up error handler
        self.error_handler.cleanup()
        
        # Clean up fallback service
        self.fallback_service.cleanup()
        
        # Clear callbacks
        self.integration_callbacks.clear()
        
        logger.info("ErrorHandlingIntegration cleanup completed")


# Global error handling integration instance
_global_integration: Optional[ErrorHandlingIntegration] = None


def get_error_handling_integration() -> ErrorHandlingIntegration:
    """Get global error handling integration instance."""
    global _global_integration
    
    if _global_integration is None:
        _global_integration = ErrorHandlingIntegration()
    
    return _global_integration


# Convenience functions for common operations

async def handle_redis_error(
    operation: str,
    error: Exception,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **context
) -> Dict[str, Any]:
    """Handle Redis-related errors."""
    integration = get_error_handling_integration()
    return await integration.handle_service_error(
        SystemComponent.REDIS_CACHE, operation, error, user_id, session_id, **context
    )


async def handle_gitingest_error(
    operation: str,
    error: Exception,
    repository_url: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **context
) -> Dict[str, Any]:
    """Handle GitIngest-related errors."""
    integration = get_error_handling_integration()
    return await integration.handle_service_error(
        SystemComponent.GITINGEST, operation, error, user_id, session_id, repository_url, **context
    )


async def handle_supabase_error(
    operation: str,
    error: Exception,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **context
) -> Dict[str, Any]:
    """Handle Supabase-related errors."""
    integration = get_error_handling_integration()
    return await integration.handle_service_error(
        SystemComponent.SUPABASE, operation, error, user_id, session_id, **context
    )


async def handle_cleanup_error(
    operation: str,
    error: Exception,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    repository_url: Optional[str] = None,
    **context
) -> Dict[str, Any]:
    """Handle cleanup-related errors."""
    integration = get_error_handling_integration()
    return await integration.handle_service_error(
        SystemComponent.CLEANUP, operation, error, user_id, session_id, repository_url, **context
    )


async def execute_with_redis_error_handling(
    operation: str,
    func: Callable,
    *args,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> Any:
    """Execute function with Redis error handling."""
    integration = get_error_handling_integration()
    return await integration.execute_with_error_handling(
        operation, SystemComponent.REDIS_CACHE, func, *args,
        user_id=user_id, session_id=session_id, **kwargs
    )


async def execute_with_gitingest_error_handling(
    operation: str,
    func: Callable,
    *args,
    repository_url: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> Any:
    """Execute function with GitIngest error handling."""
    integration = get_error_handling_integration()
    return await integration.execute_with_error_handling(
        operation, SystemComponent.GITINGEST, func, *args,
        user_id=user_id, session_id=session_id, repository_url=repository_url, **kwargs
    )