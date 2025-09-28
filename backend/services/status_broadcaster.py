"""
Status Broadcasting System

Provides real-time status updates for backend operations including gitingest processing,
Redis cache operations, and other system activities. Implements WebSocket-based broadcasting
to provide transparency into backend processes.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Set, Optional, Any, List
from enum import Enum

import structlog
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

logger = structlog.get_logger(__name__)


class OperationType(str, Enum):
    """Types of operations that can be tracked and broadcast."""
    GITINGEST = "gitingest"
    REDIS_CACHE = "redis_cache"
    API_CALL = "api_call"
    FILE_PROCESSING = "file_processing"
    CONTEXT_BUILDING = "context_building"
    AI_PROCESSING = "ai_processing"
    SESSION_MANAGEMENT = "session_management"
    ERROR_HANDLING = "error_handling"


class OperationStatus(str, Enum):
    """Status of operations."""
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StatusMessageType(str, Enum):
    """Types of status messages."""
    OPERATION_START = "operation_start"
    OPERATION_PROGRESS = "operation_progress"
    OPERATION_COMPLETE = "operation_complete"
    OPERATION_ERROR = "operation_error"
    SYSTEM_STATUS = "system_status"
    CONNECTION_STATUS = "connection_status"


class StatusBroadcaster:
    """
    WebSocket-based status broadcaster for real-time backend operation visibility.
    
    Provides methods for broadcasting status updates, progress indicators, and error
    messages to connected clients. Manages WebSocket connections and ensures reliable
    message delivery.
    """
    
    def __init__(self):
        # Active WebSocket connections: connection_id -> WebSocket
        self.connections: Dict[str, WebSocket] = {}
        
        # Session-based connections: session_id -> set of connection_ids
        self.session_connections: Dict[str, Set[str]] = {}
        
        # User-based connections: user_id -> set of connection_ids
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Connection metadata: connection_id -> metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Active operations: operation_id -> operation info
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        
        # Operation subscribers: operation_id -> set of connection_ids
        self.operation_subscribers: Dict[str, Set[str]] = {}
    
    async def add_connection(
        self,
        websocket: WebSocket,
        connection_id: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Add a WebSocket connection to the broadcaster.
        
        Args:
            websocket: The WebSocket connection
            connection_id: Unique identifier for the connection
            session_id: Optional session ID to associate with the connection
            user_id: Optional user ID to associate with the connection
            
        Returns:
            bool: True if connection was added successfully
        """
        try:
            # Store the connection
            self.connections[connection_id] = websocket
            
            # Associate with session
            if session_id:
                if session_id not in self.session_connections:
                    self.session_connections[session_id] = set()
                self.session_connections[session_id].add(connection_id)
            
            # Associate with user
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)
            
            # Store metadata
            self.connection_metadata[connection_id] = {
                "session_id": session_id,
                "user_id": user_id,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "message_count": 0,
                "subscribed_operations": set()
            }
            
            logger.info(
                "Status broadcaster connection added",
                connection_id=connection_id,
                session_id=session_id,
                user_id=user_id
            )
            
            # Send connection confirmation
            await self._send_to_connection(connection_id, {
                "type": StatusMessageType.CONNECTION_STATUS,
                "status": "connected",
                "connection_id": connection_id,
                "session_id": session_id,
                "user_id": user_id
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding status broadcaster connection: {e}")
            return False
    
    def remove_connection(self, connection_id: str):
        """
        Remove a WebSocket connection from the broadcaster.
        
        Args:
            connection_id: The connection ID to remove
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        session_id = metadata.get("session_id")
        user_id = metadata.get("user_id")
        
        # Remove from connections
        if connection_id in self.connections:
            del self.connections[connection_id]
        
        # Remove from session connections
        if session_id and session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from operation subscriptions
        subscribed_operations = metadata.get("subscribed_operations", set())
        for operation_id in subscribed_operations:
            if operation_id in self.operation_subscribers:
                self.operation_subscribers[operation_id].discard(connection_id)
                if not self.operation_subscribers[operation_id]:
                    del self.operation_subscribers[operation_id]
        
        # Remove metadata
        del self.connection_metadata[connection_id]
        
        logger.info(
            "Status broadcaster connection removed",
            connection_id=connection_id,
            session_id=session_id,
            user_id=user_id
        )
    
    async def broadcast_operation_start(
        self,
        operation_id: str,
        operation_type: OperationType,
        description: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Broadcast the start of a backend operation.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation being started
            description: Human-readable description of the operation
            session_id: Optional session ID to target specific session
            user_id: Optional user ID to target specific user
            metadata: Optional additional metadata about the operation
            
        Returns:
            bool: True if broadcast was successful
        """
        try:
            # Store operation info
            self.active_operations[operation_id] = {
                "operation_id": operation_id,
                "operation_type": operation_type,
                "description": description,
                "status": OperationStatus.STARTING,
                "started_at": datetime.now(),
                "progress": 0.0,
                "metadata": metadata or {}
            }
            
            # Create status message
            message = {
                "type": StatusMessageType.OPERATION_START,
                "operation_id": operation_id,
                "operation_type": operation_type,
                "description": description,
                "status": OperationStatus.STARTING,
                "progress": 0.0,
                "metadata": metadata or {}
            }
            
            # Broadcast to appropriate connections
            success = await self._broadcast_message(message, session_id, user_id)
            
            logger.info(
                "Operation start broadcasted",
                operation_id=operation_id,
                operation_type=operation_type,
                description=description,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error broadcasting operation start: {e}")
            return False
    
    async def broadcast_operation_progress(
        self,
        operation_id: str,
        progress: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Broadcast progress update for an ongoing operation.
        
        Args:
            operation_id: The operation ID
            progress: Progress as a float between 0.0 and 1.0
            message: Progress message to display
            details: Optional additional details about the progress
            
        Returns:
            bool: True if broadcast was successful
        """
        try:
            if operation_id not in self.active_operations:
                logger.warning(f"Progress update for unknown operation: {operation_id}")
                return False
            
            # Update operation info
            operation = self.active_operations[operation_id]
            operation["progress"] = max(0.0, min(1.0, progress))
            operation["status"] = OperationStatus.IN_PROGRESS
            operation["last_update"] = datetime.now()
            
            # Create progress message
            status_message = {
                "type": StatusMessageType.OPERATION_PROGRESS,
                "operation_id": operation_id,
                "operation_type": operation["operation_type"],
                "description": operation["description"],
                "progress": operation["progress"],
                "progress_message": message,
                "status": OperationStatus.IN_PROGRESS,
                "details": details or {}
            }
            
            # Broadcast to subscribers
            success = await self._broadcast_to_operation_subscribers(operation_id, status_message)
            
            logger.debug(
                "Operation progress broadcasted",
                operation_id=operation_id,
                progress=progress,
                message=message,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error broadcasting operation progress: {e}")
            return False
    
    async def broadcast_operation_complete(
        self,
        operation_id: str,
        result: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None
    ) -> bool:
        """
        Broadcast completion of an operation.
        
        Args:
            operation_id: The operation ID
            result: Optional result data from the operation
            summary: Optional summary message
            
        Returns:
            bool: True if broadcast was successful
        """
        try:
            if operation_id not in self.active_operations:
                logger.warning(f"Completion update for unknown operation: {operation_id}")
                return False
            
            # Update operation info
            operation = self.active_operations[operation_id]
            operation["status"] = OperationStatus.COMPLETED
            operation["completed_at"] = datetime.now()
            operation["progress"] = 1.0
            operation["result"] = result or {}
            
            # Create completion message
            status_message = {
                "type": StatusMessageType.OPERATION_COMPLETE,
                "operation_id": operation_id,
                "operation_type": operation["operation_type"],
                "description": operation["description"],
                "status": OperationStatus.COMPLETED,
                "progress": 1.0,
                "result": result or {},
                "summary": summary or f"{operation['description']} completed successfully",
                "duration": (operation["completed_at"] - operation["started_at"]).total_seconds()
            }
            
            # Broadcast to subscribers
            success = await self._broadcast_to_operation_subscribers(operation_id, status_message)
            
            # Clean up operation after a delay
            asyncio.create_task(self._cleanup_operation(operation_id, delay=30))
            
            logger.info(
                "Operation completion broadcasted",
                operation_id=operation_id,
                summary=summary,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error broadcasting operation completion: {e}")
            return False
    
    async def broadcast_operation_error(
        self,
        operation_id: str,
        error: str,
        error_details: Optional[Dict[str, Any]] = None,
        is_recoverable: bool = False
    ) -> bool:
        """
        Broadcast an error for an operation.
        
        Args:
            operation_id: The operation ID
            error: Error message
            error_details: Optional additional error details
            is_recoverable: Whether the error is recoverable
            
        Returns:
            bool: True if broadcast was successful
        """
        try:
            if operation_id not in self.active_operations:
                logger.warning(f"Error update for unknown operation: {operation_id}")
                return False
            
            # Update operation info
            operation = self.active_operations[operation_id]
            operation["status"] = OperationStatus.FAILED
            operation["failed_at"] = datetime.now()
            operation["error"] = error
            operation["error_details"] = error_details or {}
            
            # Create error message
            status_message = {
                "type": StatusMessageType.OPERATION_ERROR,
                "operation_id": operation_id,
                "operation_type": operation["operation_type"],
                "description": operation["description"],
                "status": OperationStatus.FAILED,
                "error": error,
                "error_details": error_details or {},
                "is_recoverable": is_recoverable,
                "progress": operation.get("progress", 0.0)
            }
            
            # Broadcast to subscribers
            success = await self._broadcast_to_operation_subscribers(operation_id, status_message)
            
            # Clean up operation after a delay
            asyncio.create_task(self._cleanup_operation(operation_id, delay=60))
            
            logger.error(
                "Operation error broadcasted",
                operation_id=operation_id,
                error=error,
                is_recoverable=is_recoverable,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error broadcasting operation error: {e}")
            return False
    
    async def subscribe_to_operation(self, connection_id: str, operation_id: str) -> bool:
        """
        Subscribe a connection to receive updates for a specific operation.
        
        Args:
            connection_id: The connection ID
            operation_id: The operation ID to subscribe to
            
        Returns:
            bool: True if subscription was successful
        """
        try:
            if connection_id not in self.connection_metadata:
                return False
            
            # Add to operation subscribers
            if operation_id not in self.operation_subscribers:
                self.operation_subscribers[operation_id] = set()
            self.operation_subscribers[operation_id].add(connection_id)
            
            # Update connection metadata
            self.connection_metadata[connection_id]["subscribed_operations"].add(operation_id)
            
            # Send current operation status if it exists
            if operation_id in self.active_operations:
                operation = self.active_operations[operation_id]
                await self._send_to_connection(connection_id, {
                    "type": StatusMessageType.OPERATION_PROGRESS,
                    "operation_id": operation_id,
                    "operation_type": operation["operation_type"],
                    "description": operation["description"],
                    "status": operation["status"],
                    "progress": operation.get("progress", 0.0),
                    "subscribed": True
                })
            
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to operation: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status including active operations and connections.
        
        Returns:
            Dict containing system status information
        """
        return {
            "active_connections": len(self.connections),
            "active_sessions": len(self.session_connections),
            "active_users": len(self.user_connections),
            "active_operations": len(self.active_operations),
            "operations": {
                op_id: {
                    "operation_type": op["operation_type"],
                    "description": op["description"],
                    "status": op["status"],
                    "progress": op.get("progress", 0.0),
                    "started_at": op["started_at"].isoformat(),
                    "subscribers": len(self.operation_subscribers.get(op_id, set()))
                }
                for op_id, op in self.active_operations.items()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific connection."""
        if connection_id not in self.connections:
            return False
        
        websocket = self.connections[connection_id]
        if websocket.client_state != WebSocketState.CONNECTED:
            return False
        
        try:
            # Add timestamp and message ID
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            if "message_id" not in message:
                message["message_id"] = str(uuid.uuid4())
            
            await websocket.send_json(message)
            
            # Update message count
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["message_count"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending status message: {e}")
            return False
    
    async def _broadcast_message(
        self,
        message: Dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Broadcast a message to appropriate connections."""
        success = False
        
        if session_id and session_id in self.session_connections:
            # Broadcast to session connections
            for connection_id in list(self.session_connections[session_id]):
                if await self._send_to_connection(connection_id, message):
                    success = True
        elif user_id and user_id in self.user_connections:
            # Broadcast to user connections
            for connection_id in list(self.user_connections[user_id]):
                if await self._send_to_connection(connection_id, message):
                    success = True
        else:
            # Broadcast to all connections
            for connection_id in list(self.connections.keys()):
                if await self._send_to_connection(connection_id, message):
                    success = True
        
        return success
    
    async def _broadcast_to_operation_subscribers(
        self,
        operation_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """Broadcast a message to all subscribers of an operation."""
        if operation_id not in self.operation_subscribers:
            return False
        
        success = False
        for connection_id in list(self.operation_subscribers[operation_id]):
            if await self._send_to_connection(connection_id, message):
                success = True
        
        return success
    
    async def _cleanup_operation(self, operation_id: str, delay: int = 30):
        """Clean up operation data after a delay."""
        await asyncio.sleep(delay)
        
        if operation_id in self.active_operations:
            del self.active_operations[operation_id]
        
        if operation_id in self.operation_subscribers:
            del self.operation_subscribers[operation_id]
        
        logger.debug(f"Cleaned up operation: {operation_id}")


# Global status broadcaster instance
_status_broadcaster: Optional[StatusBroadcaster] = None


def get_status_broadcaster() -> StatusBroadcaster:
    """Get the global status broadcaster instance."""
    global _status_broadcaster
    if _status_broadcaster is None:
        _status_broadcaster = StatusBroadcaster()
    return _status_broadcaster