"""
Performance Configuration for Cosmos Optimization

Optimized configurations for Redis operations, WebSocket performance,
database connections, and monitoring systems.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RedisPerformanceConfig:
    """Optimized Redis configuration for minimal memory usage and maximum performance."""
    
    # Connection settings
    max_connections: int = 20
    connection_pool_size: int = 10
    connection_timeout: float = 5.0
    socket_timeout: float = 2.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = None
    
    # Memory optimization settings
    max_memory_policy: str = "allkeys-lru"  # Evict least recently used keys
    memory_warning_threshold_mb: float = 80.0
    memory_critical_threshold_mb: float = 100.0
    
    # Cache optimization settings
    default_ttl: int = 3600  # 1 hour default TTL
    max_key_size: int = 1024 * 1024  # 1MB max key size
    compression_enabled: bool = True
    compression_threshold: int = 1024  # Compress values > 1KB
    
    # Performance tuning
    pipeline_size: int = 100  # Batch operations
    retry_attempts: int = 3
    retry_delay: float = 0.1
    
    def __post_init__(self):
        if self.socket_keepalive_options is None:
            self.socket_keepalive_options = {
                "TCP_KEEPIDLE": 1,
                "TCP_KEEPINTVL": 3,
                "TCP_KEEPCNT": 5
            }


@dataclass
class WebSocketPerformanceConfig:
    """Optimized WebSocket configuration for concurrent users."""
    
    # Connection limits
    max_connections_per_session: int = 5
    max_total_connections: int = 1000
    connection_timeout: float = 30.0
    
    # Message handling
    max_message_size: int = 64 * 1024  # 64KB max message
    message_queue_size: int = 100
    broadcast_batch_size: int = 50
    
    # Performance settings
    ping_interval: float = 30.0
    ping_timeout: float = 10.0
    close_timeout: float = 5.0
    
    # Compression
    compression_enabled: bool = True
    compression_threshold: int = 1024
    
    # Rate limiting
    messages_per_second: int = 10
    burst_limit: int = 20


@dataclass
class DatabasePerformanceConfig:
    """Optimized database configuration for connection pooling and query performance."""
    
    # Connection pool settings
    min_pool_size: int = 5
    max_pool_size: int = 20
    pool_timeout: float = 30.0
    pool_recycle: int = 3600  # Recycle connections every hour
    
    # Query optimization
    query_timeout: float = 30.0
    statement_timeout: float = 60.0
    
    # Connection settings
    connect_timeout: float = 10.0
    command_timeout: float = 60.0
    
    # Performance tuning
    prepared_statement_cache_size: int = 100
    enable_query_logging: bool = False  # Disable in production
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class MonitoringConfig:
    """Configuration for monitoring and alerting systems."""
    
    # Metrics collection
    metrics_collection_interval: float = 10.0  # seconds
    metrics_retention_hours: int = 24
    
    # Performance thresholds
    response_time_warning_ms: float = 1000.0
    response_time_critical_ms: float = 5000.0
    
    cache_hit_rate_warning: float = 0.7  # 70%
    cache_hit_rate_critical: float = 0.5  # 50%
    
    error_rate_warning: float = 0.05  # 5%
    error_rate_critical: float = 0.1   # 10%
    
    # Memory thresholds
    memory_usage_warning_percent: float = 80.0
    memory_usage_critical_percent: float = 90.0
    
    # WebSocket thresholds
    websocket_connection_warning: int = 800
    websocket_connection_critical: int = 950
    
    # Alerting
    enable_alerts: bool = True
    alert_cooldown_minutes: int = 5


class PerformanceConfigManager:
    """Manages performance configurations for the entire system."""
    
    def __init__(self):
        self.redis_config = RedisPerformanceConfig()
        self.websocket_config = WebSocketPerformanceConfig()
        self.database_config = DatabasePerformanceConfig()
        self.monitoring_config = MonitoringConfig()
        
        # Load from environment variables if available
        self._load_from_environment()
    
    def _load_from_environment(self):
        """Load configuration overrides from environment variables."""
        
        # Redis configuration
        if os.getenv("REDIS_MAX_CONNECTIONS"):
            self.redis_config.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS"))
        
        if os.getenv("REDIS_MEMORY_WARNING_MB"):
            self.redis_config.memory_warning_threshold_mb = float(os.getenv("REDIS_MEMORY_WARNING_MB"))
        
        if os.getenv("REDIS_COMPRESSION_ENABLED"):
            self.redis_config.compression_enabled = os.getenv("REDIS_COMPRESSION_ENABLED").lower() == "true"
        
        # WebSocket configuration
        if os.getenv("WS_MAX_CONNECTIONS"):
            self.websocket_config.max_total_connections = int(os.getenv("WS_MAX_CONNECTIONS"))
        
        if os.getenv("WS_MESSAGE_RATE_LIMIT"):
            self.websocket_config.messages_per_second = int(os.getenv("WS_MESSAGE_RATE_LIMIT"))
        
        # Database configuration
        if os.getenv("DB_MAX_POOL_SIZE"):
            self.database_config.max_pool_size = int(os.getenv("DB_MAX_POOL_SIZE"))
        
        if os.getenv("DB_QUERY_TIMEOUT"):
            self.database_config.query_timeout = float(os.getenv("DB_QUERY_TIMEOUT"))
        
        # Monitoring configuration
        if os.getenv("MONITORING_ENABLED"):
            self.monitoring_config.enable_alerts = os.getenv("MONITORING_ENABLED").lower() == "true"
    
    def get_redis_connection_params(self) -> Dict[str, Any]:
        """Get Redis connection parameters optimized for performance."""
        return {
            "max_connections": self.redis_config.max_connections,
            "connection_pool_class_kwargs": {
                "max_connections": self.redis_config.connection_pool_size,
                "socket_timeout": self.redis_config.socket_timeout,
                "socket_connect_timeout": self.redis_config.connection_timeout,
                "socket_keepalive": self.redis_config.socket_keepalive,
                "socket_keepalive_options": self.redis_config.socket_keepalive_options,
                "retry_on_timeout": True,
                "retry_on_error": [ConnectionError, TimeoutError],
                "health_check_interval": 30
            }
        }
    
    def get_websocket_settings(self) -> Dict[str, Any]:
        """Get WebSocket settings optimized for concurrent users."""
        return {
            "max_connections": self.websocket_config.max_total_connections,
            "max_connections_per_session": self.websocket_config.max_connections_per_session,
            "ping_interval": self.websocket_config.ping_interval,
            "ping_timeout": self.websocket_config.ping_timeout,
            "close_timeout": self.websocket_config.close_timeout,
            "max_size": self.websocket_config.max_message_size,
            "compression": "deflate" if self.websocket_config.compression_enabled else None,
            "per_message_deflate": self.websocket_config.compression_enabled
        }
    
    def get_database_settings(self) -> Dict[str, Any]:
        """Get database settings optimized for connection pooling."""
        return {
            "pool_min_size": self.database_config.min_pool_size,
            "pool_max_size": self.database_config.max_pool_size,
            "pool_timeout": self.database_config.pool_timeout,
            "pool_recycle": self.database_config.pool_recycle,
            "connect_timeout": self.database_config.connect_timeout,
            "command_timeout": self.database_config.command_timeout,
            "prepared_statement_cache_size": self.database_config.prepared_statement_cache_size,
            "statement_timeout": self.database_config.statement_timeout
        }
    
    def get_monitoring_thresholds(self) -> Dict[str, Any]:
        """Get monitoring thresholds for alerting."""
        return {
            "response_time": {
                "warning": self.monitoring_config.response_time_warning_ms,
                "critical": self.monitoring_config.response_time_critical_ms
            },
            "cache_hit_rate": {
                "warning": self.monitoring_config.cache_hit_rate_warning,
                "critical": self.monitoring_config.cache_hit_rate_critical
            },
            "error_rate": {
                "warning": self.monitoring_config.error_rate_warning,
                "critical": self.monitoring_config.error_rate_critical
            },
            "memory_usage": {
                "warning": self.monitoring_config.memory_usage_warning_percent,
                "critical": self.monitoring_config.memory_usage_critical_percent
            },
            "websocket_connections": {
                "warning": self.monitoring_config.websocket_connection_warning,
                "critical": self.monitoring_config.websocket_connection_critical
            }
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate all configurations and return validation results."""
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Validate Redis configuration
        if self.redis_config.max_connections < self.redis_config.connection_pool_size:
            validation_results["warnings"].append(
                "Redis max_connections should be >= connection_pool_size"
            )
        
        if self.redis_config.memory_critical_threshold_mb <= self.redis_config.memory_warning_threshold_mb:
            validation_results["errors"].append(
                "Redis critical memory threshold must be > warning threshold"
            )
            validation_results["valid"] = False
        
        # Validate WebSocket configuration
        if self.websocket_config.ping_timeout >= self.websocket_config.ping_interval:
            validation_results["warnings"].append(
                "WebSocket ping_timeout should be < ping_interval"
            )
        
        # Validate Database configuration
        if self.database_config.max_pool_size < self.database_config.min_pool_size:
            validation_results["errors"].append(
                "Database max_pool_size must be >= min_pool_size"
            )
            validation_results["valid"] = False
        
        # Validate Monitoring configuration
        if self.monitoring_config.cache_hit_rate_critical >= self.monitoring_config.cache_hit_rate_warning:
            validation_results["warnings"].append(
                "Monitoring critical thresholds should be more severe than warning thresholds"
            )
        
        return validation_results
    
    def log_configuration(self):
        """Log current configuration for debugging."""
        logger.info("Performance Configuration Loaded", 
                   redis_max_connections=self.redis_config.max_connections,
                   redis_memory_warning_mb=self.redis_config.memory_warning_threshold_mb,
                   websocket_max_connections=self.websocket_config.max_total_connections,
                   database_max_pool_size=self.database_config.max_pool_size,
                   monitoring_enabled=self.monitoring_config.enable_alerts)


# Global configuration instance
_performance_config = None


def get_performance_config() -> PerformanceConfigManager:
    """Get the global performance configuration instance."""
    global _performance_config
    if _performance_config is None:
        _performance_config = PerformanceConfigManager()
        
        # Validate configuration on first load
        validation = _performance_config.validate_configuration()
        if not validation["valid"]:
            logger.error("Performance configuration validation failed", 
                        errors=validation["errors"])
            raise ValueError(f"Invalid performance configuration: {validation['errors']}")
        
        if validation["warnings"]:
            logger.warning("Performance configuration warnings", 
                          warnings=validation["warnings"])
        
        _performance_config.log_configuration()
    
    return _performance_config


def reload_performance_config():
    """Reload performance configuration from environment."""
    global _performance_config
    _performance_config = None
    return get_performance_config()