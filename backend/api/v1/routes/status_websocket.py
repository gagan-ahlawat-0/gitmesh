"""
Status Broadcasting WebSocket Routes

WebSocket endpoints for real-time status updates and backend operation visibility.
Provides transparent communication about gitingest processing, Redis operations,
and other system activities.
"""

import json
import uuid
from typing import Dict, Optional, Any
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState
import structlog

try:
    # Try relative imports first (when used as module)
    from services.status_broadcaster import get_status_broadcaster, StatusMessageType
    from services.operation_tracker import get_operation_tracker
    from utils.auth_utils import jwt_handler
except ImportError:
    # Fall back to absolute imports (when used directly)
    from services.status_broadcaster import get_status_broadcaster, StatusMessageType
    from services.operation_tracker import get_operation_tracker
    from utils.auth_utils import jwt_handler

logger = structlog.get_logger(__name__)
router = APIRouter()

# Get global instances
status_broadcaster = get_status_broadcaster()
operation_tracker = get_operation_tracker()


@router.websocket("/status/ws")
async def status_websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Query(None, description="Session ID to associate with connection"),
    token: str = Query(None, description="Authentication token"),
    user_id: str = Query(None, description="User ID")
):
    """
    WebSocket endpoint for real-time status updates.
    
    Provides:
    - Real-time backend operation status
    - Progress updates for gitingest and cache operations
    - Error notifications and recovery information
    - System health and performance metrics
    """
    
    connection_id = str(uuid.uuid4())
    
    # Validate authentication
    if token:
        try:
            payload = jwt_handler.decode_token(token)
            user_id = payload.get("user_id")
        except Exception as e:
            await websocket.close(code=1008, reason="Invalid authentication token")
            return
    
    # Connect to status broadcaster
    try:
        await websocket.accept()
        
        # Add connection to status broadcaster
        success = await status_broadcaster.add_connection(
            websocket=websocket,
            connection_id=connection_id,
            session_id=session_id,
            user_id=user_id
        )
        
        if not success:
            await websocket.close(code=1011, reason="Failed to initialize status connection")
            return
        
        logger.info(
            "Status WebSocket connected",
            connection_id=connection_id,
            session_id=session_id,
            user_id=user_id
        )
        
        # Send initial system status
        system_status = await operation_tracker.get_system_status()
        await websocket.send_json({
            "type": StatusMessageType.SYSTEM_STATUS,
            "connection_id": connection_id,
            "system_status": system_status,
            "timestamp": datetime.now().isoformat()
        })
        
        # Message processing loop
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    message_id = message.get("message_id", str(uuid.uuid4()))
                    
                    # Handle different message types
                    if message_type == "heartbeat":
                        await websocket.send_json({
                            "type": "heartbeat_response",
                            "message_id": message_id,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    elif message_type == "subscribe_operation":
                        operation_id = message.get("operation_id")
                        if operation_id:
                            success = await status_broadcaster.subscribe_to_operation(
                                connection_id, operation_id
                            )
                            await websocket.send_json({
                                "type": "subscription_response",
                                "message_id": message_id,
                                "operation_id": operation_id,
                                "subscribed": success,
                                "timestamp": datetime.now().isoformat()
                            })
                    
                    elif message_type == "get_operation_status":
                        operation_id = message.get("operation_id")
                        if operation_id:
                            status = operation_tracker.get_operation_status(operation_id)
                            await websocket.send_json({
                                "type": "operation_status_response",
                                "message_id": message_id,
                                "operation_id": operation_id,
                                "status": status,
                                "timestamp": datetime.now().isoformat()
                            })
                    
                    elif message_type == "get_active_operations":
                        operations = operation_tracker.get_active_operations()
                        await websocket.send_json({
                            "type": "active_operations_response",
                            "message_id": message_id,
                            "operations": operations,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    elif message_type == "get_system_status":
                        system_status = await operation_tracker.get_system_status()
                        await websocket.send_json({
                            "type": StatusMessageType.SYSTEM_STATUS,
                            "message_id": message_id,
                            "system_status": system_status,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message_id": message_id,
                            "error": f"Unknown message type: {message_type}",
                            "timestamp": datetime.now().isoformat()
                        })
                
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    })
                
                except Exception as e:
                    logger.error(f"Error processing status WebSocket message: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Error processing message: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
        
        except WebSocketDisconnect:
            logger.info(f"Status WebSocket disconnected: {connection_id}")
        
    except Exception as e:
        logger.error(f"Status WebSocket error: {e}")
        if hasattr(websocket, 'client_state') and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011, reason="Internal server error")
    
    finally:
        # Clean up connection
        status_broadcaster.remove_connection(connection_id)


@router.get("/status/health")
async def status_service_health():
    """Health check for status broadcasting service."""
    system_status = await operation_tracker.get_system_status()
    broadcaster_status = await status_broadcaster.get_system_status()
    
    return {
        "status": "healthy",
        "operation_tracker": system_status,
        "status_broadcaster": broadcaster_status,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status/operations")
async def get_active_operations():
    """Get all currently active operations."""
    operations = operation_tracker.get_active_operations()
    return {
        "active_operations": operations,
        "count": len(operations),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status/operations/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get status of a specific operation."""
    status = operation_tracker.get_operation_status(operation_id)
    if not status:
        return {
            "error": "Operation not found",
            "operation_id": operation_id,
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "operation": status,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/status/operations/{operation_id}/subscribe")
async def subscribe_to_operation(operation_id: str, connection_id: str):
    """Subscribe a connection to receive updates for an operation."""
    success = await status_broadcaster.subscribe_to_operation(connection_id, operation_id)
    return {
        "subscribed": success,
        "operation_id": operation_id,
        "connection_id": connection_id,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status/system")
async def get_system_status():
    """Get comprehensive system status."""
    operation_status = await operation_tracker.get_system_status()
    broadcaster_status = await status_broadcaster.get_system_status()
    
    return {
        "system_status": {
            "operation_tracker": operation_status,
            "status_broadcaster": broadcaster_status,
            "healthy": True
        },
        "timestamp": datetime.now().isoformat()
    }