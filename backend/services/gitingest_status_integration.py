"""
GitIngest Status Integration

Integrates gitingest operations with the status broadcasting system to provide
real-time visibility into repository processing operations.
"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime

import structlog

from .status_broadcaster import get_status_broadcaster, OperationType
from .operation_tracker import get_operation_tracker

logger = structlog.get_logger(__name__)


class GitIngestStatusIntegration:
    """
    Integrates gitingest operations with status broadcasting.
    
    Provides real-time status updates for repository processing operations
    including file scanning, content extraction, and cache building.
    """
    
    def __init__(self):
        self.status_broadcaster = get_status_broadcaster()
        self.operation_tracker = get_operation_tracker()
        
        # Track active gitingest operations
        self.active_operations: Dict[str, str] = {}  # repo_url -> operation_id
    
    async def start_gitingest_operation(
        self,
        repo_url: str,
        branch: str = "main",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        estimated_files: Optional[int] = None
    ) -> str:
        """
        Start tracking a gitingest operation.
        
        Args:
            repo_url: Repository URL being processed
            branch: Branch being processed
            session_id: Optional session ID
            user_id: Optional user ID
            estimated_files: Optional estimated number of files
            
        Returns:
            str: Operation ID for tracking
        """
        try:
            # Create operation description
            repo_name = repo_url.split('/')[-1] if '/' in repo_url else repo_url
            description = f"Mapping codebase for {repo_name}"
            
            # Calculate total steps based on estimated files
            total_steps = estimated_files or 100  # Default to 100 if unknown
            
            # Start operation tracking
            operation_id = await self.operation_tracker.start_operation(
                operation_type=OperationType.GITINGEST,
                description=description,
                session_id=session_id,
                user_id=user_id,
                metadata={
                    "repo_url": repo_url,
                    "branch": branch,
                    "estimated_files": estimated_files,
                    "started_at": datetime.now().isoformat()
                },
                total_steps=total_steps
            )
            
            # Store operation mapping
            self.active_operations[repo_url] = operation_id
            
            logger.info(
                "GitIngest operation started",
                operation_id=operation_id,
                repo_url=repo_url,
                branch=branch,
                estimated_files=estimated_files
            )
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Error starting gitingest operation: {e}")
            raise
    
    async def update_gitingest_progress(
        self,
        repo_url: str,
        files_processed: int,
        total_files: int,
        current_file: Optional[str] = None,
        bytes_processed: Optional[int] = None,
        stage: str = "processing"
    ) -> bool:
        """
        Update progress for a gitingest operation.
        
        Args:
            repo_url: Repository URL
            files_processed: Number of files processed so far
            total_files: Total number of files to process
            current_file: Currently processing file
            bytes_processed: Bytes processed so far
            stage: Current processing stage
            
        Returns:
            bool: True if update was successful
        """
        try:
            if repo_url not in self.active_operations:
                logger.warning(f"No active gitingest operation for repo: {repo_url}")
                return False
            
            operation_id = self.active_operations[repo_url]
            
            # Calculate progress
            progress_percentage = (files_processed / total_files * 100) if total_files > 0 else 0
            
            # Create progress message
            if current_file:
                message = f"Processing {current_file} ({files_processed}/{total_files} files)"
            else:
                message = f"Processed {files_processed}/{total_files} files"
            
            # Create progress details
            details = {
                "files_processed": files_processed,
                "total_files": total_files,
                "progress_percentage": progress_percentage,
                "stage": stage
            }
            
            if current_file:
                details["current_file"] = current_file
            if bytes_processed:
                details["bytes_processed"] = bytes_processed
            
            # Update progress
            success = await self.operation_tracker.update_progress(
                operation_id=operation_id,
                current=files_processed,
                message=message,
                details=details
            )
            
            # Update metrics
            if bytes_processed:
                await self.operation_tracker.update_metrics(
                    operation_id=operation_id,
                    bytes_processed=bytes_processed,
                    files_processed=1  # Increment by 1 for this update
                )
            
            logger.debug(
                "GitIngest progress updated",
                operation_id=operation_id,
                repo_url=repo_url,
                files_processed=files_processed,
                total_files=total_files,
                progress_percentage=progress_percentage
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating gitingest progress: {e}")
            return False
    
    async def complete_gitingest_operation(
        self,
        repo_url: str,
        result: Optional[Dict[str, Any]] = None,
        cache_size: Optional[str] = None,
        processing_time: Optional[float] = None
    ) -> bool:
        """
        Mark a gitingest operation as completed.
        
        Args:
            repo_url: Repository URL
            result: Optional result data
            cache_size: Optional cache size information
            processing_time: Optional processing time in seconds
            
        Returns:
            bool: True if completion was successful
        """
        try:
            if repo_url not in self.active_operations:
                logger.warning(f"No active gitingest operation for repo: {repo_url}")
                return False
            
            operation_id = self.active_operations[repo_url]
            
            # Prepare result data
            operation_result = result or {}
            if cache_size:
                operation_result["cache_size"] = cache_size
            if processing_time:
                operation_result["processing_time"] = processing_time
            
            # Create summary message
            repo_name = repo_url.split('/')[-1] if '/' in repo_url else repo_url
            summary = f"Successfully mapped {repo_name} codebase"
            if cache_size:
                summary += f" (Cache size: {cache_size})"
            
            # Complete operation
            success = await self.operation_tracker.complete_operation(
                operation_id=operation_id,
                result=operation_result,
                summary=summary
            )
            
            # Remove from active operations
            del self.active_operations[repo_url]
            
            logger.info(
                "GitIngest operation completed",
                operation_id=operation_id,
                repo_url=repo_url,
                cache_size=cache_size,
                processing_time=processing_time
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error completing gitingest operation: {e}")
            return False
    
    async def fail_gitingest_operation(
        self,
        repo_url: str,
        error: str,
        error_details: Optional[Dict[str, Any]] = None,
        is_recoverable: bool = True
    ) -> bool:
        """
        Mark a gitingest operation as failed.
        
        Args:
            repo_url: Repository URL
            error: Error message
            error_details: Optional error details
            is_recoverable: Whether the error is recoverable
            
        Returns:
            bool: True if failure was recorded successfully
        """
        try:
            if repo_url not in self.active_operations:
                logger.warning(f"No active gitingest operation for repo: {repo_url}")
                return False
            
            operation_id = self.active_operations[repo_url]
            
            # Fail operation
            success = await self.operation_tracker.fail_operation(
                operation_id=operation_id,
                error=error,
                error_details=error_details,
                is_recoverable=is_recoverable
            )
            
            # Remove from active operations
            del self.active_operations[repo_url]
            
            logger.error(
                "GitIngest operation failed",
                operation_id=operation_id,
                repo_url=repo_url,
                error=error,
                is_recoverable=is_recoverable
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error failing gitingest operation: {e}")
            return False
    
    async def get_gitingest_status(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a gitingest operation.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Optional[Dict]: Operation status or None if not found
        """
        if repo_url not in self.active_operations:
            return None
        
        operation_id = self.active_operations[repo_url]
        return self.operation_tracker.get_operation_status(operation_id)
    
    def is_gitingest_active(self, repo_url: str) -> bool:
        """
        Check if gitingest is currently active for a repository.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            bool: True if gitingest is active
        """
        return repo_url in self.active_operations
    
    async def cancel_gitingest_operation(self, repo_url: str) -> bool:
        """
        Cancel an active gitingest operation.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            bool: True if cancellation was successful
        """
        try:
            if repo_url not in self.active_operations:
                return False
            
            operation_id = self.active_operations[repo_url]
            
            # Mark operation as cancelled (using fail with specific error)
            success = await self.operation_tracker.fail_operation(
                operation_id=operation_id,
                error="Operation cancelled by user",
                error_details={"cancelled_at": datetime.now().isoformat()},
                is_recoverable=False
            )
            
            # Remove from active operations
            del self.active_operations[repo_url]
            
            logger.info(
                "GitIngest operation cancelled",
                operation_id=operation_id,
                repo_url=repo_url
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling gitingest operation: {e}")
            return False
    
    def get_active_gitingest_operations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active gitingest operations.
        
        Returns:
            Dict: Mapping of repo_url to operation status
        """
        active_ops = {}
        for repo_url, operation_id in self.active_operations.items():
            status = self.operation_tracker.get_operation_status(operation_id)
            if status:
                active_ops[repo_url] = status
        return active_ops


# Global instance
_gitingest_integration: Optional[GitIngestStatusIntegration] = None


def get_gitingest_status_integration() -> GitIngestStatusIntegration:
    """Get the global gitingest status integration instance."""
    global _gitingest_integration
    if _gitingest_integration is None:
        _gitingest_integration = GitIngestStatusIntegration()
    return _gitingest_integration