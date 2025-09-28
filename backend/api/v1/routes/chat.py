"""
Chat API routes using Cosmos AI Integration with Enhanced Architecture
"""
import os
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
import structlog

from .dependencies import get_current_user
from models.api.auth_models import User

# Import new architecture services
try:
    from services.status_broadcaster import get_status_broadcaster, OperationType, OperationStatus
    from services.auto_init_service import get_auto_init_service
    from services.metrics_collection_service import get_metrics_collector
    STATUS_BROADCASTING_AVAILABLE = True
except ImportError:
    STATUS_BROADCASTING_AVAILABLE = False

try:
    from services.enhanced_session_service import get_enhanced_session_service
    ENHANCED_SESSION_AVAILABLE = True
except ImportError:
    ENHANCED_SESSION_AVAILABLE = False

# Safe imports for Cosmos integration
try:
    from services.cosmos_web_wrapper import CosmosWebWrapper, COSMOS_COMPONENTS_AVAILABLE
    COSMOS_AVAILABLE = True
except ImportError:
    COSMOS_AVAILABLE = False
    COSMOS_COMPONENTS_AVAILABLE = False
    CosmosWebWrapper = None

# Cache management imports
try:
    from services.cache_management_service import create_cache_management_service
    from services.navigation_cache_manager import create_navigation_cache_manager
    CACHE_MANAGEMENT_AVAILABLE = True
except ImportError:
    CACHE_MANAGEMENT_AVAILABLE = False
    create_cache_management_service = None
    create_navigation_cache_manager = None

logger = structlog.get_logger(__name__)
router = APIRouter()

# WebSocket connection manager for real-time status updates
class ChatWebSocketManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, set] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, connection_id: str):
        await websocket.accept()
        self.connections[connection_id] = websocket
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)
        
        # Integrate with status broadcaster if available
        if STATUS_BROADCASTING_AVAILABLE:
            status_broadcaster = get_status_broadcaster()
            await status_broadcaster.add_connection(websocket, connection_id, session_id)
    
    def disconnect(self, connection_id: str, session_id: str = None):
        if connection_id in self.connections:
            del self.connections[connection_id]
        if session_id and session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        
        # Remove from status broadcaster if available
        if STATUS_BROADCASTING_AVAILABLE:
            status_broadcaster = get_status_broadcaster()
            status_broadcaster.remove_connection(connection_id)
    
    async def send_to_session(self, session_id: str, message: dict):
        if session_id not in self.session_connections:
            return False
        
        success_count = 0
        for connection_id in list(self.session_connections[session_id]):
            if connection_id in self.connections:
                websocket = self.connections[connection_id]
                if websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        await websocket.send_json(message)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error sending WebSocket message: {e}")
                        self.disconnect(connection_id, session_id)
        
        return success_count > 0

# Global WebSocket manager
ws_manager = ChatWebSocketManager()

# WebSocket endpoint for real-time chat status updates
@router.websocket("/ws/{session_id}")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = None
):
    """WebSocket endpoint for real-time chat status updates and communication."""
    connection_id = str(uuid.uuid4())
    user_id = None
    
    # Validate authentication if token provided
    if token:
        try:
            from utils.auth_utils import jwt_handler
            payload = jwt_handler.decode_token(token)
            user_id = payload.get("user_id")
        except Exception as e:
            await websocket.close(code=1008, reason="Invalid authentication token")
            return
    
    try:
        # Connect to WebSocket
        await ws_manager.connect(websocket, session_id, connection_id)
        
        # Send connection established message
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "connection_id": connection_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize auto-init service if available and trigger repository caching
        if STATUS_BROADCASTING_AVAILABLE:
            try:
                auto_init_service = get_auto_init_service()
                # This would be called when user visits /contribution/[repo] page
                # The frontend should send repository info via WebSocket message
                logger.info(f"Auto-init service available for session {session_id}")
            except Exception as e:
                logger.error(f"Error initializing auto-init service: {e}")
        
        # Keep connection alive and handle messages
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    if message_type == "heartbeat":
                        await websocket.send_json({
                            "type": "heartbeat_ack",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    elif message_type == "init_repository":
                        # Handle repository initialization request
                        await handle_repository_initialization(
                            websocket, session_id, message, user_id
                        )
                    
                    elif message_type == "get_status":
                        # Send current status
                        await websocket.send_json({
                            "type": "status_update",
                            "session_id": session_id,
                            "status": "connected",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "error": f"Unknown message type: {message_type}",
                            "timestamp": datetime.now().isoformat()
                        })
                
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    })
        
        except WebSocketDisconnect:
            ws_manager.disconnect(connection_id, session_id)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011, reason="Internal server error")
        ws_manager.disconnect(connection_id, session_id)

