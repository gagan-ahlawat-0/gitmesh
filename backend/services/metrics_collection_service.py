"""
Metrics Collection Service

Implements real-time performance tracking, token usage monitoring, and latency measurement
for the Cosmos optimization system as specified in requirements 7.1-7.5.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import json

from config.settings import get_settings
from services.supabase_service import SupabaseService
from models.api.chat_analytics_models import PerformanceMetrics, MetricType

# Configure logging
logger = logging.getLogger(__name__)


class MetricCategory(Enum):
    """Categories of metrics for organization."""
    RESPONSE_TIME = "response_time"
    TOKEN_USAGE = "token_usage"
    CACHE_PERFORMANCE = "cache_performance"
    SYSTEM_PERFORMANCE = "system_performance"
    ERROR_TRACKING = "error_tracking"


@dataclass
class TokenUsageData:
    """Token usage tracking data."""
    session_id: str
    request_id: str
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model_name: str
    cost_estimate: float = 0.0
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'request_id': self.request_id,
            'timestamp': self.timestamp.isoformat(),
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'model_name': self.model_name,
            'cost_estimate': self.cost_estimate,
            'user_id': self.user_id
        }


@dataclass
class LatencyMeasurement:
    """Latency measurement data."""
    session_id: str
    request_id: str
    timestamp: datetime
    operation_type: str
    latency_ms: float
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'request_id': self.request_id,
            'timestamp': self.timestamp.isoformat(),
            'operation_type': self.operation_type,
            'latency_ms': self.latency_ms,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    session_id: str
    timestamp: datetime
    operation: str
    hit_rate: float
    response_time_ms: float
    cache_size_mb: float
    eviction_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'operation': self.operation,
            'hit_rate': self.hit_rate,
            'response_time_ms': self.response_time_ms,
            'cache_size_mb': self.cache_size_mb,
            'eviction_count': self.eviction_count,
            'metadata': self.metadata
        }


class TokenTracker:
    """Tracks token usage for accurate monitoring."""
    
    def __init__(self, supabase_service: SupabaseService):
        """Initialize token tracker."""
        self.supabase_service = supabase_service
        self._token_data: Dict[str, TokenUsageData] = {}
        self._lock = asyncio.Lock()
        
        # Token cost estimates (per 1K tokens)
        self._token_costs = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
            'claude-3-opus': {'input': 0.015, 'output': 0.075},
            'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
            'claude-3-haiku': {'input': 0.00025, 'output': 0.00125}
        }
    
    async def track_token_usage(
        self,
        session_id: str,
        request_id: str,
        input_tokens: int,
        output_tokens: int,
        model_name: str,
        user_id: Optional[str] = None
    ) -> TokenUsageData:
        """Track token usage for a request."""
        async with self._lock:
            total_tokens = input_tokens + output_tokens
            cost_estimate = self._calculate_cost(model_name, input_tokens, output_tokens)
            
            token_data = TokenUsageData(
                session_id=session_id,
                request_id=request_id,
                timestamp=datetime.now(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                model_name=model_name,
                cost_estimate=cost_estimate,
                user_id=user_id
            )
            
            self._token_data[request_id] = token_data
            
            # Store in Supabase for persistence
            await self._store_token_data(token_data)
            
            return token_data
    
    def _calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for token usage."""
        model_costs = self._token_costs.get(model_name.lower(), {'input': 0.001, 'output': 0.002})
        
        input_cost = (input_tokens / 1000) * model_costs['input']
        output_cost = (output_tokens / 1000) * model_costs['output']
        
        return input_cost + output_cost
    
    async def _store_token_data(self, token_data: TokenUsageData) -> None:
        """Store token data in Supabase."""
        try:
            await self.supabase_service.insert_data(
                'token_usage_metrics',
                token_data.to_dict()
            )
        except Exception as e:
            logger.error(f"Failed to store token data: {e}")
    
    async def get_session_token_usage(self, session_id: str) -> Dict[str, Any]:
        """Get token usage summary for a session."""
        try:
            data = await self.supabase_service.query_data(
                'token_usage_metrics',
                filters={'session_id': session_id}
            )
            
            if not data:
                return {'total_tokens': 0, 'total_cost': 0.0, 'request_count': 0}
            
            total_tokens = sum(item['total_tokens'] for item in data)
            total_cost = sum(item['cost_estimate'] for item in data)
            request_count = len(data)
            
            return {
                'total_tokens': total_tokens,
                'total_cost': total_cost,
                'request_count': request_count,
                'average_tokens_per_request': total_tokens / request_count if request_count > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get session token usage: {e}")
            return {'total_tokens': 0, 'total_cost': 0.0, 'request_count': 0}


class LatencyMonitor:
    """Monitors response time measurements."""
    
    def __init__(self, supabase_service: SupabaseService):
        """Initialize latency monitor."""
        self.supabase_service = supabase_service
        self._active_requests: Dict[str, float] = {}
        self._latency_data: deque = deque(maxlen=1000)
        self._lock = asyncio.Lock()
    
    def start_measurement(self, request_id: str) -> None:
        """Start measuring latency for a request."""
        self._active_requests[request_id] = time.time()
    
    async def end_measurement(
        self,
        request_id: str,
        session_id: str,
        operation_type: str,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[LatencyMeasurement]:
        """End latency measurement and record data."""
        if request_id not in self._active_requests:
            logger.warning(f"No active measurement found for request {request_id}")
            return None
        
        start_time = self._active_requests.pop(request_id)
        latency_ms = (time.time() - start_time) * 1000
        
        measurement = LatencyMeasurement(
            session_id=session_id,
            request_id=request_id,
            timestamp=datetime.now(),
            operation_type=operation_type,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        async with self._lock:
            self._latency_data.append(measurement)
        
        # Store in Supabase
        await self._store_latency_data(measurement)
        
        return measurement
    
    async def _store_latency_data(self, measurement: LatencyMeasurement) -> None:
        """Store latency data in Supabase."""
        try:
            await self.supabase_service.insert_data(
                'latency_measurements',
                measurement.to_dict()
            )
        except Exception as e:
            logger.error(f"Failed to store latency data: {e}")
    
    async def get_average_latency(
        self,
        session_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> float:
        """Get average latency for specified criteria."""
        try:
            filters = {}
            if session_id:
                filters['session_id'] = session_id
            if operation_type:
                filters['operation_type'] = operation_type
            if since:
                filters['timestamp'] = f"gte.{since.isoformat()}"
            
            data = await self.supabase_service.query_data(
                'latency_measurements',
                filters=filters
            )
            
            if not data:
                return 0.0
            
            successful_measurements = [item for item in data if item['success']]
            if not successful_measurements:
                return 0.0
            
            return sum(item['latency_ms'] for item in successful_measurements) / len(successful_measurements)
        except Exception as e:
            logger.error(f"Failed to get average latency: {e}")
            return 0.0
    
    async def get_latency_percentiles(
        self,
        session_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, float]:
        """Get latency percentiles (50th, 95th, 99th)."""
        try:
            filters = {}
            if session_id:
                filters['session_id'] = session_id
            if operation_type:
                filters['operation_type'] = operation_type
            if since:
                filters['timestamp'] = f"gte.{since.isoformat()}"
            
            data = await self.supabase_service.query_data(
                'latency_measurements',
                filters=filters
            )
            
            if not data:
                return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
            
            successful_measurements = [item['latency_ms'] for item in data if item['success']]
            if not successful_measurements:
                return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
            
            successful_measurements.sort()
            n = len(successful_measurements)
            
            return {
                'p50': successful_measurements[int(n * 0.5)],
                'p95': successful_measurements[int(n * 0.95)],
                'p99': successful_measurements[int(n * 0.99)]
            }
        except Exception as e:
            logger.error(f"Failed to get latency percentiles: {e}")
            return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}


class MetricsCollector:
    """Main metrics collection service for real-time performance tracking."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.settings = get_settings()
        self.supabase_service = SupabaseService()
        
        # Initialize component trackers
        self.token_tracker = TokenTracker(self.supabase_service)
        self.latency_monitor = LatencyMonitor(self.supabase_service)
        
        # In-memory metrics storage for real-time access
        self._metrics_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._cache_metrics: Dict[str, CacheMetrics] = {}
        self._lock = asyncio.Lock()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._aggregation_task: Optional[asyncio.Task] = None
    
    async def start_collection(self) -> None:
        """Start metrics collection background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
        logger.info("Metrics collection started")
    
    async def stop_collection(self) -> None:
        """Stop metrics collection background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Metrics collection stopped")
    
    async def record_request_latency(
        self,
        session_id: str,
        request_id: str,
        latency_ms: float,
        operation_type: str = "chat_request",
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record request latency metric."""
        async with self._lock:
            metric_data = {
                'timestamp': datetime.now(),
                'session_id': session_id,
                'request_id': request_id,
                'latency_ms': latency_ms,
                'operation_type': operation_type,
                'success': success,
                'metadata': metadata or {}
            }
            
            self._metrics_cache['request_latency'].append(metric_data)
        
        # Also store in persistent storage
        measurement = LatencyMeasurement(
            session_id=session_id,
            request_id=request_id,
            timestamp=datetime.now(),
            operation_type=operation_type,
            latency_ms=latency_ms,
            success=success,
            metadata=metadata or {}
        )
        
        await self.latency_monitor._store_latency_data(measurement)
    
    async def record_token_usage(
        self,
        session_id: str,
        request_id: str,
        input_tokens: int,
        output_tokens: int,
        model_name: str,
        user_id: Optional[str] = None
    ) -> TokenUsageData:
        """Record token usage metric."""
        return await self.token_tracker.track_token_usage(
            session_id=session_id,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
            user_id=user_id
        )
    
    async def record_cache_metrics(
        self,
        session_id: str,
        operation: str,
        hit_rate: float,
        response_time_ms: float,
        cache_size_mb: float,
        eviction_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record cache performance metrics."""
        cache_metrics = CacheMetrics(
            session_id=session_id,
            timestamp=datetime.now(),
            operation=operation,
            hit_rate=hit_rate,
            response_time_ms=response_time_ms,
            cache_size_mb=cache_size_mb,
            eviction_count=eviction_count,
            metadata=metadata or {}
        )
        
        async with self._lock:
            self._cache_metrics[f"{session_id}_{operation}"] = cache_metrics
            self._metrics_cache['cache_performance'].append(cache_metrics.to_dict())
        
        # Store in Supabase
        try:
            await self.supabase_service.insert_data(
                'cache_metrics',
                cache_metrics.to_dict()
            )
        except Exception as e:
            logger.error(f"Failed to store cache metrics: {e}")
    
    async def get_real_time_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get real-time metrics for a session."""
        try:
            # Get token usage
            token_usage = await self.token_tracker.get_session_token_usage(session_id)
            
            # Get latency metrics
            avg_latency = await self.latency_monitor.get_average_latency(session_id=session_id)
            latency_percentiles = await self.latency_monitor.get_latency_percentiles(session_id=session_id)
            
            # Get cache metrics
            cache_hit_rate = await self._get_session_cache_hit_rate(session_id)
            
            # Get error rate
            error_rate = await self._get_session_error_rate(session_id)
            
            return {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'token_usage': token_usage,
                'latency': {
                    'average_ms': avg_latency,
                    'percentiles': latency_percentiles
                },
                'cache_performance': {
                    'hit_rate': cache_hit_rate,
                    'avg_response_time_ms': await self._get_avg_cache_response_time(session_id)
                },
                'error_rate': error_rate,
                'requests_per_minute': await self._get_requests_per_minute(session_id)
            }
        except Exception as e:
            logger.error(f"Failed to get real-time metrics: {e}")
            return {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def _get_session_cache_hit_rate(self, session_id: str) -> float:
        """Get cache hit rate for a session."""
        try:
            data = await self.supabase_service.query_data(
                'cache_metrics',
                filters={'session_id': session_id}
            )
            
            if not data:
                return 0.0
            
            return sum(item['hit_rate'] for item in data) / len(data)
        except Exception as e:
            logger.error(f"Failed to get cache hit rate: {e}")
            return 0.0
    
    async def _get_avg_cache_response_time(self, session_id: str) -> float:
        """Get average cache response time for a session."""
        try:
            data = await self.supabase_service.query_data(
                'cache_metrics',
                filters={'session_id': session_id}
            )
            
            if not data:
                return 0.0
            
            return sum(item['response_time_ms'] for item in data) / len(data)
        except Exception as e:
            logger.error(f"Failed to get cache response time: {e}")
            return 0.0
    
    async def _get_session_error_rate(self, session_id: str) -> float:
        """Get error rate for a session."""
        try:
            total_data = await self.supabase_service.query_data(
                'latency_measurements',
                filters={'session_id': session_id}
            )
            
            if not total_data:
                return 0.0
            
            error_count = len([item for item in total_data if not item['success']])
            return (error_count / len(total_data)) * 100
        except Exception as e:
            logger.error(f"Failed to get error rate: {e}")
            return 0.0
    
    async def _get_requests_per_minute(self, session_id: str) -> float:
        """Get requests per minute for a session."""
        try:
            since = datetime.now() - timedelta(minutes=1)
            data = await self.supabase_service.query_data(
                'latency_measurements',
                filters={
                    'session_id': session_id,
                    'timestamp': f"gte.{since.isoformat()}"
                }
            )
            
            return len(data) if data else 0.0
        except Exception as e:
            logger.error(f"Failed to get requests per minute: {e}")
            return 0.0
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for old metrics."""
        while True:
            try:
                # Clean up old in-memory metrics (older than 1 hour)
                cutoff_time = datetime.now() - timedelta(hours=1)
                
                async with self._lock:
                    for metric_name, metric_deque in self._metrics_cache.items():
                        # Remove old entries
                        while metric_deque and metric_deque[0]['timestamp'] < cutoff_time:
                            metric_deque.popleft()
                
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def _aggregation_loop(self) -> None:
        """Background aggregation loop for metrics."""
        while True:
            try:
                # Aggregate metrics every 5 minutes
                await self._aggregate_metrics()
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}")
                await asyncio.sleep(60)
    
    async def _aggregate_metrics(self) -> None:
        """Aggregate metrics for better performance."""
        try:
            # This could include creating summary tables, calculating averages, etc.
            # For now, we'll just log that aggregation is running
            logger.debug("Running metrics aggregation")
        except Exception as e:
            logger.error(f"Failed to aggregate metrics: {e}")


# Global instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


async def initialize_metrics_collection() -> None:
    """Initialize the metrics collection service."""
    collector = get_metrics_collector()
    await collector.start_collection()


async def shutdown_metrics_collection() -> None:
    """Shutdown the metrics collection service."""
    global _metrics_collector
    if _metrics_collector:
        await _metrics_collector.stop_collection()
        _metrics_collector = None