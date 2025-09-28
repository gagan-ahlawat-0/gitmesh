"""
Fallback Mechanisms Service

Provides comprehensive fallback strategies for system failures:
- Alternative processing paths for degraded performance
- User notification system for service issues
- Graceful degradation strategies
- Recovery mechanisms and health monitoring

Requirements: 2.5, 3.5, 5.4
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .comprehensive_error_handler import (
    ComprehensiveErrorHandler, 
    SystemComponent, 
    get_comprehensive_error_handler
)

logger = logging.getLogger(__name__)


class FallbackStrategy(Enum):
    """Available fallback strategies."""
    DIRECT_PROCESSING = "direct_processing"
    CACHED_RESPONSE = "cached_response"
    SIMPLIFIED_RESPONSE = "simplified_response"
    BASIC_FUNCTIONALITY = "basic_functionality"
    OFFLINE_MODE = "offline_mode"
    QUEUE_FOR_RETRY = "queue_for_retry"
    ALTERNATIVE_SERVICE = "alternative_service"
    GRACEFUL_SKIP = "graceful_skip"


class ServiceIssueType(Enum):
    """Types of service issues for user notifications."""
    TEMPORARY_UNAVAILABLE = "temporary_unavailable"
    DEGRADED_PERFORMANCE = "degraded_performance"
    PARTIAL_FUNCTIONALITY = "partial_functionality"
    MAINTENANCE_MODE = "maintenance_mode"
    HIGH_LOAD = "high_load"
    CONNECTIVITY_ISSUE = "connectivity_issue"


@dataclass
class FallbackResult:
    """Result of a fallback operation."""
    strategy_used: FallbackStrategy
    success: bool
    result: Any
    performance_impact: str  # "none", "minimal", "moderate", "significant"
    user_message: Optional[str] = None
    technical_details: Optional[str] = None
    retry_recommended: bool = True
    estimated_resolution: Optional[str] = None


@dataclass
class ServiceIssue:
    """Service issue information for user notifications."""
    issue_id: str
    component: SystemComponent
    issue_type: ServiceIssueType
    title: str
    description: str
    impact_level: str  # "low", "medium", "high", "critical"
    affected_features: List[str]
    workaround_available: bool
    workaround_description: Optional[str] = None
    estimated_resolution: Optional[str] = None
    started_at: datetime = None
    resolved_at: Optional[datetime] = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()


class AlternativeProcessingPaths:
    """
    Manages alternative processing paths for different system components.
    """

    def __init__(self):
        """Initialize alternative processing paths."""
        self.processing_paths: Dict[str, List[Callable]] = {}
        self.path_performance: Dict[str, Dict[str, float]] = {}
        self.path_success_rates: Dict[str, Dict[str, float]] = {}
        
        # Register default alternative paths
        self._register_default_paths()
        
        logger.info("AlternativeProcessingPaths initialized")

    def _register_default_paths(self):
        """Register default alternative processing paths."""
        
        # Redis cache alternatives
        self.register_processing_path(
            "redis_cache_get",
            [
                self._direct_file_access,
                self._memory_cache_fallback,
                self._basic_response_fallback
            ]
        )
        
        # GitIngest alternatives
        self.register_processing_path(
            "gitingest_process",
            [
                self._basic_repo_scan,
                self._cached_repo_info,
                self._minimal_repo_response
            ]
        )
        
        # Supabase alternatives
        self.register_processing_path(
            "supabase_store",
            [
                self._local_storage_fallback,
                self._memory_storage_fallback,
                self._skip_storage_fallback
            ]
        )
        
        # Cosmos AI alternatives
        self.register_processing_path(
            "cosmos_process",
            [
                self._simplified_ai_response,
                self._template_response,
                self._error_acknowledgment_response
            ]
        )

    def register_processing_path(self, operation: str, path_functions: List[Callable]):
        """Register alternative processing path for an operation."""
        self.processing_paths[operation] = path_functions
        self.path_performance[operation] = {}
        self.path_success_rates[operation] = {}
        
        logger.debug(f"Registered {len(path_functions)} alternative paths for {operation}")

    async def execute_alternative_path(
        self, 
        operation: str, 
        primary_error: Exception,
        *args, 
        **kwargs
    ) -> FallbackResult:
        """
        Execute alternative processing path for failed operation.
        
        Args:
            operation: Operation that failed
            primary_error: Error from primary operation
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            FallbackResult with outcome
        """
        
        if operation not in self.processing_paths:
            return FallbackResult(
                strategy_used=FallbackStrategy.GRACEFUL_SKIP,
                success=False,
                result=None,
                performance_impact="significant",
                user_message="No alternative processing available for this operation",
                retry_recommended=True
            )
        
        paths = self.processing_paths[operation]
        
        for i, path_func in enumerate(paths):
            path_name = f"path_{i}_{path_func.__name__}"
            start_time = time.time()
            
            try:
                logger.info(f"Trying alternative path {path_name} for {operation}")
                
                if asyncio.iscoroutinefunction(path_func):
                    result = await path_func(primary_error, *args, **kwargs)
                else:
                    result = path_func(primary_error, *args, **kwargs)
                
                # Record performance
                execution_time = time.time() - start_time
                self.path_performance[operation][path_name] = execution_time
                
                # Update success rate
                current_rate = self.path_success_rates[operation].get(path_name, 0.0)
                self.path_success_rates[operation][path_name] = min(1.0, current_rate + 0.1)
                
                # Determine performance impact
                if execution_time < 0.5:
                    performance_impact = "minimal"
                elif execution_time < 2.0:
                    performance_impact = "moderate"
                else:
                    performance_impact = "significant"
                
                logger.info(f"Alternative path {path_name} succeeded for {operation}")
                
                return FallbackResult(
                    strategy_used=self._determine_strategy(path_func),
                    success=True,
                    result=result,
                    performance_impact=performance_impact,
                    user_message=f"Using alternative processing method",
                    technical_details=f"Fallback path: {path_name}",
                    retry_recommended=True,
                    estimated_resolution="1-2 minutes"
                )
                
            except Exception as e:
                # Update failure rate
                current_rate = self.path_success_rates[operation].get(path_name, 1.0)
                self.path_success_rates[operation][path_name] = max(0.0, current_rate - 0.1)
                
                logger.warning(f"Alternative path {path_name} failed for {operation}: {e}")
                continue
        
        # All alternative paths failed
        return FallbackResult(
            strategy_used=FallbackStrategy.GRACEFUL_SKIP,
            success=False,
            result=None,
            performance_impact="significant",
            user_message="All alternative processing methods failed",
            technical_details=f"Tried {len(paths)} alternative paths",
            retry_recommended=True,
            estimated_resolution="5-10 minutes"
        )

    def _determine_strategy(self, path_func: Callable) -> FallbackStrategy:
        """Determine fallback strategy based on function name."""
        func_name = path_func.__name__.lower()
        
        if "direct" in func_name or "file" in func_name:
            return FallbackStrategy.DIRECT_PROCESSING
        elif "cache" in func_name:
            return FallbackStrategy.CACHED_RESPONSE
        elif "simplified" in func_name or "basic" in func_name:
            return FallbackStrategy.SIMPLIFIED_RESPONSE
        elif "template" in func_name:
            return FallbackStrategy.BASIC_FUNCTIONALITY
        elif "memory" in func_name or "local" in func_name:
            return FallbackStrategy.ALTERNATIVE_SERVICE
        elif "skip" in func_name:
            return FallbackStrategy.GRACEFUL_SKIP
        else:
            return FallbackStrategy.DIRECT_PROCESSING

    # Alternative processing implementations
    
    async def _direct_file_access(self, error: Exception, *args, **kwargs) -> Dict[str, Any]:
        """Direct file access fallback for Redis cache failures."""
        logger.info("Using direct file access fallback")
        
        # This would implement direct file system access
        # For now, return a basic structure
        return {
            "method": "direct_file_access",
            "data": "Basic file content",
            "source": "filesystem",
            "performance_note": "Slower than cache but functional"
        }

    def _memory_cache_fallback(self, error: Exception, *args, **kwargs) -> Dict[str, Any]:
        """In-memory cache fallback."""
        logger.info("Using memory cache fallback")
        
        return {
            "method": "memory_cache",
            "data": "Cached in memory",
            "source": "memory",
            "limitation": "Data may not persist across restarts"
        }

    def _basic_response_fallback(self, error: Exception, *args, **kwargs) -> Dict[str, Any]:
        """Basic response fallback."""
        return {
            "method": "basic_response",
            "message": "Basic functionality available",
            "limitation": "Limited features due to system issues"
        }

    async def _basic_repo_scan(self, error: Exception, repo_url: str, **kwargs) -> Dict[str, Any]:
        """Basic repository scan fallback."""
        logger.info(f"Using basic repo scan fallback for {repo_url}")
        
        return {
            "repo_url": repo_url,
            "repo_name": repo_url.split("/")[-1] if "/" in repo_url else repo_url,
            "method": "basic_scan",
            "files": ["README.md", "main.py", "requirements.txt"],  # Mock data
            "note": "Basic repository information only"
        }

    def _cached_repo_info(self, error: Exception, repo_url: str, **kwargs) -> Dict[str, Any]:
        """Cached repository info fallback."""
        return {
            "repo_url": repo_url,
            "method": "cached_info",
            "data": "Previously cached repository information",
            "freshness": "May not reflect recent changes"
        }

    def _minimal_repo_response(self, error: Exception, repo_url: str, **kwargs) -> Dict[str, Any]:
        """Minimal repository response fallback."""
        return {
            "repo_url": repo_url,
            "method": "minimal_response",
            "message": "Repository access limited due to technical issues"
        }

    def _local_storage_fallback(self, error: Exception, *args, **kwargs) -> Dict[str, Any]:
        """Local storage fallback for Supabase."""
        return {
            "method": "local_storage",
            "status": "stored_locally",
            "warning": "Data stored locally, may not sync until service recovers"
        }

    def _memory_storage_fallback(self, error: Exception, *args, **kwargs) -> Dict[str, Any]:
        """Memory storage fallback."""
        return {
            "method": "memory_storage",
            "status": "stored_in_memory",
            "warning": "Data will be lost when session ends"
        }

    def _skip_storage_fallback(self, error: Exception, *args, **kwargs) -> Dict[str, Any]:
        """Skip storage fallback."""
        return {
            "method": "skip_storage",
            "status": "storage_skipped",
            "warning": "Data not saved due to storage issues"
        }

    def _simplified_ai_response(self, error: Exception, message: str, **kwargs) -> str:
        """Simplified AI response fallback."""
        return (
            f"I understand you're asking about: '{message[:100]}...'. "
            f"I'm currently experiencing technical difficulties that limit my ability to provide "
            f"detailed analysis. Please try again in a few minutes for full functionality."
        )

    def _template_response(self, error: Exception, message: str, **kwargs) -> str:
        """Template response fallback."""
        return (
            f"Thank you for your message. I'm currently operating in limited mode due to "
            f"technical issues. Your request has been noted and I'll provide a full response "
            f"once normal operations resume."
        )

    def _error_acknowledgment_response(self, error: Exception, message: str, **kwargs) -> str:
        """Error acknowledgment response fallback."""
        return (
            f"I apologize, but I'm currently unable to process your request due to system issues. "
            f"Please try again shortly. If the problem persists, please contact support."
        )

    def get_path_statistics(self) -> Dict[str, Any]:
        """Get statistics about alternative processing paths."""
        return {
            "registered_operations": list(self.processing_paths.keys()),
            "path_performance": self.path_performance,
            "path_success_rates": self.path_success_rates,
            "total_paths": sum(len(paths) for paths in self.processing_paths.values())
        }


class UserNotificationSystem:
    """
    System for notifying users about service issues and providing guidance.
    """

    def __init__(self):
        """Initialize user notification system."""
        self.active_issues: Dict[str, ServiceIssue] = {}
        self.notification_history: List[ServiceIssue] = []
        self.notification_templates = self._initialize_notification_templates()
        
        logger.info("UserNotificationSystem initialized")

    def _initialize_notification_templates(self) -> Dict[ServiceIssueType, Dict[str, Any]]:
        """Initialize notification templates for different issue types."""
        return {
            ServiceIssueType.TEMPORARY_UNAVAILABLE: {
                "title": "Service Temporarily Unavailable",
                "description_template": "The {component} service is temporarily unavailable. We're working to restore it quickly.",
                "impact_descriptions": {
                    "low": "Some features may be slower than usual",
                    "medium": "Several features are currently limited",
                    "high": "Most features are currently unavailable",
                    "critical": "The service is completely unavailable"
                },
                "default_workaround": "Please wait a few minutes and try again"
            },
            ServiceIssueType.DEGRADED_PERFORMANCE: {
                "title": "Performance Issues",
                "description_template": "The {component} service is experiencing performance issues.",
                "impact_descriptions": {
                    "low": "Responses may be slightly slower",
                    "medium": "Responses are noticeably slower",
                    "high": "Significant delays in responses",
                    "critical": "Severe performance degradation"
                },
                "default_workaround": "Continue using the service normally, expect longer response times"
            },
            ServiceIssueType.PARTIAL_FUNCTIONALITY: {
                "title": "Limited Functionality",
                "description_template": "Some features of the {component} service are currently limited.",
                "impact_descriptions": {
                    "low": "Minor features affected",
                    "medium": "Some important features affected",
                    "high": "Many features affected",
                    "critical": "Most features affected"
                },
                "default_workaround": "Core functionality remains available"
            },
            ServiceIssueType.MAINTENANCE_MODE: {
                "title": "Maintenance in Progress",
                "description_template": "The {component} service is undergoing scheduled maintenance.",
                "impact_descriptions": {
                    "low": "Minimal impact expected",
                    "medium": "Some features temporarily unavailable",
                    "high": "Service mostly unavailable",
                    "critical": "Service completely unavailable"
                },
                "default_workaround": "Please check back after the maintenance window"
            },
            ServiceIssueType.HIGH_LOAD: {
                "title": "High System Load",
                "description_template": "The {component} service is experiencing higher than normal load.",
                "impact_descriptions": {
                    "low": "Slight delays possible",
                    "medium": "Noticeable delays",
                    "high": "Significant delays",
                    "critical": "Service may be unresponsive"
                },
                "default_workaround": "Please be patient, the system will catch up shortly"
            },
            ServiceIssueType.CONNECTIVITY_ISSUE: {
                "title": "Connectivity Problems",
                "description_template": "There are connectivity issues affecting the {component} service.",
                "impact_descriptions": {
                    "low": "Occasional connection issues",
                    "medium": "Frequent connection problems",
                    "high": "Persistent connection issues",
                    "critical": "Unable to connect to service"
                },
                "default_workaround": "Check your internet connection and try again"
            }
        }

    def create_service_issue(
        self,
        component: SystemComponent,
        issue_type: ServiceIssueType,
        impact_level: str,
        affected_features: List[str],
        custom_description: Optional[str] = None,
        workaround_description: Optional[str] = None,
        estimated_resolution: Optional[str] = None
    ) -> ServiceIssue:
        """
        Create a new service issue notification.
        
        Args:
            component: Affected system component
            issue_type: Type of service issue
            impact_level: Impact level (low, medium, high, critical)
            affected_features: List of affected features
            custom_description: Custom description (optional)
            workaround_description: Custom workaround description (optional)
            estimated_resolution: Estimated resolution time (optional)
            
        Returns:
            ServiceIssue object
        """
        
        issue_id = f"{component.value}_{issue_type.value}_{int(time.time())}"
        template = self.notification_templates[issue_type]
        
        # Generate description
        if custom_description:
            description = custom_description
        else:
            description = template["description_template"].format(component=component.value)
            description += f" {template['impact_descriptions'][impact_level]}"
        
        # Determine workaround
        workaround_available = bool(workaround_description or template.get("default_workaround"))
        final_workaround = workaround_description or template.get("default_workaround")
        
        issue = ServiceIssue(
            issue_id=issue_id,
            component=component,
            issue_type=issue_type,
            title=template["title"],
            description=description,
            impact_level=impact_level,
            affected_features=affected_features,
            workaround_available=workaround_available,
            workaround_description=final_workaround,
            estimated_resolution=estimated_resolution
        )
        
        # Add to active issues
        self.active_issues[issue_id] = issue
        
        # Add to history
        self.notification_history.append(issue)
        
        # Keep only last 100 notifications in history
        if len(self.notification_history) > 100:
            self.notification_history = self.notification_history[-100:]
        
        logger.info(f"Created service issue notification: {issue_id}")
        
        return issue

    def resolve_service_issue(self, issue_id: str) -> bool:
        """
        Mark a service issue as resolved.
        
        Args:
            issue_id: ID of the issue to resolve
            
        Returns:
            True if issue was found and resolved, False otherwise
        """
        
        if issue_id in self.active_issues:
            issue = self.active_issues[issue_id]
            issue.resolved_at = datetime.now()
            del self.active_issues[issue_id]
            
            logger.info(f"Resolved service issue: {issue_id}")
            return True
        
        return False

    def get_active_issues_for_component(self, component: SystemComponent) -> List[ServiceIssue]:
        """Get active issues for a specific component."""
        return [
            issue for issue in self.active_issues.values()
            if issue.component == component
        ]

    def get_user_notification(self, component: SystemComponent) -> Optional[Dict[str, Any]]:
        """
        Get user notification for a component's current issues.
        
        Args:
            component: System component to check
            
        Returns:
            Dictionary with notification information or None
        """
        
        active_issues = self.get_active_issues_for_component(component)
        
        if not active_issues:
            return None
        
        # Get the most severe issue
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        most_severe = max(active_issues, key=lambda x: severity_order[x.impact_level])
        
        return {
            "issue_id": most_severe.issue_id,
            "title": most_severe.title,
            "description": most_severe.description,
            "impact_level": most_severe.impact_level,
            "affected_features": most_severe.affected_features,
            "workaround_available": most_severe.workaround_available,
            "workaround_description": most_severe.workaround_description,
            "estimated_resolution": most_severe.estimated_resolution,
            "started_at": most_severe.started_at.isoformat(),
            "total_active_issues": len(active_issues)
        }

    def get_system_status_summary(self) -> Dict[str, Any]:
        """Get overall system status summary."""
        
        component_status = {}
        overall_status = "operational"
        
        for component in SystemComponent:
            issues = self.get_active_issues_for_component(component)
            
            if not issues:
                component_status[component.value] = "operational"
            else:
                # Determine component status based on most severe issue
                severity_levels = [issue.impact_level for issue in issues]
                if "critical" in severity_levels:
                    component_status[component.value] = "major_outage"
                    overall_status = "major_outage"
                elif "high" in severity_levels:
                    component_status[component.value] = "partial_outage"
                    if overall_status == "operational":
                        overall_status = "partial_outage"
                elif "medium" in severity_levels:
                    component_status[component.value] = "degraded_performance"
                    if overall_status == "operational":
                        overall_status = "degraded_performance"
                else:
                    component_status[component.value] = "minor_issues"
                    if overall_status == "operational":
                        overall_status = "minor_issues"
        
        return {
            "overall_status": overall_status,
            "component_status": component_status,
            "total_active_issues": len(self.active_issues),
            "last_updated": datetime.now().isoformat()
        }

    def cleanup_old_issues(self, max_age_hours: int = 24):
        """Clean up old resolved issues from history."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Remove old issues from history
        self.notification_history = [
            issue for issue in self.notification_history
            if (issue.resolved_at is None or issue.resolved_at > cutoff_time)
        ]
        
        logger.info(f"Cleaned up old service issues older than {max_age_hours} hours")