async def handle_repository_initialization(websocket: WebSocket, session_id: str, message: dict, user_id: str):
    """Handle repository initialization request via WebSocket."""
    try:
        repo_url = message.get("repository_url")
        if not repo_url:
            await websocket.send_json({
                "type": "error",
                "error": "Repository URL is required",
                "timestamp": datetime.now().isoformat()
            })
            return
        
        if STATUS_BROADCASTING_AVAILABLE:
            # Use auto-init service to start repository caching
            auto_init_service = get_auto_init_service()
            status_broadcaster = get_status_broadcaster()
            
            # Start repository initialization
            operation_id = str(uuid.uuid4())
            await status_broadcaster.broadcast_operation_start(
                operation_id=operation_id,
                operation_type=OperationType.GITINGEST,
                description=f"Mapping codebase: {repo_url}",
                session_id=session_id,
                metadata={"repository_url": repo_url}
            )
            
            # Trigger auto-initialization
            init_session_id = await auto_init_service.on_page_visit(repo_url, user_id or "anonymous")
            
            # Send initialization started response
            await websocket.send_json({
                "type": "repository_init_started",
                "session_id": session_id,
                "operation_id": operation_id,
                "init_session_id": init_session_id,
                "repository_url": repo_url,
                "timestamp": datetime.now().isoformat()
            })
            
            # Monitor initialization progress (this would be handled by the auto-init service)
            # The status broadcaster will send progress updates automatically
            
        else:
            await websocket.send_json({
                "type": "error",
                "error": "Auto-initialization service not available",
                "timestamp": datetime.now().isoformat()
            })
    
    except Exception as e:
        logger.error(f"Error handling repository initialization: {e}")
        await websocket.send_json({
            "type": "error",
            "error": f"Repository initialization failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

# Navigation cache management endpoints
@router.post("/navigation-cleanup")
async def handle_navigation_cleanup(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Handle cache cleanup during navigation transitions with enhanced architecture."""
    try:
        data = await request.json()
        from_page = data.get('from_page', '')
        to_page = data.get('to_page', '')
        user_id = data.get('user_id') or current_user.id
        
        # Track metrics if available
        if STATUS_BROADCASTING_AVAILABLE:
            try:
                metrics_collector = get_metrics_collector()
                operation_start = datetime.now()
            except Exception:
                metrics_collector = None
        
        # Broadcast navigation cleanup start if status broadcasting is available
        if STATUS_BROADCASTING_AVAILABLE:
            try:
                status_broadcaster = get_status_broadcaster()
                operation_id = str(uuid.uuid4())
                await status_broadcaster.broadcast_operation_start(
                    operation_id=operation_id,
                    operation_type=OperationType.REDIS_CACHE,
                    description=f"Cleaning up cache during navigation: {from_page} → {to_page}",
                    user_id=str(user_id),
                    metadata={"from_page": from_page, "to_page": to_page}
                )
            except Exception as e:
                logger.error(f"Error broadcasting navigation cleanup start: {e}")
        
        if CACHE_MANAGEMENT_AVAILABLE:
            # Create navigation cache manager
            nav_manager = create_navigation_cache_manager(user_id)
            
            # Handle navigation with automatic cleanup
            cleanup_result = nav_manager.handle_navigation(
                from_page=from_page,
                to_page=to_page
            )
            
            # Broadcast completion if available
            if STATUS_BROADCASTING_AVAILABLE:
                try:
                    await status_broadcaster.broadcast_operation_complete(
                        operation_id=operation_id,
                        result={
                            "entries_cleaned": cleanup_result.entries_cleaned,
                            "memory_freed_mb": cleanup_result.memory_freed_mb,
                            "cleanup_time_ms": cleanup_result.cleanup_time_ms
                        }
                    )
                except Exception as e:
                    logger.error(f"Error broadcasting navigation cleanup completion: {e}")
            
            # Track metrics if available
            if metrics_collector:
                try:
                    operation_end = datetime.now()
                    latency = (operation_end - operation_start).total_seconds() * 1000
                    await metrics_collector.record_request_latency(
                        session_id=session_id,
                        request_id="navigation_cleanup",
                        latency_ms=latency,
                        operation_type="navigation_cleanup"
                    )
                    await metrics_collector.track_cache_operation(
                        operation_type="cleanup",
                        cache_type="navigation",
                        success=True,
                        entries_affected=cleanup_result.entries_cleaned,
                        memory_freed_mb=cleanup_result.memory_freed_mb
                    )
                except Exception as e:
                    logger.error(f"Error tracking navigation cleanup metrics: {e}")
            
            return JSONResponse(content={
                "repository_cache_cleared": cleanup_result.repository_cache_cleared,
                "session_cache_cleared": cleanup_result.session_cache_cleared,
                "context_cache_cleared": cleanup_result.context_cache_cleared,
                "entries_cleaned": cleanup_result.entries_cleaned,
                "memory_freed_mb": cleanup_result.memory_freed_mb,
                "cleanup_time_ms": cleanup_result.cleanup_time_ms,
                "success": True
            })
        else:
            logger.warning("Cache management not available")
            return JSONResponse(content={
                "repository_cache_cleared": False,
                "session_cache_cleared": False,
                "context_cache_cleared": False,
                "entries_cleaned": 0,
                "memory_freed_mb": 0.0,
                "cleanup_time_ms": 0.0,
                "success": False,
                "error": "Cache management not available"
            })
            
    except Exception as e:
        logger.error(f"Navigation cleanup error: {e}")
        
        # Broadcast error if available
        if STATUS_BROADCASTING_AVAILABLE:
            try:
                status_broadcaster = get_status_broadcaster()
                await status_broadcaster.broadcast_operation_error(
                    operation_id=operation_id if 'operation_id' in locals() else str(uuid.uuid4()),
                    error_message=str(e),
                    error_details={"from_page": from_page, "to_page": to_page}
                )
            except Exception:
                pass
        
        return JSONResponse(
            status_code=500,
            content={
                "repository_cache_cleared": False,
                "session_cache_cleared": False,
                "context_cache_cleared": False,
                "entries_cleaned": 0,
                "memory_freed_mb": 0.0,
                "cleanup_time_ms": 0.0,
                "success": False,
                "error": str(e)
            }
        )

@router.post("/clear-cache")
async def clear_all_cache(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Clear all cache for a user."""
    try:
        data = await request.json()
        user_id = data.get('user_id') or current_user.id
        
        # logger.info(f"Clear all cache requested for user {user_id}")
        
        if CACHE_MANAGEMENT_AVAILABLE:
            # Create cache management service
            cache_service = create_cache_management_service(user_id)
            
            # Clear all user caches
            repo_cleared = cache_service.clear_user_repository_cache(user_id)
            session_cleared = cache_service.clear_user_session_cache(user_id)
            
            # Cleanup expired entries
            entries_cleaned = cache_service.cleanup_expired_caches()
            
            # Get optimization results
            optimization_results = cache_service.optimize_memory_usage()
            
            return JSONResponse(content={
                "repository_cache_cleared": repo_cleared,
                "session_cache_cleared": session_cleared,
                "entries_cleaned": entries_cleaned,
                "memory_freed_mb": optimization_results.get('memory_saved_mb', 0.0),
                "optimization_results": optimization_results,
                "success": True
            })
        else:
            logger.warning("Cache management not available")
            return JSONResponse(content={
                "repository_cache_cleared": False,
                "session_cache_cleared": False,
                "entries_cleaned": 0,
                "memory_freed_mb": 0.0,
                "success": False,
                "error": "Cache management not available"
            })
            
    except Exception as e:
        logger.error(f"Clear all cache error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "repository_cache_cleared": False,
                "session_cache_cleared": False,
                "entries_cleaned": 0,
                "memory_freed_mb": 0.0,
                "success": False,
                "error": str(e)
            }
        )

@router.get("/cache-stats")
async def get_cache_stats(
    user_id: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get cache statistics for a user."""
    try:
        target_user_id = user_id or current_user.id
        
        if CACHE_MANAGEMENT_AVAILABLE:
            # Create cache management service
            cache_service = create_cache_management_service(target_user_id)
            
            # Get cache statistics
            cache_stats = cache_service.get_cache_stats()
            
            # Create navigation manager for session stats
            nav_manager = create_navigation_cache_manager(target_user_id)
            session_stats = nav_manager.get_session_stats()
            
            return JSONResponse(content={
                "cache_stats": {
                    "total_keys": cache_stats.total_keys,
                    "memory_usage_mb": cache_stats.memory_usage_mb,
                    "hit_rate": cache_stats.hit_rate,
                    "miss_rate": cache_stats.miss_rate,
                    "expired_keys": cache_stats.expired_keys,
                    "user_cache_count": cache_stats.user_cache_count,
                    "repository_cache_count": cache_stats.repository_cache_count,
                    "session_cache_count": cache_stats.session_cache_count,
                    "last_cleanup": cache_stats.last_cleanup.isoformat() if cache_stats.last_cleanup else None
                },
                "session_stats": session_stats,
                "success": True
            })
        else:
            logger.warning("Cache management not available")
            return JSONResponse(content={
                "cache_stats": {},
                "session_stats": {},
                "success": False,
                "error": "Cache management not available"
            })
            
    except Exception as e:
        logger.error(f"Get cache stats error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "cache_stats": {},
                "session_stats": {},
                "success": False,
                "error": str(e)
            }
        )

@router.get("/cache-health")
async def get_cache_health(
    user_id: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get cache health status."""
    try:
        target_user_id = user_id or current_user.id
        
        if CACHE_MANAGEMENT_AVAILABLE:
            # Create cache management service
            cache_service = create_cache_management_service(target_user_id)
            
            # Get health status
            health_status = cache_service.health_check()
            
            return JSONResponse(content={
                "health_status": {
                    "is_healthy": health_status.is_healthy,
                    "connection_status": health_status.connection_status,
                    "memory_usage_percent": health_status.memory_usage_percent,
                    "response_time_ms": health_status.response_time_ms,
                    "error_count": health_status.error_count,
                    "last_error": health_status.last_error,
                    "uptime_seconds": health_status.uptime_seconds
                },
                "success": True
            })
        else:
            logger.warning("Cache management not available")
            return JSONResponse(content={
                "health_status": {
                    "is_healthy": False,
                    "connection_status": "unavailable",
                    "memory_usage_percent": 0.0,
                    "response_time_ms": 0.0,
                    "error_count": 0,
                    "last_error": "Cache management not available",
                    "uptime_seconds": 0
                },
                "success": False,
                "error": "Cache management not available"
            })
            
    except Exception as e:
        logger.error(f"Get cache health error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "health_status": {
                    "is_healthy": False,
                    "connection_status": "error",
                    "memory_usage_percent": 0.0,
                    "response_time_ms": 0.0,
                    "error_count": 1,
                    "last_error": str(e),
                    "uptime_seconds": 0
                },
                "success": False,
                "error": str(e)
            }
        )

@router.post("/optimize-cache")
async def optimize_cache(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Optimize cache memory usage."""
    try:
        data = await request.json()
        user_id = data.get('user_id') or current_user.id
        
        # logger.info(f"Cache optimization requested for user {user_id}")
        
        if CACHE_MANAGEMENT_AVAILABLE:
            # Create cache management service
            cache_service = create_cache_management_service(user_id)
            
            # Optimize memory usage
            optimization_results = cache_service.optimize_memory_usage()
            
            return JSONResponse(content={
                "optimization_results": optimization_results,
                "success": True
            })
        else:
            logger.warning("Cache management not available")
            return JSONResponse(content={
                "optimization_results": {
                    "cleaned_entries": 0,
                    "memory_saved_mb": 0.0,
                    "error": "Cache management not available"
                },
                "success": False,
                "error": "Cache management not available"
            })
            
    except Exception as e:
        logger.error(f"Cache optimization error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "optimization_results": {
                    "cleaned_entries": 0,
                    "memory_saved_mb": 0.0,
                    "error": str(e)
                },
                "success": False,
                "error": str(e)
            }
        )

@router.get("/scheduler-status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """Get cache cleanup scheduler status."""
    try:
        # Import scheduler
        try:
            from services.cache_cleanup_scheduler import get_cache_cleanup_scheduler
            scheduler = get_cache_cleanup_scheduler()
            
            # Get scheduler stats
            stats = scheduler.get_scheduler_stats()
            job_history = scheduler.get_job_history(limit=10)
            
            return JSONResponse(content={
                "scheduler_stats": stats,
                "job_history": job_history,
                "success": True
            })
            
        except ImportError:
            return JSONResponse(content={
                "scheduler_stats": {
                    "is_running": False,
                    "error": "Scheduler not available"
                },
                "job_history": [],
                "success": False,
                "error": "Cache cleanup scheduler not available"
            })
            
    except Exception as e:
        logger.error(f"Get scheduler status error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "scheduler_stats": {
                    "is_running": False,
                    "error": str(e)
                },
                "job_history": [],
                "success": False,
                "error": str(e)
            }
        )

# Redis-based session storage for persistence
import redis
import json
from datetime import timedelta
import time

# Initialize Redis connection for session storage with optimized settings
try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Use environment variables for timeout settings
    socket_timeout = float(os.getenv('REDIS_SOCKET_TIMEOUT', '10.0'))  # Increased from 5.0
    connect_timeout = float(os.getenv('REDIS_CONNECT_TIMEOUT', '10.0'))  # Increased from 5.0
    max_connections = int(os.getenv('REDIS_MAX_CONNECTIONS', '20'))
    
    # Create connection pool for better performance
    connection_pool = redis.ConnectionPool.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=socket_timeout,
        socket_connect_timeout=connect_timeout,
        retry_on_timeout=True,
        health_check_interval=30,
        max_connections=max_connections,
        socket_keepalive=True,
        socket_keepalive_options={}
    )
    
    session_redis = redis.Redis(connection_pool=connection_pool)
    
    # Test the connection
    session_redis.ping()
    REDIS_AVAILABLE = True
    # logger.info(f"Redis session storage initialized with pool (timeout: {socket_timeout}s, max_conn: {max_connections})")
except Exception as e:
    logger.warning(f"Redis not available for session storage: {e}")
    REDIS_AVAILABLE = False
    # Fallback to in-memory storage
    chat_sessions: Dict[str, Dict[str, Any]] = {}
    chat_messages: Dict[str, List[Dict[str, Any]]] = {}

# Circuit breaker for Redis operations
class RedisCircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self):
        if self.state == 'CLOSED':
            return True
        elif self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'

redis_circuit_breaker = RedisCircuitBreaker()

# Session management helper functions
def get_session_key(session_id: str) -> str:
    """Get Redis key for session data."""
    return f"chat_session:{session_id}"

def get_messages_key(session_id: str) -> str:
    """Get Redis key for session messages."""
    return f"chat_messages:{session_id}"

def get_user_sessions_key(user_id: str) -> str:
    """Get Redis key for user's session list."""
    return f"user_sessions:{user_id}"

def store_session(session_id: str, session_data: Dict[str, Any], ttl_hours: int = 24):
    """Store session data with TTL."""
    if REDIS_AVAILABLE and redis_circuit_breaker.can_execute():
        try:
            session_redis.setex(
                get_session_key(session_id),
                timedelta(hours=ttl_hours),
                json.dumps(session_data)
            )
            # Add to user's session list
            user_id = session_data.get('userId')
            if user_id:
                session_redis.sadd(get_user_sessions_key(user_id), session_id)
                session_redis.expire(get_user_sessions_key(user_id), timedelta(hours=ttl_hours))
            
            redis_circuit_breaker.record_success()
        except (redis.TimeoutError, redis.ConnectionError) as e:
            logger.error(f"Redis timeout/connection error storing session {session_id}: {e}")
            redis_circuit_breaker.record_failure()
            # Fallback to in-memory storage for this session
            chat_sessions[session_id] = session_data
        except Exception as e:
            logger.error(f"Error storing session {session_id}: {e}")
            redis_circuit_breaker.record_failure()
            # Fallback to in-memory storage for this session
            chat_sessions[session_id] = session_data
    else:
        # Use in-memory storage when Redis is unavailable or circuit is open
        chat_sessions[session_id] = session_data

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data."""
    if REDIS_AVAILABLE and redis_circuit_breaker.can_execute():
        try:
            data = session_redis.get(get_session_key(session_id))
            redis_circuit_breaker.record_success()
            return json.loads(data) if data else chat_sessions.get(session_id)
        except (redis.TimeoutError, redis.ConnectionError) as e:
            logger.error(f"Redis timeout/connection error getting session {session_id}: {e}")
            redis_circuit_breaker.record_failure()
            # Try fallback to in-memory storage
            return chat_sessions.get(session_id)
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            redis_circuit_breaker.record_failure()
            # Try fallback to in-memory storage
            return chat_sessions.get(session_id)
    else:
        return chat_sessions.get(session_id)

def store_messages(session_id: str, messages: List[Dict[str, Any]], ttl_hours: int = 24):
    """Store session messages with TTL."""
    if REDIS_AVAILABLE and redis_circuit_breaker.can_execute():
        try:
            session_redis.setex(
                get_messages_key(session_id),
                timedelta(hours=ttl_hours),
                json.dumps(messages)
            )
            redis_circuit_breaker.record_success()
        except (redis.TimeoutError, redis.ConnectionError) as e:
            logger.error(f"Redis timeout/connection error storing messages for {session_id}: {e}")
            redis_circuit_breaker.record_failure()
            # Fallback to in-memory storage
            chat_messages[session_id] = messages
        except Exception as e:
            logger.error(f"Error storing messages for {session_id}: {e}")
            redis_circuit_breaker.record_failure()
            # Fallback to in-memory storage
            chat_messages[session_id] = messages
    else:
        chat_messages[session_id] = messages

def get_messages(session_id: str) -> List[Dict[str, Any]]:
    """Get session messages."""
    if REDIS_AVAILABLE and redis_circuit_breaker.can_execute():
        try:
            data = session_redis.get(get_messages_key(session_id))
            redis_circuit_breaker.record_success()
            return json.loads(data) if data else chat_messages.get(session_id, [])
        except (redis.TimeoutError, redis.ConnectionError) as e:
            logger.error(f"Redis timeout/connection error getting messages for {session_id}: {e}")
            redis_circuit_breaker.record_failure()
            # Try fallback to in-memory storage
            return chat_messages.get(session_id, [])
        except Exception as e:
            logger.error(f"Error getting messages for {session_id}: {e}")
            redis_circuit_breaker.record_failure()
            # Try fallback to in-memory storage
            return chat_messages.get(session_id, [])
    else:
        return chat_messages.get(session_id, [])

def delete_session(session_id: str, user_id: str = None):
    """Delete session and its messages."""
    if REDIS_AVAILABLE:
        try:
            session_redis.delete(get_session_key(session_id))
            session_redis.delete(get_messages_key(session_id))
            if user_id:
                session_redis.srem(get_user_sessions_key(user_id), session_id)
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
    else:
        chat_sessions.pop(session_id, None)
        chat_messages.pop(session_id, None)

def get_user_sessions(user_id: str) -> List[str]:
    """Get all session IDs for a user."""
    if REDIS_AVAILABLE:
        try:
            return list(session_redis.smembers(get_user_sessions_key(user_id)))
        except Exception as e:
            logger.error(f"Error getting user sessions for {user_id}: {e}")
            return []
    else:
        return [sid for sid, session in chat_sessions.items() if session.get('userId') == user_id]

class ChatCosmosService:
    """Service to bridge chat interface to Cosmos AI system"""
    
    def __init__(self):
        if COSMOS_AVAILABLE:
            self.cosmos_available = True
        else:
            self.cosmos_available = False
    

    
    async def create_session(self, user_id: str, title: str = None, repository_id: str = None, branch: str = None, repository_url: str = None):
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        
        # Auto-detect repository context if not provided
        if not repository_id and not repository_url:
            # This would typically come from the current user's repository context
            # For now, we'll use a default that can be overridden by the frontend
            repository_id = "default"
            repository_url = None
        
        session = {
            "id": session_id,
            "title": title or f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "repositoryId": repository_id,
            "repositoryUrl": repository_url,
            "branch": branch or "main",
            "messages": [],
            "selectedFiles": [],
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat(),
            "userId": user_id,
            "cosmosReady": self.cosmos_available and COSMOS_AVAILABLE
        }
        
        # Store session with 24-hour TTL
        store_session(session_id, session, ttl_hours=24)
        store_messages(session_id, [], ttl_hours=24)
        
        # Initialize Cosmos session if available
        if self.cosmos_available and COSMOS_AVAILABLE:
            try:
                # Note: Cosmos wrapper will be created per message for now
                # In the future, we can implement session-based wrapper caching
                # logger.info(f"Cosmos is available for session {session_id}")
                pass
            except Exception as e:
                logger.error(f"Error checking Cosmos availability: {e}")
        
        return session
    
    async def get_session(self, session_id: str, user_id: str):
        """Get a chat session"""
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Include messages
        session["messages"] = get_messages(session_id)
        return session
    
    async def send_message(self, session_id: str, user_id: str, message: str, context: Dict[str, Any] = None, model_name: str = "gpt-4o-mini"):
        """Send a message and get AI response via Cosmos with enhanced architecture integration"""
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Start metrics tracking if available
        request_start = datetime.now()
        operation_id = str(uuid.uuid4())
        
        if STATUS_BROADCASTING_AVAILABLE:
            try:
                metrics_collector = get_metrics_collector()
                status_broadcaster = get_status_broadcaster()
                
                # Broadcast message processing start
                await status_broadcaster.broadcast_operation_start(
                    operation_id=operation_id,
                    operation_type=OperationType.AI_PROCESSING,
                    description=f"Processing message with {model_name}",
                    session_id=session_id,
                    user_id=user_id,
                    metadata={"model": model_name, "message_length": len(message)}
                )
            except Exception as e:
                logger.error(f"Error starting status broadcast: {e}")
                metrics_collector = None
                status_broadcaster = None
        else:
            metrics_collector = None
            status_broadcaster = None
        
        # Debug: Log the incoming request
        logger.info(f"Chat context received: {context}")
        if context and context.get("files"):
            files = context.get("files", [])
            logger.info(f"Files in context: {len(files)} files")
            for i, file in enumerate(files[:3]):  # Log first 3 files
                logger.info(f"  File {i+1}: {file.get('path', 'unknown')} - content length: {len(file.get('content', ''))}")
        
        # Create user message
        user_message = {
            "id": str(uuid.uuid4()),
            "type": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "files": [],
            "model": model_name
        }
        
        # Add user message to history
        messages = get_messages(session_id)
        messages.append(user_message)
        store_messages(session_id, messages, ttl_hours=24)
        
        # Broadcast progress update
        if status_broadcaster:
            try:
                await status_broadcaster.broadcast_operation_progress(
                    operation_id=operation_id,
                    progress=0.2,
                    message="Message stored, initializing AI processing..."
                )
            except Exception as e:
                logger.error(f"Error broadcasting progress: {e}")
        
        # Generate AI response via Cosmos with full AI capabilities
        confidence = 0.8
        knowledge_used = 0
        sources = []
        model_used = model_name
        
        try:
            if self.cosmos_available and COSMOS_AVAILABLE:
                # Broadcast AI processing start
                if status_broadcaster:
                    try:
                        await status_broadcaster.broadcast_operation_progress(
                            operation_id=operation_id,
                            progress=0.4,
                            message="Initializing Cosmos AI system..."
                        )
                    except Exception as e:
                        logger.error(f"Error broadcasting AI processing start: {e}")
                # Initialize Cosmos configuration first
                try:
                    from integrations.cosmos.v1.cosmos.config import initialize_configuration
                    initialize_configuration()
                    logger.info("Cosmos configuration initialized successfully")
                    
                    # Broadcast configuration success
                    if status_broadcaster:
                        await status_broadcaster.broadcast_operation_progress(
                            operation_id=operation_id,
                            progress=0.5,
                            message="Cosmos configuration initialized"
                        )
                except Exception as e:
                    logger.warning(f"Could not initialize Cosmos configuration: {e}")
                    if status_broadcaster:
                        await status_broadcaster.broadcast_operation_progress(
                            operation_id=operation_id,
                            progress=0.5,
                            message=f"Configuration warning: {str(e)}"
                        )
                
                # Import optimized services with fallback
                try:
                    from middleware.optimized_repo_middleware import get_repo_middleware
                    from services.optimized_redis_repo_manager import OptimizedRedisRepoManager
                    optimized_system_available = True
                    logger.info("Using full optimized repository system")
                except ImportError as e:
                    logger.warning(f"Full optimized system not available: {e}")
                    # Fallback to simple optimized system
                    from services.simple_optimized_repo_service import get_simple_optimized_repo_service
                    from services.redis_repo_manager import RedisRepoManager
                    optimized_system_available = False
                    logger.info("Using simple optimized repository system")
                
                # Build enhanced context with repository information
                enhanced_context = context or {}
                
                # Import repository validation service
                from services.repository_validation_service import repository_validation_service
                
                # Import repository context detection service
                from services.repository_context_detection_service import repository_context_service
                
                # Detect repository context automatically from /contribution page
                repository_context = None
                repository_url = None
                
                # Build page context from available information
                page_context = {
                    'repository_id': context.get('repository_id') if context else None,
                    'repository_url': context.get('repository_url') if context else None,
                    'branch': context.get('branch') if context else None,
                    'owner': context.get('owner') if context else None,
                    'repo': context.get('repo') if context else None,
                    'current_url': '/contribution/chat',  # Assume we're on the chat page
                }
                
                # Add repository info from session
                if session.get("repositoryId"):
                    page_context['repository_id'] = session["repositoryId"]
                if session.get("repositoryUrl"):
                    page_context['repository_url'] = session["repositoryUrl"]
                if session.get("branch"):
                    page_context['branch'] = session["branch"]
                
                # Add repository info from files context
                if context and context.get("files"):
                    files = context["files"]
                    if files and len(files) > 0:
                        first_file = files[0]
                        if isinstance(first_file, dict):
                            if first_file.get("owner") and first_file.get("repo"):
                                page_context['owner'] = first_file.get("owner")
                                page_context['repo'] = first_file.get("repo")
                
                # Detect repository context
                if status_broadcaster:
                    await status_broadcaster.broadcast_operation_progress(
                        operation_id=operation_id,
                        progress=0.6,
                        message="Detecting repository context..."
                    )
                
                repository_context = repository_context_service.detect_repository_context(page_context)
                
                if repository_context:
                    repository_url = repository_context.url
                    logger.info(f"Repository context detected: {repository_url} (branch: {repository_context.branch})")
                    
                    if status_broadcaster:
                        await status_broadcaster.broadcast_operation_progress(
                            operation_id=operation_id,
                            progress=0.7,
                            message=f"Repository context detected: {repository_context.name}"
                        )
                    
                    # Validate repository size before processing
                    repository_context = await repository_context_service.validate_repository_size(
                        repository_context, user_id
                    )
                    
                    if repository_context.validation_status == "too_large":
                        # Repository is too large - block chat
                        logger.warning(f"Repository too large: {repository_context.size_mb}MB")
                        
                        assistant_content = f"🚫 **Repository Too Large**\n\n{repository_context.error_message}\n\nPlease try with a smaller repository (under 150MB) or upgrade your plan for larger repository support."
                        model_used = "validation_blocked"
                        confidence = 0.0
                        knowledge_used = 0
                        sources = []
                        
                        # Create assistant message with error
                        assistant_message = {
                            "id": str(uuid.uuid4()),
                            "type": "assistant", 
                            "content": assistant_content,
                            "timestamp": datetime.now().isoformat(),
                            "files": [],
                            "model": model_used,
                            "metadata": {
                                "confidence": confidence,
                                "knowledge_used": knowledge_used,
                                "sources_count": len(sources),
                                "cosmos_available": False,
                                "validation_error": "repository_too_large",
                                "repository_blocked": True,
                                "size_mb": repository_context.size_mb
                            }
                        }
                        
                        # Add assistant message to history
                        messages = get_messages(session_id)
                        messages.append(assistant_message)
                        store_messages(session_id, messages, ttl_hours=24)
                        
                        # Update session timestamp
                        session["updatedAt"] = datetime.now().isoformat()
                        session["messages"] = messages
                        store_session(session_id, session, ttl_hours=24)
                        
                        return {
                            "userMessage": user_message,
                            "assistantMessage": assistant_message,
                            "session": session
                        }
                    
                    elif repository_context.validation_status in ["invalid", "rate_limited"]:
                        # Repository validation failed or rate limited
                        logger.warning(f"Repository validation failed: {repository_context.error_message}")
                        
                        assistant_content = repository_context.error_message or "Repository validation failed. Please try with a different repository."
                        model_used = "validation_blocked"
                        confidence = 0.0
                        knowledge_used = 0
                        sources = []
                        
                        # Create assistant message with error
                        assistant_message = {
                            "id": str(uuid.uuid4()),
                            "type": "assistant", 
                            "content": assistant_content,
                            "timestamp": datetime.now().isoformat(),
                            "files": [],
                            "model": model_used,
                            "metadata": {
                                "confidence": confidence,
                                "knowledge_used": knowledge_used,
                                "sources_count": len(sources),
                                "cosmos_available": False,
                                "validation_error": "repository_invalid",
                                "repository_blocked": True,
                                "size_mb": repository_context.size_mb
                            }
                        }
                        
                        # Add assistant message to history
                        messages = get_messages(session_id)
                        messages.append(assistant_message)
                        store_messages(session_id, messages, ttl_hours=24)
                        
                        # Update session timestamp
                        session["updatedAt"] = datetime.now().isoformat()
                        session["messages"] = messages
                        store_session(session_id, session, ttl_hours=24)
                        
                        return {
                            "userMessage": user_message,
                            "assistantMessage": assistant_message,
                            "session": session
                        }
                    
                    # Repository validation passed - ensure it's cached
                    logger.info(f"Repository validation passed: {repository_context.size_mb:.2f}MB" if repository_context.size_mb else "Repository validation passed")
                    
                    # Ensure repository data is cached in Redis
                    cache_success = repository_context_service.ensure_repository_cached(
                        repository_context, user_id
                    )
                    
                    if not cache_success:
                        logger.warning(f"Failed to cache repository data: {repository_url}")
                        # Continue anyway, but log the issue
                else:
                    logger.warning("No repository context could be detected from request")
                

                
                # Set the repository URL in enhanced context
                if repository_url:
                    enhanced_context["repository_url"] = repository_url
                    logger.info(f"Using repository URL for Cosmos: {repository_url}")
                    
                    # Get branch info from repository context or fallback
                    branch = repository_context.branch if repository_context else (session.get("branch") or context.get("branch") or "main")
                    enhanced_context["branch"] = branch
                    
                    if optimized_system_available:
                        # Use full optimized repository middleware for fast data access with user's GitHub token
                        repo_middleware = get_repo_middleware(user_id)
                        
                        # Get repository context with optimized caching
                        repo_context = repo_middleware.get_repository_context(repository_url)
                        
                        if repo_context.get("error"):
                            logger.warning(f"Repository context error: {repo_context['error']}")
                            # Still use optimized manager even with errors
                            repo_manager = OptimizedRedisRepoManager(
                                repo_url=repository_url,
                                branch=branch,
                                username=user_id
                            )
                        else:
                            logger.info(f"Repository context loaded in {repo_context.get('fetch_time_ms', 0)}ms")
                            # Create optimized repo manager that uses our fast service
                            repo_manager = OptimizedRedisRepoManager(
                                repo_url=repository_url,
                                branch=branch,
                                username=user_id
                            )
                            
                            # Pre-load selected files using optimized service
                            if session.get("selectedFiles"):
                                for file_info in session["selectedFiles"]:
                                    if isinstance(file_info, dict) and file_info.get("path"):
                                        file_path = file_info["path"]
                                        file_content = repo_middleware.get_file_content_fast(repository_url, file_path)
                                        if file_content:
                                            logger.info(f"Pre-loaded file: {file_path}")
                    else:
                        # Use simple optimized system as fallback
                        logger.info("Using simple optimized repository system")
                        
                        # Create a wrapper that uses the simple optimized service
                        simple_service = get_simple_optimized_repo_service(user_id)
                        
                        # Test repository access
                        repo_data = simple_service.get_repository_data(repository_url)
                        if repo_data:
                            logger.info("Repository data loaded successfully with simple optimized system")
                        else:
                            logger.warning("Repository data not available with simple optimized system")
                        
                        # Create standard repo manager but with optimized token handling
                        repo_manager = RedisRepoManager(
                            repo_url=repository_url,
                            branch=branch,
                            username=user_id
                        )
                    
                    # Create Cosmos wrapper for this request
                    wrapper = CosmosWebWrapper(
                        repo_manager=repo_manager,
                        model=model_name,
                        user_id=user_id
                    )
                    
                    # Add selected files to context using optimized access
                    if session.get("selectedFiles"):
                        for file_info in session["selectedFiles"]:
                            if isinstance(file_info, dict) and file_info.get("path"):
                                wrapper.add_file_to_context(file_info["path"])
                else:
                    logger.warning("No repository URL found in request - Cosmos will not have repository context")
                    # Create a minimal wrapper without repository context
                    if optimized_system_available:
                        repo_manager = OptimizedRedisRepoManager(
                            repo_url="https://github.com/default/repo",  # Placeholder
                            branch="main",
                            username=user_id
                        )
                    else:
                        repo_manager = RedisRepoManager(
                            repo_url="https://github.com/default/repo",  # Placeholder
                            branch="main",
                            username=user_id
                        )
                    wrapper = CosmosWebWrapper(
                        repo_manager=repo_manager,
                        model=model_name,
                        user_id=user_id
                    )
                
                # Process message through Cosmos AI system
                if status_broadcaster:
                    await status_broadcaster.broadcast_operation_progress(
                        operation_id=operation_id,
                        progress=0.8,
                        message="Processing message with AI..."
                    )
                
                cosmos_response = await wrapper.process_message(
                    message=message,
                    context=enhanced_context
                )
                
                if status_broadcaster:
                    await status_broadcaster.broadcast_operation_progress(
                        operation_id=operation_id,
                        progress=0.9,
                        message="AI processing complete, preparing response..."
                    )
                
                # Extract content and metadata
                raw_assistant_content = cosmos_response.content
                confidence = cosmos_response.confidence
                sources = cosmos_response.sources
                knowledge_used = len(sources) if sources else 0
                model_used = cosmos_response.model_used or model_name
                
                # Apply tool command filtering for security
                try:
                    from services.tool_command_filter import filter_tool_commands
                    assistant_content = filter_tool_commands(raw_assistant_content)
                    logger.debug("Applied tool command filtering to response")
                except ImportError:
                    logger.warning("Tool command filter not available, using raw content")
                    assistant_content = raw_assistant_content
                except Exception as filter_error:
                    logger.error(f"Error applying tool command filter: {filter_error}")
                    assistant_content = raw_assistant_content
                
                # Add metadata to response if available
                if knowledge_used > 0:
                    assistant_content += f"\n\n*Analyzed {knowledge_used} files from your codebase*"
                
                if sources:
                    source_names = [s.split('/')[-1] for s in sources[:3]]  # Get file names
                    assistant_content += f"\n\n*Referenced files: {', '.join(source_names)}*"
                
                # Cleanup wrapper
                wrapper.cleanup()
                
                # Broadcast successful completion
                if status_broadcaster:
                    await status_broadcaster.broadcast_operation_complete(
                        operation_id=operation_id,
                        result={
                            "model_used": model_used,
                            "confidence": confidence,
                            "knowledge_used": knowledge_used,
                            "sources_count": len(sources),
                            "response_length": len(assistant_content)
                        }
                    )
                
            else:
                # When Cosmos is not available, return an error message
                assistant_content = "I'm sorry, but the Cosmos AI system is currently unavailable. Please ensure that Cosmos is properly installed and configured to use the chat functionality."
                
                if status_broadcaster:
                    await status_broadcaster.broadcast_operation_error(
                        operation_id=operation_id,
                        error_message="Cosmos AI system unavailable",
                        error_details={"cosmos_available": False}
                    )
                model_used = "unavailable"
        
        except Exception as e:
            logger.error(f"Error processing message with Cosmos: {e}")
            assistant_content = f"I encountered an error while processing your message through Cosmos AI: {str(e)}. Please try again or check the Cosmos configuration."
            model_used = "error"
            
            # Broadcast error if available
            if status_broadcaster:
                try:
                    await status_broadcaster.broadcast_operation_error(
                        operation_id=operation_id,
                        error_message=str(e),
                        error_details={"phase": "cosmos_processing", "model": model_name}
                    )
                except Exception as broadcast_error:
                    logger.error(f"Error broadcasting operation error: {broadcast_error}")
        
        # Create assistant message
        assistant_message = {
            "id": str(uuid.uuid4()),
            "type": "assistant", 
            "content": assistant_content,
            "timestamp": datetime.now().isoformat(),
            "files": [],
            "model": model_used,
            "metadata": {
                "confidence": confidence,
                "knowledge_used": knowledge_used,
                "sources_count": len(sources),
                "cosmos_available": self.cosmos_available and COSMOS_AVAILABLE
            }
        }
        
        # Add assistant message to history
        messages = get_messages(session_id)
        messages.append(assistant_message)
        store_messages(session_id, messages, ttl_hours=24)
        
        # Update session timestamp
        session["updatedAt"] = datetime.now().isoformat()
        session["messages"] = messages
        store_session(session_id, session, ttl_hours=24)
        
        # Track final metrics if available
        if metrics_collector:
            try:
                request_end = datetime.now()
                total_latency = (request_end - request_start).total_seconds() * 1000
                
                await metrics_collector.record_request_latency(
                    session_id=session_id,
                    request_id="chat_message",
                    latency_ms=total_latency,
                    operation_type="chat_message"
                )
                await metrics_collector.track_token_usage(session_id, len(message.split()) + len(assistant_content.split()))
                await metrics_collector.track_ai_operation(
                    model=model_used,
                    success=True,
                    confidence=confidence,
                    knowledge_used=knowledge_used,
                    response_time_ms=total_latency
                )
            except Exception as e:
                logger.error(f"Error tracking final metrics: {e}")
        
        # Send WebSocket update to connected clients
        try:
            await ws_manager.send_to_session(session_id, {
                "type": "message_complete",
                "user_message": user_message,
                "assistant_message": assistant_message,
                "session_updated": True,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending WebSocket update: {e}")
        
        return {
            "userMessage": user_message,
            "assistantMessage": assistant_message,
            "session": session
        }

# Initialize service
chat_service = ChatCosmosService()

@router.get("/repository/suggested-files")
async def get_suggested_files(
    repository_url: str,
    branch: str = "main",
    limit: int = 10,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get suggested files for repository context"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from services.repository_context_detection_service import repository_context_service
        
        # Create repository context
        repo_context = repository_context_service._create_repository_context(repository_url, branch)
        
        # Get suggested files
        suggested_files = repository_context_service.get_suggested_files(repo_context, limit)
        
        return JSONResponse({
            "success": True,
            "suggested_files": [
                {
                    "path": file.path,
                    "name": file.name,
                    "relevance_score": file.relevance_score,
                    "language": file.language,
                    "size_bytes": file.size_bytes,
                    "show_plus_icon": file.show_plus_icon
                }
                for file in suggested_files
            ],
            "repository_url": repository_url,
            "branch": branch
        })
        
    except Exception as e:
        logger.error(f"Error getting suggested files: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "suggested_files": []
        }, status_code=500)

@router.post("/repository/context")
async def detect_repository_context(
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Detect repository context from page information"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from services.repository_context_detection_service import repository_context_service
        
        page_context = request.get("page_context", {})
        user_id = str(current_user.id)
        
        # Detect repository context
        repo_context = repository_context_service.detect_repository_context(page_context)
        
        if not repo_context:
            return JSONResponse({
                "success": False,
                "error": "No repository context could be detected",
                "repository_context": None
            })
        
        # Validate repository size
        repo_context = await repository_context_service.validate_repository_size(repo_context, user_id)
        
        # Ensure repository is cached if validation passed
        cache_success = False
        if repo_context.validation_status == "valid":
            cache_success = repository_context_service.ensure_repository_cached(repo_context, user_id)
        
        return JSONResponse({
            "success": True,
            "repository_context": {
                "url": repo_context.url,
                "branch": repo_context.branch,
                "name": repo_context.name,
                "owner": repo_context.owner,
                "is_private": repo_context.is_private,
                "size_mb": repo_context.size_mb,
                "file_count": repo_context.file_count,
                "validation_status": repo_context.validation_status,
                "error_message": repo_context.error_message,
                "cached": cache_success
            }
        })
        
    except Exception as e:
        logger.error(f"Error detecting repository context: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "repository_context": None
        }, status_code=500)

@router.delete("/repository/cache")
async def clear_repository_cache(
    repository_url: str,
    branch: str = "main",
    current_user: Optional[User] = Depends(get_current_user)
):
    """Clear repository cache (called when navigating away from /contribution)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from services.repository_context_detection_service import repository_context_service
        
        user_id = str(current_user.id)
        
        # Clear specific repository cache
        cache_cleared = repository_context_service.clear_repository_cache(repository_url, branch)
        
        # Also cleanup user cache if requested
        cleanup_all = request.args.get('cleanup_all', 'false').lower() == 'true'
        if cleanup_all:
            cleanup_count = repository_context_service.cleanup_user_cache(user_id)
            return JSONResponse({
                "success": True,
                "cache_cleared": cache_cleared,
                "cleanup_count": cleanup_count,
                "message": f"Cleared repository cache and {cleanup_count} user cache entries"
            })
        
        return JSONResponse({
            "success": True,
            "cache_cleared": cache_cleared,
            "message": "Repository cache cleared" if cache_cleared else "No cache found to clear"
        })
        
    except Exception as e:
        logger.error(f"Error clearing repository cache: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "cache_cleared": False
        }, status_code=500)

@router.post("/sessions")
async def create_chat_session(
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = await chat_service.create_session(
            user_id=str(current_user.id),
            title=request.get("title"),
            repository_id=request.get("repositoryId"),
            repository_url=request.get("repositoryUrl"),
            branch=request.get("branch", "main")
        )
        
        return {
            "success": True,
            "session": session
        }
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = await chat_service.get_session(session_id, str(current_user.id))
        return {
            "success": True,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@router.put("/sessions/{session_id}")
async def update_chat_session(
    session_id: str,
    updates: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.get("userId") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update allowed fields
        allowed_fields = ["title", "selectedFiles"]
        for field in allowed_fields:
            if field in updates:
                session[field] = updates[field]
        
        session["updatedAt"] = datetime.now().isoformat()
        store_session(session_id, session, ttl_hours=24)
        
        return {
            "success": True,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Delete a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.get("userId") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete session and messages
        delete_session(session_id, str(current_user.id))
        
        return {
            "success": True,
            "message": "Session deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all sessions for a user"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        user_sessions = []
        session_ids = get_user_sessions(user_id)
        
        for session_id in session_ids:
            session = get_session(session_id)
            if session and session.get("userId") == user_id:
                session_copy = session.copy()
                session_copy["messages"] = get_messages(session_id)
                user_sessions.append(session_copy)
        
        # Sort by updated time (newest first)
        user_sessions.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
        
        return {
            "success": True,
            "sessions": user_sessions
        }
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Send a message in a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        message = request.get("message", "")
        context = request.get("context", {})
        model_name = request.get("model", "gpt-4o-mini")  # Default model
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        result = await chat_service.send_message(
            session_id=session_id,
            user_id=str(current_user.id),
            message=message,
            context=context,
            model_name=model_name
        )
        
        return {
            "success": True,
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        # Handle rate limit errors specifically
        from utils.error_handling import RateLimitError
        if isinstance(e, RateLimitError):
            logger.warning(f"Rate limit exceeded for user {current_user.id}: {e.message}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": e.message,
                        "category": "rate_limit",
                        "retry_after": e.retry_after,
                        "details": e.details
                    }
                }
            )
        
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.get("/sessions/{session_id}/messages")
async def get_chat_history(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get chat history for a session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = await chat_service.get_session(session_id, str(current_user.id))
        messages = get_messages(session_id)
        
        return {
            "success": True,
            "messages": messages,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat history")

@router.get("/health")
async def chat_health_check():
    """Enhanced health check endpoint for chat service with performance monitoring"""
    health_status = {
        "status": "healthy",
        "redis_available": REDIS_AVAILABLE,
        "redis_circuit_breaker": {
            "state": redis_circuit_breaker.state,
            "failure_count": redis_circuit_breaker.failure_count
        },
        "cosmos_available": COSMOS_AVAILABLE,
        "status_broadcasting_available": STATUS_BROADCASTING_AVAILABLE,
        "enhanced_session_available": ENHANCED_SESSION_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }
    
    # Test Redis connection if available
    if REDIS_AVAILABLE and redis_circuit_breaker.can_execute():
        try:
            start_time = datetime.now()
            session_redis.ping()
            ping_time = (datetime.now() - start_time).total_seconds() * 1000
            
            health_status["redis_ping"] = "success"
            health_status["redis_ping_time_ms"] = ping_time
            redis_circuit_breaker.record_success()
        except Exception as e:
            health_status["redis_ping"] = f"failed: {str(e)}"
            health_status["status"] = "degraded"
            redis_circuit_breaker.record_failure()
    else:
        health_status["redis_ping"] = "circuit_open" if REDIS_AVAILABLE else "unavailable"
        if not REDIS_AVAILABLE:
            health_status["status"] = "degraded"
    
    # Test enhanced services if available
    if STATUS_BROADCASTING_AVAILABLE:
        try:
            status_broadcaster = get_status_broadcaster()
            health_status["status_broadcaster"] = {
                "active_connections": len(status_broadcaster.connections),
                "active_sessions": len(status_broadcaster.session_connections),
                "active_operations": len(status_broadcaster.active_operations)
            }
        except Exception as e:
            health_status["status_broadcaster"] = {"error": str(e)}
            health_status["status"] = "degraded"
    
    # Add WebSocket connection stats
    health_status["websocket_connections"] = {
        "active_connections": len(ws_manager.connections),
        "active_sessions": len(ws_manager.session_connections)
    }
    
    return health_status

@router.get("/metrics")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user),
    session_id: str = None,
    time_range: str = "1h"  # 1h, 24h, 7d, 30d
):
    """Get performance metrics for chat operations."""
    try:
        if not STATUS_BROADCASTING_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Performance monitoring not available",
                    "metrics": {}
                }
            )
        
        metrics_collector = get_metrics_collector()
        user_id = str(current_user.id)
        
        # Get metrics based on time range
        time_ranges = {
            "1h": 3600,
            "24h": 86400,
            "7d": 604800,
            "30d": 2592000
        }
        
        seconds = time_ranges.get(time_range, 3600)
        
        # Collect various metrics
        metrics = {
            "request_metrics": await metrics_collector.get_request_metrics(
                user_id=user_id,
                session_id=session_id,
                time_window_seconds=seconds
            ),
            "token_usage": await metrics_collector.get_token_usage_metrics(
                user_id=user_id,
                session_id=session_id,
                time_window_seconds=seconds
            ),
            "cache_metrics": await metrics_collector.get_cache_metrics(
                user_id=user_id,
                time_window_seconds=seconds
            ),
            "ai_operation_metrics": await metrics_collector.get_ai_operation_metrics(
                user_id=user_id,
                session_id=session_id,
                time_window_seconds=seconds
            ),
            "error_metrics": await metrics_collector.get_error_metrics(
                user_id=user_id,
                time_window_seconds=seconds
            ),
            "timestamp": datetime.now().isoformat(),
            "time_range": time_range
        }
        
        return JSONResponse(content={
            "success": True,
            "metrics": metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "metrics": {}
            }
        )

@router.get("/metrics/realtime")
async def get_realtime_metrics(
    current_user: User = Depends(get_current_user),
    session_id: str = None
):
    """Get real-time performance metrics for active sessions."""
    try:
        if not STATUS_BROADCASTING_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Real-time monitoring not available",
                    "metrics": {}
                }
            )
        
        metrics_collector = get_metrics_collector()
        status_broadcaster = get_status_broadcaster()
        user_id = str(current_user.id)
        
        # Get current system status
        realtime_metrics = {
            "system_status": {
                "active_operations": len(status_broadcaster.active_operations),
                "active_connections": len(status_broadcaster.connections),
                "active_sessions": len(status_broadcaster.session_connections),
                "websocket_connections": len(ws_manager.connections)
            },
            "current_operations": [
                {
                    "operation_id": op_id,
                    "operation_type": op_data.get("operation_type"),
                    "description": op_data.get("description"),
                    "progress": op_data.get("progress", 0.0),
                    "started_at": op_data.get("started_at").isoformat() if op_data.get("started_at") else None,
                    "status": op_data.get("status")
                }
                for op_id, op_data in status_broadcaster.active_operations.items()
                if not session_id or op_data.get("session_id") == session_id
            ],
            "recent_metrics": await metrics_collector.get_recent_metrics(
                user_id=user_id,
                session_id=session_id,
                limit=10
            ),
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content={
            "success": True,
            "metrics": realtime_metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "metrics": {}
            }
        )

@router.get("/metrics/system")
async def get_system_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get system-wide performance metrics (admin endpoint)."""
    try:
        # This could be restricted to admin users in production
        if not STATUS_BROADCASTING_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "System monitoring not available",
                    "metrics": {}
                }
            )
        
        metrics_collector = get_metrics_collector()
        
        # Get system-wide metrics
        system_metrics = {
            "redis_metrics": await metrics_collector.get_redis_system_metrics(),
            "cosmos_metrics": await metrics_collector.get_cosmos_system_metrics(),
            "session_metrics": await metrics_collector.get_session_system_metrics(),
            "error_summary": await metrics_collector.get_system_error_summary(),
            "performance_summary": await metrics_collector.get_system_performance_summary(),
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content={
            "success": True,
            "metrics": system_metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "metrics": {}
            }
        )

@router.post("/admin/cache/optimize")
async def optimize_system_cache(
    current_user: User = Depends(get_current_user)
):
    """Admin endpoint to optimize system cache performance."""
    try:
        # This should be restricted to admin users in production
        if not CACHE_MANAGEMENT_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Cache management not available",
                    "result": {}
                }
            )
        
        # Start cache optimization operation
        operation_id = str(uuid.uuid4())
        
        if STATUS_BROADCASTING_AVAILABLE:
            status_broadcaster = get_status_broadcaster()
            await status_broadcaster.broadcast_operation_start(
                operation_id=operation_id,
                operation_type=OperationType.REDIS_CACHE,
                description="System-wide cache optimization",
                user_id=str(current_user.id),
                metadata={"admin_operation": True}
            )
        
        # Perform cache optimization
        cache_service = create_cache_management_service("system")
        optimization_results = cache_service.optimize_memory_usage()
        
        # Cleanup expired entries
        expired_cleaned = cache_service.cleanup_expired_caches()
        
        # Get final cache stats
        cache_stats = cache_service.get_cache_stats()
        
        result = {
            "optimization_results": optimization_results,
            "expired_entries_cleaned": expired_cleaned,
            "final_cache_stats": {
                "total_keys": cache_stats.total_keys,
                "memory_usage_mb": cache_stats.memory_usage_mb,
                "hit_rate": cache_stats.hit_rate,
                "miss_rate": cache_stats.miss_rate
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if STATUS_BROADCASTING_AVAILABLE:
            await status_broadcaster.broadcast_operation_complete(
                operation_id=operation_id,
                result=result
            )
        
        return JSONResponse(content={
            "success": True,
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Error optimizing system cache: {e}")
        
        if STATUS_BROADCASTING_AVAILABLE:
            try:
                await status_broadcaster.broadcast_operation_error(
                    operation_id=operation_id if 'operation_id' in locals() else str(uuid.uuid4()),
                    error_message=str(e),
                    error_details={"operation": "cache_optimization"}
                )
            except Exception:
                pass
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "result": {}
            }
        )

@router.get("/admin/cache/stats")
async def get_admin_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """Admin endpoint to get detailed cache statistics."""
    try:
        if not CACHE_MANAGEMENT_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Cache management not available",
                    "stats": {}
                }
            )
        
        cache_service = create_cache_management_service("system")
        
        # Get comprehensive cache statistics
        cache_stats = cache_service.get_cache_stats()
        health_status = cache_service.health_check()
        
        # Get user-specific cache counts
        user_cache_breakdown = {}
        if hasattr(cache_service, 'get_user_cache_breakdown'):
            user_cache_breakdown = cache_service.get_user_cache_breakdown()
        
        stats = {
            "cache_stats": {
                "total_keys": cache_stats.total_keys,
                "memory_usage_mb": cache_stats.memory_usage_mb,
                "hit_rate": cache_stats.hit_rate,
                "miss_rate": cache_stats.miss_rate,
                "expired_keys": cache_stats.expired_keys,
                "user_cache_count": cache_stats.user_cache_count,
                "repository_cache_count": cache_stats.repository_cache_count,
                "session_cache_count": cache_stats.session_cache_count,
                "last_cleanup": cache_stats.last_cleanup.isoformat() if cache_stats.last_cleanup else None
            },
            "health_status": {
                "is_healthy": health_status.is_healthy,
                "connection_status": health_status.connection_status,
                "memory_usage_percent": health_status.memory_usage_percent,
                "response_time_ms": health_status.response_time_ms,
                "error_count": health_status.error_count,
                "last_error": health_status.last_error,
                "uptime_seconds": health_status.uptime_seconds
            },
            "user_cache_breakdown": user_cache_breakdown,
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content={
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting admin cache stats: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "stats": {}
            }
        )

@router.delete("/admin/cache/clear")
async def clear_system_cache(
    current_user: User = Depends(get_current_user),
    cache_type: str = "all"  # all, repository, session, user
):
    """Admin endpoint to clear system cache."""
    try:
        if not CACHE_MANAGEMENT_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Cache management not available",
                    "result": {}
                }
            )
        
        operation_id = str(uuid.uuid4())
        
        if STATUS_BROADCASTING_AVAILABLE:
            status_broadcaster = get_status_broadcaster()
            await status_broadcaster.broadcast_operation_start(
                operation_id=operation_id,
                operation_type=OperationType.REDIS_CACHE,
                description=f"System cache clear: {cache_type}",
                user_id=str(current_user.id),
                metadata={"admin_operation": True, "cache_type": cache_type}
            )
        
        cache_service = create_cache_management_service("system")
        
        # Clear cache based on type
        if cache_type == "all":
            result = {
                "repository_cleared": cache_service.clear_all_repository_cache(),
                "session_cleared": cache_service.clear_all_session_cache(),
                "user_cleared": cache_service.clear_all_user_cache()
            }
        elif cache_type == "repository":
            result = {"repository_cleared": cache_service.clear_all_repository_cache()}
        elif cache_type == "session":
            result = {"session_cleared": cache_service.clear_all_session_cache()}
        elif cache_type == "user":
            result = {"user_cleared": cache_service.clear_all_user_cache()}
        else:
            raise ValueError(f"Invalid cache_type: {cache_type}")
        
        result["timestamp"] = datetime.now().isoformat()
        result["cache_type"] = cache_type
        
        if STATUS_BROADCASTING_AVAILABLE:
            await status_broadcaster.broadcast_operation_complete(
                operation_id=operation_id,
                result=result
            )
        
        return JSONResponse(content={
            "success": True,
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Error clearing system cache: {e}")
        
        if STATUS_BROADCASTING_AVAILABLE:
            try:
                await status_broadcaster.broadcast_operation_error(
                    operation_id=operation_id if 'operation_id' in locals() else str(uuid.uuid4()),
                    error_message=str(e),
                    error_details={"operation": "cache_clear", "cache_type": cache_type}
                )
            except Exception:
                pass
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "result": {}
            }
        )

@router.get("/sessions/{session_id}/context/stats")
async def get_session_context_stats(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get context stats for a session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = await chat_service.get_session(session_id, str(current_user.id))
        selected_files = session.get("selectedFiles", [])
        
        stats = {
            "totalFiles": len(selected_files),
            "totalSources": len(selected_files),
            "totalTokens": sum(len(f.get("content", "").split()) for f in selected_files),
            "averageTokensPerFile": 0,
            "createdAt": session["createdAt"],
            "updatedAt": session["updatedAt"]
        }
        
        if stats["totalFiles"] > 0:
            stats["averageTokensPerFile"] = stats["totalTokens"] / stats["totalFiles"]
        
        return {
            "success": True,
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting context stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get context stats")

@router.put("/sessions/{session_id}/context")
async def update_session_context(
    session_id: str,
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update session context (add/remove files)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.get("userId") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        action = request.get("action")
        files = request.get("files", [])
        
        if action == "add_files":
            session["selectedFiles"].extend(files)
        elif action == "remove_files":
            # Remove files by path
            file_paths = {f["path"] for f in files}
            session["selectedFiles"] = [
                f for f in session["selectedFiles"] 
                if f["path"] not in file_paths
            ]
        elif action == "clear_files":
            session["selectedFiles"] = []
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        session["updatedAt"] = datetime.now().isoformat()
        store_session(session_id, session, ttl_hours=24)
        
        return {
            "success": True,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session context: {e}")
        raise HTTPException(status_code=500, detail="Failed to update context")

@router.get("/models")
async def get_available_models():
    """Get list of available AI models (equivalent to cosmos --list-models)"""
    try:
        if COSMOS_AVAILABLE:
            from services.redis_repo_manager import RedisRepoManager
            from services.cosmos_web_wrapper import CosmosWebWrapper
            
            # Create a temporary wrapper to get available models
            repo_manager = RedisRepoManager(
                repo_url="https://github.com/default/repo",  # Placeholder for model info
                branch="main",
                username="system"
            )
            wrapper = CosmosWebWrapper(repo_manager=repo_manager, model="gemini")
            models = [
                {
                    "name": model,
                    "display_name": model.replace("_", " ").title(),
                    "provider": "cosmos",
                    "available": True,
                    "context_length": 128000,  # Default context length
                    "supports_streaming": True
                }
                for model in wrapper.get_supported_models()
            ]
            wrapper.cleanup()
        else:
            # When Cosmos is not available, return empty models list
            models = [
                {
                    "name": "unavailable",
                    "display_name": "Cosmos AI Unavailable",
                    "provider": "cosmos",
                    "available": False,
                    "context_length": 0,
                    "supports_streaming": False,
                    "error": "Cosmos AI system is not available. Please install and configure Cosmos to use AI models."
                }
            ]
        
        return {
            "success": True,
            "models": models,
            "cosmos_available": COSMOS_AVAILABLE
        }
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail="Failed to get models")

@router.post("/sessions/cleanup")
async def cleanup_user_sessions(
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Clean up user sessions when navigating away from chat"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        cleanup_type = request.get("type", "all")  # "all", "inactive", or specific session_ids
        user_id = str(current_user.id)
        
        if cleanup_type == "all":
            # Delete all user sessions
            session_ids = get_user_sessions(user_id)
            for session_id in session_ids:
                delete_session(session_id, user_id)
            
            return {
                "success": True,
                "message": f"Cleaned up {len(session_ids)} sessions",
                "cleaned_sessions": len(session_ids)
            }
        
        elif cleanup_type == "inactive":
            # Delete sessions older than 1 hour
            session_ids = get_user_sessions(user_id)
            cleaned_count = 0
            current_time = datetime.now()
            
            for session_id in session_ids:
                session = get_session(session_id)
                if session:
                    updated_at = datetime.fromisoformat(session.get("updatedAt", session.get("createdAt", "")))
                    if (current_time - updated_at).total_seconds() > 3600:  # 1 hour
                        delete_session(session_id, user_id)
                        cleaned_count += 1
            
            return {
                "success": True,
                "message": f"Cleaned up {cleaned_count} inactive sessions",
                "cleaned_sessions": cleaned_count
            }
        
        elif cleanup_type == "specific":
            # Delete specific sessions
            session_ids_to_delete = request.get("session_ids", [])
            cleaned_count = 0
            
            for session_id in session_ids_to_delete:
                session = get_session(session_id)
                if session and session.get("userId") == user_id:
                    delete_session(session_id, user_id)
                    cleaned_count += 1
            
            return {
                "success": True,
                "message": f"Cleaned up {cleaned_count} specific sessions",
                "cleaned_sessions": cleaned_count
            }
        
        else:
            raise HTTPException(status_code=400, detail="Invalid cleanup type")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup sessions")

@router.post("/sessions/{session_id}/heartbeat")
async def session_heartbeat(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Keep session alive with heartbeat"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.get("userId") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update session timestamp and extend TTL
        session["updatedAt"] = datetime.now().isoformat()
        store_session(session_id, session, ttl_hours=24)
        
        # Also extend messages TTL
        messages = get_messages(session_id)
        store_messages(session_id, messages, ttl_hours=24)
        
        return {
            "success": True,
            "message": "Session heartbeat updated",
            "session_id": session_id,
            "updated_at": session["updatedAt"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session heartbeat: {e}")
        raise HTTPException(status_code=500, detail="Failed to update heartbeat")

@router.get("/models/{model_name}")
async def get_model_info(model_name: str):
    """Get detailed information about a specific model"""
    try:
        if COSMOS_AVAILABLE:
            from services.redis_repo_manager import RedisRepoManager
            from services.cosmos_web_wrapper import CosmosWebWrapper
            
            # Create a temporary wrapper to get model info
            repo_manager = RedisRepoManager(
                repo_url="https://github.com/default/repo",  # Placeholder for model info
                branch="main",
                username="system"
            )
            wrapper = CosmosWebWrapper(repo_manager=repo_manager, model="gemini")
            supported_models = wrapper.get_supported_models()
            
            if model_name in supported_models:
                model_info = {
                    "available": True,
                    "name": model_name,
                    "display_name": model_name.replace("_", " ").title(),
                    "provider": "cosmos",
                    "context_length": 128000,
                    "supports_streaming": True
                }
            else:
                model_info = {
                    "available": False,
                    "name": model_name,
                    "error": f"Model {model_name} not supported"
                }
            wrapper.cleanup()
        else:
            model_info = {
                "available": False,
                "name": model_name,
                "error": "Cosmos not available"
            }
        
        return {
            "success": True,
            "model": model_info
        }
    except Exception as e:
        logger.error(f"Error getting model info for {model_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model info")

@router.post("/sessions/{session_id}/cleanup")
async def cleanup_chat_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Cleanup cosmos session and cache when user leaves chat page"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = chat_sessions[session_id]
        if session.get("userId") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Cleanup cosmos session and Redis cache
        if COSMOS_AVAILABLE:
            try:
                from services.redis_repo_manager import RedisRepoManager
                repo_manager = RedisRepoManager(
                    repo_url="https://github.com/default/repo",  # Placeholder for cleanup
                    branch="main",
                    username=str(current_user.id)
                )
                # Cleanup any cached data for this session
                logger.info(f"Cleaned up session {session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session: {e}")
        
        return {
            "success": True,
            "message": "Session cleaned up successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up session: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup session")

@router.post("/cleanup/user")
async def cleanup_all_user_sessions(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Cleanup all cosmos sessions for a user when they leave the chat page entirely"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Cleanup all cosmos sessions for this user
        if COSMOS_AVAILABLE:
            try:
                from services.redis_repo_manager import RedisRepoManager
                repo_manager = RedisRepoManager(
                    repo_url="https://github.com/default/repo",  # Placeholder for cleanup
                    branch="main",
                    username=str(current_user.id)
                )
                # Cleanup any cached data for this user
                logger.info(f"Cleaned up all sessions for user {current_user.id}")
            except Exception as e:
                logger.error(f"Error cleaning up user sessions: {e}")
        
        return {
            "success": True,
            "message": "All user sessions cleaned up successfully"
        }
    except Exception as e:
        logger.error(f"Error cleaning up all user sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup user sessions")

@router.post("/cleanup/repository")
async def cleanup_repository_cache(
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Cleanup Redis cache for a specific repository"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        repository_id = request.get("repositoryId")
        branch = request.get("branch", "main")
        
        if not repository_id:
            raise HTTPException(status_code=400, detail="Repository ID is required")
        
        # Cleanup Redis cache for the repository
        if COSMOS_AVAILABLE:
            try:
                from services.redis_repo_manager import RedisRepoManager
                repo_manager = RedisRepoManager(
                    repo_url=f"https://github.com/{repository_id}",
                    branch=branch,
                    username=str(current_user.id)
                )
                
                message = f"Repository cache cleared for {repository_id}:{branch}"
                logger.info(message)
                
                return {
                    "success": True,
                    "message": message,
                    "cache_cleared": True
                }
            except Exception as cache_error:
                logger.error(f"Error clearing repository cache: {cache_error}")
                return {
                    "success": False,
                    "message": f"Error clearing cache: {str(cache_error)}"
                }
        else:
            return {
                "success": False,
                "message": "Cosmos not available - no cache to clear"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up repository cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup repository cache")

# Cache Management Endpoints

@router.get("/cache/stats")
async def get_cache_stats(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get cache statistics for the current user."""
    try:
        if not CACHE_MANAGEMENT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Cache management not available")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Create cache management service for user
        cache_service = create_cache_management_service(current_user.id)
        
        # Get cache statistics
        stats = cache_service.get_cache_stats()
        health = cache_service.health_check()
        
        return {
            "success": True,
            "user_id": current_user.id,
            "cache_stats": {
                "total_keys": stats.total_keys,
                "memory_usage_mb": stats.memory_usage_mb,
                "hit_rate": stats.hit_rate,
                "miss_rate": stats.miss_rate,
                "expired_keys": stats.expired_keys,
                "user_cache_count": stats.user_cache_count,
                "repository_cache_count": stats.repository_cache_count,
                "session_cache_count": stats.session_cache_count,
                "last_cleanup": stats.last_cleanup.isoformat() if stats.last_cleanup else None
            },
            "health_status": {
                "is_healthy": health.is_healthy,
                "connection_status": health.connection_status,
                "memory_usage_percent": health.memory_usage_percent,
                "response_time_ms": health.response_time_ms,
                "error_count": health.error_count,
                "uptime_seconds": health.uptime_seconds
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")


@router.post("/cache/cleanup")
async def cleanup_cache(
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Cleanup expired cache entries for the current user."""
    try:
        if not CACHE_MANAGEMENT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Cache management not available")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Create cache management service for user
        cache_service = create_cache_management_service(current_user.id)
        
        # Get cleanup options from request
        cleanup_type = request.get("type", "expired")  # expired, repository, session, all
        
        cleaned_entries = 0
        operations_performed = []
        
        if cleanup_type in ["expired", "all"]:
            cleaned_entries += cache_service.cleanup_expired_caches()
            operations_performed.append("expired_cleanup")
        
        if cleanup_type in ["repository", "all"]:
            cache_service.clear_user_repository_cache()
            operations_performed.append("repository_cleanup")
        
        if cleanup_type in ["session", "all"]:
            cache_service.clear_user_session_cache()
            operations_performed.append("session_cleanup")
        
        # Get final stats
        final_stats = cache_service.get_cache_stats()
        
        return {
            "success": True,
            "user_id": current_user.id,
            "cleanup_type": cleanup_type,
            "operations_performed": operations_performed,
            "cleaned_entries": cleaned_entries,
            "final_stats": {
                "total_keys": final_stats.total_keys,
                "memory_usage_mb": final_stats.memory_usage_mb,
                "repository_cache_count": final_stats.repository_cache_count,
                "session_cache_count": final_stats.session_cache_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup cache")


@router.post("/navigation/track")
async def track_navigation(
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Track navigation event and perform automatic cache cleanup."""
    try:
        if not CACHE_MANAGEMENT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Cache management not available")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get navigation data from request
        from_page = request.get("from_page", "")
        to_page = request.get("to_page", "")
        session_id = request.get("session_id")
        repository_url = request.get("repository_url")
        
        if not from_page or not to_page:
            raise HTTPException(status_code=400, detail="from_page and to_page are required")
        
        # Create navigation cache manager for user
        nav_manager = create_navigation_cache_manager(current_user.id)
        
        # Handle navigation with automatic cleanup
        cleanup_result = nav_manager.handle_navigation(
            from_page=from_page,
            to_page=to_page,
            session_id=session_id,
            repository_url=repository_url
        )
        
        # Get navigation history
        recent_history = nav_manager.get_navigation_history(limit=5)
        
        return {
            "success": True,
            "user_id": current_user.id,
            "navigation": {
                "from_page": from_page,
                "to_page": to_page,
                "session_id": session_id,
                "repository_url": repository_url
            },
            "cleanup_result": {
                "repository_cache_cleared": cleanup_result.repository_cache_cleared,
                "session_cache_cleared": cleanup_result.session_cache_cleared,
                "context_cache_cleared": cleanup_result.context_cache_cleared,
                "entries_cleaned": cleanup_result.entries_cleaned,
                "memory_freed_mb": cleanup_result.memory_freed_mb,
                "cleanup_time_ms": cleanup_result.cleanup_time_ms
            },
            "recent_navigation": recent_history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking navigation: {e}")
        raise HTTPException(status_code=500, detail="Failed to track navigation")


@router.get("/navigation/session-stats")
async def get_session_stats(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get session statistics including navigation and cache information."""
    try:
        if not CACHE_MANAGEMENT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Cache management not available")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Create navigation cache manager for user
        nav_manager = create_navigation_cache_manager(current_user.id)
        
        # Get session statistics
        session_stats = nav_manager.get_session_stats()
        
        return {
            "success": True,
            "user_id": current_user.id,
            "session_stats": session_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session statistics")


@router.post("/cache/optimize")
async def optimize_cache_memory(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Optimize cache memory usage by cleaning up old entries and compacting data."""
    try:
        if not CACHE_MANAGEMENT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Cache management not available")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Create cache management service for user
        cache_service = create_cache_management_service(current_user.id)
        
        # Perform memory optimization
        optimization_result = cache_service.optimize_memory_usage()
        
        return {
            "success": True,
            "user_id": current_user.id,
            "optimization_result": optimization_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing cache memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to optimize cache memory")