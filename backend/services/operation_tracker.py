"""
Operation Tracking System

Monitors backend operations and provides progress tracking for gitingest processing,
Redis cache operations, and other system activities. Works in conjunction with the
StatusBroadcaster to provide real-time visibility into backend processes.
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

import structlog

from .status_broadcaster import (
    StatusBroadcaster, 
    OperationType, 
    OperationStatus,
    get_status_broadcaster
)

logger = structlog.get_logger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for tracking operation performance."""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    progress_updates: int = 0
    bytes_processed: int = 0
    files_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    warnings: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressIndicator:
    """Progress indicator for operations."""
    current: float = 0.0
    total: float = 100.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def percentage(self) -> float:
        """Get progress as percentage (0-100)."""
        if self.total <= 0:
            return 0.0
        return min(100.0, max(0.0, (self.current / self.total) * 100.0))
    
    @property
    def fraction(self) -> float:
        """Get progress as fraction (0-1)."""
        return self.percentage / 100.0
    
    def update(self, current: float, message: str = None, details: Dict[str, Any] = None):
        """Update progress values."""
        self.current = current
        if message is not None:
            self.message = message
        if details is not None:
            self.details.update(details)


class OperationTracker:
    """
    Tracks backend operations and provides progress monitoring.
    
    Integrates with StatusBroadcaster to provide real-time updates to connected clients.
    Supports nested operations, progress tracking, and performance metrics collection.
    """
    
    def __init__(self, status_broadcaster: Optional[StatusBroadcaster] = None):
        self.status_broadcaster = status_broadcaster or get_status_broadcaster()
        
        # Active operations: operation_id -> operation info
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        
        # Operation metrics: operation_id -> OperationMetrics
        self.operation_metrics: Dict[str, OperationMetrics] = {}
        
        # Progress indicators: operation_id -> ProgressIndicator
        self.progress_indicators: Dict[str, ProgressIndicator] = {}
        
        # Parent-child operation relationships: child_id -> parent_id
        self.operation_hierarchy: Dict[str, str] = {}
        
        # Operation callbacks: operation_id -> list of callbacks
        self.operation_callbacks: Dict[str, List[Callable]] = {}
    
    async def start_operation(
        self,
        operation_type: OperationType,
        description: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        parent_operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        total_steps: Optional[float] = None
    ) -> str:
        """
        Start tracking a new operation.
        
        Args:
            operation_type: Type of operation
            description: Human-readable description
            session_id: Optional session ID
            user_id: Optional user ID
            parent_operation_id: Optional parent operation ID for nested operations
            metadata: Optional additional metadata
            total_steps: Optional total steps for progress tracking
            
        Returns:
            str: Unique operation ID
        """
        operation_id = str(uuid.uuid4())
        
        try:
            # Store operation info
            self.active_operations[operation_id] = {
                "operation_id": operation_id,
                "operation_type": operation_type,
                "description": description,
                "session_id": session_id,
                "user_id": user_id,
                "parent_operation_id": parent_operation_id,
                "metadata": metadata or {},
                "status": OperationStatus.STARTING,
                "started_at": datetime.now()
            }
            
            # Initialize metrics
            self.operation_metrics[operation_id] = OperationMetrics(
                start_time=datetime.now()
            )
            
            # Initialize progress indicator
            self.progress_indicators[operation_id] = ProgressIndicator(
                total=total_steps or 100.0,
                message=f"Starting {description}..."
            )
            
            # Set up hierarchy
            if parent_operation_id:
                self.operation_hierarchy[operation_id] = parent_operation_id
            
            # Broadcast operation start
            await self.status_broadcaster.broadcast_operation_start(
                operation_id=operation_id,
                operation_type=operation_type,
                description=description,
                session_id=session_id,
                user_id=user_id,
                metadata=metadata
            )
            
            logger.info(
                "Operation started",
                operation_id=operation_id,
                operation_type=operation_type,
                description=description,
                parent_operation_id=parent_operation_id
            )
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Error starting operation: {e}")
            raise
    
    async def update_progress(
        self,
        operation_id: str,
        current: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update progress for an operation.
        
        Args:
            operation_id: The operation ID
            current: Current progress value
            message: Progress message
            details: Optional additional details
            
        Returns:
            bool: True if update was successful
        """
        try:
            if operation_id not in self.active_operations:
                logger.warning(f"Progress update for unknown operation: {operation_id}")
                return False
            
            # Update progress indicator
            progress = self.progress_indicators[operation_id]
            progress.update(current, message, details or {})
            
            # Update metrics
            metrics = self.operation_metrics[operation_id]
            metrics.progress_updates += 1
            
            # Update operation status
            self.active_operations[operation_id]["status"] = OperationStatus.IN_PROGRESS
            self.active_operations[operation_id]["last_update"] = datetime.now()
            
            # Broadcast progress update
            await self.status_broadcaster.broadcast_operation_progress(
                operation_id=operation_id,
                progress=progress.fraction,
                message=message,
                details={
                    "current": current,
                    "total": progress.total,
                    "percentage": progress.percentage,
                    **(details or {})
                }
            )
            
            # Update parent operation if exists
            parent_id = self.operation_hierarchy.get(operation_id)
            if parent_id:
                await self._update_parent_progress(parent_id)
            
            logger.debug(
                "Operation progress updated",
                operation_id=operation_id,
                progress=progress.percentage,
                message=message
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating operation progress: {e}")
            return False
    
    async def complete_operation(
        self,
        operation_id: str,
        result: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None
    ) -> bool:
        """
        Mark an operation as completed.
        
        Args:
            operation_id: The operation ID
            result: Optional result data
            summary: Optional summary message
            
        Returns:
            bool: True if completion was successful
        """
        try:
            if operation_id not in self.active_operations:
                logger.warning(f"Completion for unknown operation: {operation_id}")
                return False
            
            # Update operation status
            operation = self.active_operations[operation_id]
            operation["status"] = OperationStatus.COMPLETED
            operation["completed_at"] = datetime.now()
            operation["result"] = result or {}
            
            # Update metrics
            metrics = self.operation_metrics[operation_id]
            metrics.end_time = datetime.now()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
            
            # Update progress to 100%
            progress = self.progress_indicators[operation_id]
            progress.current = progress.total
            progress.message = summary or f"{operation['description']} completed"
            
            # Broadcast completion
            await self.status_broadcaster.broadcast_operation_complete(
                operation_id=operation_id,
                result=result,
                summary=summary
            )
            
            # Execute callbacks
            await self._execute_callbacks(operation_id, "completed", result)
            
            # Update parent operation if exists
            parent_id = self.operation_hierarchy.get(operation_id)
            if parent_id:
                await self._update_parent_progress(parent_id)
            
            logger.info(
                "Operation completed",
                operation_id=operation_id,
                duration=metrics.duration,
                summary=summary
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error completing operation: {e}")
            return False
    
    async def fail_operation(
        self,
        operation_id: str,
        error: str,
        error_details: Optional[Dict[str, Any]] = None,
        is_recoverable: bool = False
    ) -> bool:
        """
        Mark an operation as failed.
        
        Args:
            operation_id: The operation ID
            error: Error message
            error_details: Optional error details
            is_recoverable: Whether the error is recoverable
            
        Returns:
            bool: True if failure was recorded successfully
        """
        try:
            if operation_id not in self.active_operations:
                logger.warning(f"Failure for unknown operation: {operation_id}")
                return False
            
            # Update operation status
            operation = self.active_operations[operation_id]
            operation["status"] = OperationStatus.FAILED
            operation["failed_at"] = datetime.now()
            operation["error"] = error
            operation["error_details"] = error_details or {}
            
            # Update metrics
            metrics = self.operation_metrics[operation_id]
            metrics.end_time = datetime.now()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.errors += 1
            
            # Update progress message
            progress = self.progress_indicators[operation_id]
            progress.message = f"Failed: {error}"
            
            # Broadcast error
            await self.status_broadcaster.broadcast_operation_error(
                operation_id=operation_id,
                error=error,
                error_details=error_details,
                is_recoverable=is_recoverable
            )
            
            # Execute callbacks
            await self._execute_callbacks(operation_id, "failed", {"error": error, "error_details": error_details})
            
            logger.error(
                "Operation failed",
                operation_id=operation_id,
                error=error,
                is_recoverable=is_recoverable
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording operation failure: {e}")
            return False
    
    def add_callback(
        self,
        operation_id: str,
        callback: Callable[[str, str, Any], Awaitable[None]]
    ):
        """
        Add a callback to be executed when operation status changes.
        
        Args:
            operation_id: The operation ID
            callback: Async callback function (operation_id, status, data)
        """
        if operation_id not in self.operation_callbacks:
            self.operation_callbacks[operation_id] = []
        self.operation_callbacks[operation_id].append(callback)
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an operation."""
        if operation_id not in self.active_operations:
            return None
        
        operation = self.active_operations[operation_id]
        metrics = self.operation_metrics.get(operation_id)
        progress = self.progress_indicators.get(operation_id)
        
        return {
            "operation_id": operation_id,
            "operation_type": operation["operation_type"],
            "description": operation["description"],
            "status": operation["status"],
            "started_at": operation["started_at"].isoformat(),
            "progress": {
                "current": progress.current if progress else 0,
                "total": progress.total if progress else 100,
                "percentage": progress.percentage if progress else 0,
                "message": progress.message if progress else "",
                "details": progress.details if progress else {}
            },
            "metrics": {
                "duration": metrics.duration if metrics and metrics.duration else None,
                "progress_updates": metrics.progress_updates if metrics else 0,
                "bytes_processed": metrics.bytes_processed if metrics else 0,
                "files_processed": metrics.files_processed if metrics else 0,
                "errors": metrics.errors if metrics else 0,
                "warnings": metrics.warnings if metrics else 0
            } if metrics else {},
            "metadata": operation.get("metadata", {})
        }
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get all active operations."""
        return [
            self.get_operation_status(op_id)
            for op_id in self.active_operations.keys()
        ]
    
    @asynccontextmanager
    async def track_operation(
        self,
        operation_type: OperationType,
        description: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        parent_operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        total_steps: Optional[float] = None
    ):
        """
        Context manager for tracking an operation.
        
        Usage:
            async with tracker.track_operation(
                OperationType.GITINGEST,
                "Processing repository"
            ) as operation_id:
                # Do work
                await tracker.update_progress(operation_id, 50, "Halfway done")
                # Operation will be automatically completed or failed
        """
        operation_id = await self.start_operation(
            operation_type=operation_type,
            description=description,
            session_id=session_id,
            user_id=user_id,
            parent_operation_id=parent_operation_id,
            metadata=metadata,
            total_steps=total_steps
        )
        
        try:
            yield operation_id
            # Auto-complete if not already completed/failed
            if (operation_id in self.active_operations and 
                self.active_operations[operation_id]["status"] in [OperationStatus.STARTING, OperationStatus.IN_PROGRESS]):
                await self.complete_operation(operation_id)
        except Exception as e:
            # Auto-fail on exception
            await self.fail_operation(
                operation_id,
                str(e),
                {"exception_type": type(e).__name__},
                is_recoverable=False
            )
            raise
    
    async def update_metrics(
        self,
        operation_id: str,
        bytes_processed: Optional[int] = None,
        files_processed: Optional[int] = None,
        cache_hits: Optional[int] = None,
        cache_misses: Optional[int] = None,
        custom_metrics: Optional[Dict[str, Any]] = None
    ):
        """Update metrics for an operation."""
        if operation_id not in self.operation_metrics:
            return
        
        metrics = self.operation_metrics[operation_id]
        
        if bytes_processed is not None:
            metrics.bytes_processed += bytes_processed
        if files_processed is not None:
            metrics.files_processed += files_processed
        if cache_hits is not None:
            metrics.cache_hits += cache_hits
        if cache_misses is not None:
            metrics.cache_misses += cache_misses
        if custom_metrics:
            metrics.custom_metrics.update(custom_metrics)
    
    async def _update_parent_progress(self, parent_id: str):
        """Update progress of parent operation based on child operations."""
        if parent_id not in self.active_operations:
            return
        
        # Find all child operations
        child_operations = [
            op_id for op_id, parent in self.operation_hierarchy.items()
            if parent == parent_id
        ]
        
        if not child_operations:
            return
        
        # Calculate average progress of children
        total_progress = 0.0
        completed_children = 0
        
        for child_id in child_operations:
            if child_id in self.progress_indicators:
                child_progress = self.progress_indicators[child_id]
                total_progress += child_progress.fraction
                if child_progress.fraction >= 1.0:
                    completed_children += 1
        
        if child_operations:
            avg_progress = total_progress / len(child_operations)
            parent_progress = self.progress_indicators[parent_id]
            
            await self.update_progress(
                parent_id,
                avg_progress * parent_progress.total,
                f"Completed {completed_children}/{len(child_operations)} sub-operations",
                {"child_operations": len(child_operations), "completed": completed_children}
            )
    
    async def _execute_callbacks(self, operation_id: str, status: str, data: Any):
        """Execute callbacks for an operation."""
        if operation_id not in self.operation_callbacks:
            return
        
        callbacks = self.operation_callbacks[operation_id]
        for callback in callbacks:
            try:
                await callback(operation_id, status, data)
            except Exception as e:
                logger.error(f"Error executing operation callback: {e}")
    
    async def cleanup_completed_operations(self, max_age_hours: int = 24):
        """Clean up old completed operations."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        operations_to_remove = []
        for operation_id, operation in self.active_operations.items():
            if (operation["status"] in [OperationStatus.COMPLETED, OperationStatus.FAILED] and
                operation.get("completed_at", operation.get("failed_at", datetime.now())) < cutoff_time):
                operations_to_remove.append(operation_id)
        
        for operation_id in operations_to_remove:
            self._cleanup_operation(operation_id)
        
        logger.info(f"Cleaned up {len(operations_to_remove)} old operations")
    
    def _cleanup_operation(self, operation_id: str):
        """Clean up data for a single operation."""
        self.active_operations.pop(operation_id, None)
        self.operation_metrics.pop(operation_id, None)
        self.progress_indicators.pop(operation_id, None)
        self.operation_callbacks.pop(operation_id, None)
        
        # Remove from hierarchy
        self.operation_hierarchy.pop(operation_id, None)
        children_to_remove = [
            child_id for child_id, parent_id in self.operation_hierarchy.items()
            if parent_id == operation_id
        ]
        for child_id in children_to_remove:
            self.operation_hierarchy.pop(child_id, None)


# Global operation tracker instance
_operation_tracker: Optional[OperationTracker] = None


def get_operation_tracker() -> OperationTracker:
    """Get the global operation tracker instance."""
    global _operation_tracker
    if _operation_tracker is None:
        _operation_tracker = OperationTracker()
    return _operation_tracker