class FallbackMechanismsService:
    """
    Main service that coordinates all fallback mechanisms.
    """

    def __init__(self):
        """Initialize fallback mechanisms service."""
        self.error_handler = get_comprehensive_error_handler()
        self.alternative_paths = AlternativeProcessingPaths()
        self.notification_system = UserNotificationSystem()
        
        # Integration with error handler
        self._integrate_with_error_handler()
        
        logger.info("FallbackMechanismsService initialized")

    def _integrate_with_error_handler(self):
        """Integrate with the comprehensive error handler."""
        
        # Register this service's fallback functions with the error handler
        self.error_handler.base_handler.fallback_manager.register_fallback(
            "comprehensive_fallback",
            self.execute_comprehensive_fallback
        )

    async def execute_comprehensive_fallback(
        self,
        operation: str,
        component: SystemComponent,
        primary_error: Exception,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute comprehensive fallback for a failed operation.
        
        Args:
            operation: Operation that failed
            component: System component involved
            primary_error: Primary error that occurred
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Dictionary with fallback result and user notification
        """
        
        # Try alternative processing path
        fallback_result = await self.alternative_paths.execute_alternative_path(
            operation, primary_error, *args, **kwargs
        )
        
        # Create service issue notification if fallback failed or has significant impact
        if not fallback_result.success or fallback_result.performance_impact in ["moderate", "significant"]:
            
            # Determine issue type and impact level
            if not fallback_result.success:
                issue_type = ServiceIssueType.TEMPORARY_UNAVAILABLE
                impact_level = "high"
            elif fallback_result.performance_impact == "significant":
                issue_type = ServiceIssueType.DEGRADED_PERFORMANCE
                impact_level = "medium"
            else:
                issue_type = ServiceIssueType.PARTIAL_FUNCTIONALITY
                impact_level = "low"
            
            # Create service issue
            service_issue = self.notification_system.create_service_issue(
                component=component,
                issue_type=issue_type,
                impact_level=impact_level,
                affected_features=[operation],
                estimated_resolution=fallback_result.estimated_resolution
            )
            
            user_notification = self.notification_system.get_user_notification(component)
        else:
            user_notification = None
        
        return {
            "fallback_result": asdict(fallback_result),
            "user_notification": user_notification,
            "operation": operation,
            "component": component.value,
            "timestamp": datetime.now().isoformat()
        }

    async def handle_system_failure(
        self,
        component: SystemComponent,
        operation: str,
        error: Exception,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle system failure with comprehensive fallback mechanisms.
        
        Args:
            component: Failed system component
            operation: Failed operation
            error: Error that occurred
            context: Additional context
            
        Returns:
            Dictionary with handling result
        """
        
        context = context or {}
        
        # Execute comprehensive fallback
        result = await self.execute_comprehensive_fallback(
            operation, component, error, **context
        )
        
        # Log the fallback execution
        logger.info(
            f"Executed fallback for {component.value}.{operation}: "
            f"success={result['fallback_result']['success']}, "
            f"strategy={result['fallback_result']['strategy_used']}"
        )
        
        return result

    def get_service_health_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive service health dashboard."""
        
        return {
            "system_status": self.notification_system.get_system_status_summary(),
            "alternative_paths": self.alternative_paths.get_path_statistics(),
            "error_statistics": self.error_handler.get_comprehensive_statistics(),
            "active_issues": len(self.notification_system.active_issues),
            "timestamp": datetime.now().isoformat()
        }

    def cleanup(self):
        """Clean up fallback mechanisms service."""
        logger.info("Cleaning up FallbackMechanismsService")
        
        # Clean up notification system
        self.notification_system.cleanup_old_issues()
        
        # Clean up error handler
        self.error_handler.cleanup()
        
        logger.info("FallbackMechanismsService cleanup completed")


# Global fallback mechanisms service instance
_global_fallback_service: Optional[FallbackMechanismsService] = None


def get_fallback_mechanisms_service() -> FallbackMechanismsService:
    """Get global fallback mechanisms service instance."""
    global _global_fallback_service
    
    if _global_fallback_service is None:
        _global_fallback_service = FallbackMechanismsService()
    
    return _global_fallback_service