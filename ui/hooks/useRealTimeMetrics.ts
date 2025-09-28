/**
 * Real-Time Metrics Hook
 * 
 * Provides real-time performance metrics with both HTTP polling and WebSocket support.
 * Falls back gracefully between different data sources.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { performanceMetricsService } from '@/lib/performance-metrics-service';
import { useWebSocketMetrics, WebSocketMetricsUpdate } from '@/lib/websocket-metrics-service';

export interface RealTimeMetrics {
  session_id: string;
  timestamp: string;
  token_usage: {
    total_tokens: number;
    total_cost: number;
    request_count: number;
    average_tokens_per_request: number;
  };
  latency: {
    average_ms: number;
    percentiles: {
      p50: number;
      p95: number;
      p99: number;
    };
  };
  cache_performance: {
    hit_rate: number;
    avg_response_time_ms: number;
  };
  error_rate: number;
  requests_per_minute: number;
}

export interface UseRealTimeMetricsOptions {
  sessionId: string;
  userId?: string;
  enableWebSocket?: boolean;
  enablePolling?: boolean;
  pollingInterval?: number;
  autoStart?: boolean;
}

export interface UseRealTimeMetricsReturn {
  metrics: RealTimeMetrics | null;
  loading: boolean;
  error: string | null;
  connected: boolean;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
  startTracking: () => void;
  stopTracking: () => void;
  recordLatency: (requestId: string, latencyMs: number, operationType?: string) => Promise<void>;
  recordTokenUsage: (requestId: string, inputTokens: number, outputTokens: number, modelName: string) => Promise<void>;
  recordCacheMetrics: (operation: string, hitRate: number, responseTimeMs: number, cacheSizeMb: number) => Promise<void>;
}

export function useRealTimeMetrics(options: UseRealTimeMetricsOptions): UseRealTimeMetricsReturn {
  const {
    sessionId,
    userId,
    enableWebSocket = true,
    enablePolling = true,
    pollingInterval = 5000,
    autoStart = true
  } = options;

  const [metrics, setMetrics] = useState<RealTimeMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isTracking, setIsTracking] = useState(false);

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  // WebSocket connection (only if enabled)
  const webSocketOptions = enableWebSocket ? { sessionId, userId } : null;
  const {
    connected: wsConnected,
    lastUpdate: wsLastUpdate,
    error: wsError
  } = webSocketOptions ? useWebSocketMetrics(webSocketOptions) : { connected: false, lastUpdate: null, error: null };

  // Fetch metrics from HTTP API
  const fetchMetrics = useCallback(async (): Promise<void> => {
    if (!sessionId || !mountedRef.current) return;

    try {
      setError(null);
      const data = await performanceMetricsService.fetchRealTimeMetrics(sessionId);
      
      if (mountedRef.current) {
        setMetrics(data);
        setLastUpdated(new Date());
        setLoading(false);
      }
    } catch (err) {
      if (mountedRef.current) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch metrics';
        setError(errorMessage);
        setLoading(false);
        console.error('Error fetching real-time metrics:', err);
      }
    }
  }, [sessionId]);

  // Handle WebSocket updates
  useEffect(() => {
    if (!wsLastUpdate || !enableWebSocket) return;

    try {
      // Update metrics based on WebSocket message type
      switch (wsLastUpdate.type) {
        case 'metrics_update':
          if (wsLastUpdate.data && mountedRef.current) {
            setMetrics(wsLastUpdate.data);
            setLastUpdated(new Date());
            setError(null);
          }
          break;
        
        case 'latency_update':
        case 'token_update':
        case 'cache_update':
          // Trigger a full metrics refresh for partial updates
          fetchMetrics();
          break;
        
        case 'error_update':
          if (mountedRef.current) {
            setError(wsLastUpdate.data?.message || 'WebSocket error');
          }
          break;
      }
    } catch (err) {
      console.error('Error processing WebSocket update:', err);
    }
  }, [wsLastUpdate, enableWebSocket, fetchMetrics]);

  // Handle WebSocket errors
  useEffect(() => {
    if (wsError && enableWebSocket && mountedRef.current) {
      console.warn('WebSocket error, falling back to polling:', wsError.message);
      // Don't set error state for WebSocket issues, just fall back to polling
    }
  }, [wsError, enableWebSocket]);

  // Polling mechanism
  useEffect(() => {
    if (!enablePolling || !isTracking || !sessionId) return;

    // Initial fetch
    fetchMetrics();

    // Set up polling interval
    pollingIntervalRef.current = setInterval(() => {
      // Only poll if WebSocket is not connected or disabled
      if (!enableWebSocket || !wsConnected) {
        fetchMetrics();
      }
    }, pollingInterval);

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [enablePolling, isTracking, sessionId, fetchMetrics, enableWebSocket, wsConnected, pollingInterval]);

  // Auto-start tracking
  useEffect(() => {
    if (autoStart && sessionId) {
      setIsTracking(true);
    }
  }, [autoStart, sessionId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Control functions
  const startTracking = useCallback(() => {
    setIsTracking(true);
    setLoading(true);
    setError(null);
  }, []);

  const stopTracking = useCallback(() => {
    setIsTracking(false);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const refresh = useCallback(async (): Promise<void> => {
    setLoading(true);
    await fetchMetrics();
  }, [fetchMetrics]);

  // Recording functions
  const recordLatency = useCallback(async (
    requestId: string,
    latencyMs: number,
    operationType: string = 'chat_request'
  ): Promise<void> => {
    try {
      await performanceMetricsService.recordLatencyMetric(
        sessionId,
        requestId,
        latencyMs,
        operationType,
        true
      );
    } catch (err) {
      console.error('Failed to record latency metric:', err);
    }
  }, [sessionId]);

  const recordTokenUsage = useCallback(async (
    requestId: string,
    inputTokens: number,
    outputTokens: number,
    modelName: string
  ): Promise<void> => {
    try {
      await performanceMetricsService.recordTokenUsageMetric(
        sessionId,
        requestId,
        inputTokens,
        outputTokens,
        modelName,
        userId
      );
    } catch (err) {
      console.error('Failed to record token usage metric:', err);
    }
  }, [sessionId, userId]);

  const recordCacheMetrics = useCallback(async (
    operation: string,
    hitRate: number,
    responseTimeMs: number,
    cacheSizeMb: number
  ): Promise<void> => {
    try {
      await performanceMetricsService.recordCacheMetric(
        sessionId,
        operation,
        hitRate,
        responseTimeMs,
        cacheSizeMb
      );
    } catch (err) {
      console.error('Failed to record cache metrics:', err);
    }
  }, [sessionId]);

  return {
    metrics,
    loading,
    error,
    connected: enableWebSocket ? wsConnected : isTracking,
    lastUpdated,
    refresh,
    startTracking,
    stopTracking,
    recordLatency,
    recordTokenUsage,
    recordCacheMetrics
  };
}

export default useRealTimeMetrics;