/**
 * Real-Time Metrics Display Component
 * 
 * Displays real-time performance metrics including token usage, latency,
 * cache performance, and error rates with live updates.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Button } from '../ui/button';
import { 
  Activity, 
  Clock, 
  Zap, 
  Database, 
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Wifi,
  WifiOff
} from 'lucide-react';

interface TokenUsage {
  total_tokens: number;
  total_cost: number;
  request_count: number;
  average_tokens_per_request: number;
}

interface LatencyMetrics {
  average_ms: number;
  percentiles: {
    p50: number;
    p95: number;
    p99: number;
  };
}

interface CachePerformance {
  hit_rate: number;
  avg_response_time_ms: number;
}

interface RealTimeMetrics {
  session_id: string;
  timestamp: string;
  token_usage: TokenUsage;
  latency: LatencyMetrics;
  cache_performance: CachePerformance;
  error_rate: number;
  requests_per_minute: number;
}

interface MetricTrend {
  value: number;
  change: number;
  direction: 'up' | 'down' | 'stable';
}

interface RealTimeMetricsDisplayProps {
  sessionId: string;
  updateInterval?: number; // milliseconds
  showDetailed?: boolean;
  className?: string;
  onMetricsUpdate?: (metrics: RealTimeMetrics) => void;
}

export const RealTimeMetricsDisplay: React.FC<RealTimeMetricsDisplayProps> = ({
  sessionId,
  updateInterval = 5000, // 5 seconds
  showDetailed = false,
  className = '',
  onMetricsUpdate
}) => {
  // State
  const [metrics, setMetrics] = useState<RealTimeMetrics | null>(null);
  const [previousMetrics, setPreviousMetrics] = useState<RealTimeMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Fetch metrics from backend
  const fetchMetrics = useCallback(async () => {
    try {
      const response = await fetch(`/api/v1/metrics/realtime/${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data: RealTimeMetrics = await response.json();
      
      // Store previous metrics for trend calculation
      if (metrics) {
        setPreviousMetrics(metrics);
      }
      
      setMetrics(data);
      setLastUpdated(new Date());
      setError(null);
      setIsConnected(true);
      
      // Notify parent component
      if (onMetricsUpdate) {
        onMetricsUpdate(data);
      }
      
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, metrics, onMetricsUpdate]);

  // Calculate trend for a metric
  const calculateTrend = (current: number, previous: number): MetricTrend => {
    if (!previous || previous === 0) {
      return { value: current, change: 0, direction: 'stable' };
    }
    
    const change = ((current - previous) / previous) * 100;
    const direction = Math.abs(change) < 1 ? 'stable' : change > 0 ? 'up' : 'down';
    
    return { value: current, change: Math.abs(change), direction };
  };

  // Get trend icon
  const getTrendIcon = (direction: 'up' | 'down' | 'stable', isPositive: boolean = true) => {
    const iconClass = `w-4 h-4 ${
      direction === 'up' 
        ? isPositive ? 'text-green-500' : 'text-red-500'
        : direction === 'down'
        ? isPositive ? 'text-red-500' : 'text-green-500'
        : 'text-gray-400'
    }`;
    
    switch (direction) {
      case 'up':
        return <TrendingUp className={iconClass} />;
      case 'down':
        return <TrendingDown className={iconClass} />;
      default:
        return <Minus className={iconClass} />;
    }
  };

  // Get performance status color
  const getPerformanceColor = (value: number, thresholds: { good: number; warning: number }) => {
    if (value <= thresholds.good) return 'text-green-600';
    if (value <= thresholds.warning) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4
    }).format(amount);
  };

  // Format number with commas
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  // Setup polling
  useEffect(() => {
    fetchMetrics();
    
    const interval = setInterval(fetchMetrics, updateInterval);
    return () => clearInterval(interval);
  }, [fetchMetrics, updateInterval]);

  if (isLoading && !metrics) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-8">
          <div className="flex items-center space-x-2">
            <Activity className="w-5 h-5 animate-spin" />
            <span>Loading metrics...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !metrics) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-8">
          <div className="text-center">
            <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
            <p className="text-red-600 mb-2">Failed to load metrics</p>
            <p className="text-sm text-gray-500 mb-4">{error}</p>
            <Button onClick={fetchMetrics} size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!metrics) return null;

  // Calculate trends
  const latencyTrend = previousMetrics 
    ? calculateTrend(metrics.latency.average_ms, previousMetrics.latency.average_ms)
    : { value: metrics.latency.average_ms, change: 0, direction: 'stable' as const };
    
  const errorRateTrend = previousMetrics
    ? calculateTrend(metrics.error_rate, previousMetrics.error_rate)
    : { value: metrics.error_rate, change: 0, direction: 'stable' as const };
    
  const cacheHitTrend = previousMetrics
    ? calculateTrend(metrics.cache_performance.hit_rate, previousMetrics.cache_performance.hit_rate)
    : { value: metrics.cache_performance.hit_rate, change: 0, direction: 'stable' as const };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Activity className="w-5 h-5" />
          <h3 className="text-lg font-semibold">Performance Metrics</h3>
          {isConnected ? (
            <Wifi className="w-4 h-4 text-green-500" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-500" />
          )}
        </div>
        <div className="flex items-center space-x-2">
          {lastUpdated && (
            <span className="text-xs text-gray-500">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button onClick={fetchMetrics} variant="ghost" size="sm">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Response Time */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500">Response Time</p>
                <p className={`text-lg font-bold ${getPerformanceColor(latencyTrend.value, { good: 1000, warning: 3000 })}`}>
                  {latencyTrend.value.toFixed(0)}ms
                </p>
                {latencyTrend.change > 0 && (
                  <div className="flex items-center space-x-1">
                    {getTrendIcon(latencyTrend.direction, false)}
                    <span className="text-xs text-gray-500">
                      {latencyTrend.change.toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
              <Clock className="w-6 h-6 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        {/* Cache Hit Rate */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500">Cache Hit Rate</p>
                <p className={`text-lg font-bold ${getPerformanceColor(100 - cacheHitTrend.value * 100, { good: 10, warning: 30 })}`}>
                  {(cacheHitTrend.value * 100).toFixed(1)}%
                </p>
                {cacheHitTrend.change > 0 && (
                  <div className="flex items-center space-x-1">
                    {getTrendIcon(cacheHitTrend.direction, true)}
                    <span className="text-xs text-gray-500">
                      {cacheHitTrend.change.toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
              <Database className="w-6 h-6 text-green-500" />
            </div>
          </CardContent>
        </Card>

        {/* Error Rate */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500">Error Rate</p>
                <p className={`text-lg font-bold ${getPerformanceColor(errorRateTrend.value, { good: 1, warning: 5 })}`}>
                  {errorRateTrend.value.toFixed(1)}%
                </p>
                {errorRateTrend.change > 0 && (
                  <div className="flex items-center space-x-1">
                    {getTrendIcon(errorRateTrend.direction, false)}
                    <span className="text-xs text-gray-500">
                      {errorRateTrend.change.toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
              <AlertTriangle className="w-6 h-6 text-red-500" />
            </div>
          </CardContent>
        </Card>

        {/* Requests/Min */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500">Requests/Min</p>
                <p className="text-lg font-bold text-purple-600">
                  {metrics.requests_per_minute.toFixed(1)}
                </p>
              </div>
              <Zap className="w-6 h-6 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Token Usage */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Token Usage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Total Tokens</span>
            <span className="font-semibold">{formatNumber(metrics.token_usage.total_tokens)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Estimated Cost</span>
            <span className="font-semibold">{formatCurrency(metrics.token_usage.total_cost)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Avg Tokens/Request</span>
            <span className="font-semibold">{metrics.token_usage.average_tokens_per_request.toFixed(0)}</span>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Metrics (if enabled) */}
      {showDetailed && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Latency Percentiles */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Latency Percentiles</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">50th percentile</span>
                <span className="font-semibold">{metrics.latency.percentiles.p50.toFixed(0)}ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">95th percentile</span>
                <span className="font-semibold">{metrics.latency.percentiles.p95.toFixed(0)}ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">99th percentile</span>
                <span className="font-semibold">{metrics.latency.percentiles.p99.toFixed(0)}ms</span>
              </div>
            </CardContent>
          </Card>

          {/* Cache Performance */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Cache Performance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Hit Rate</span>
                <div className="flex items-center space-x-2">
                  <span className="font-semibold">{(metrics.cache_performance.hit_rate * 100).toFixed(1)}%</span>
                  <div className="w-16">
                    <Progress value={metrics.cache_performance.hit_rate * 100} className="h-2" />
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Avg Response Time</span>
                <span className="font-semibold">{metrics.cache_performance.avg_response_time_ms.toFixed(1)}ms</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Status Indicators */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${metrics.latency.average_ms < 1000 ? 'bg-green-500' : metrics.latency.average_ms < 3000 ? 'bg-yellow-500' : 'bg-red-500'}`} />
            <span>Response Time</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${metrics.cache_performance.hit_rate > 0.8 ? 'bg-green-500' : metrics.cache_performance.hit_rate > 0.6 ? 'bg-yellow-500' : 'bg-red-500'}`} />
            <span>Cache Performance</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${metrics.error_rate < 1 ? 'bg-green-500' : metrics.error_rate < 5 ? 'bg-yellow-500' : 'bg-red-500'}`} />
            <span>Error Rate</span>
          </div>
        </div>
        <span>Session: {sessionId.slice(-8)}</span>
      </div>
    </div>
  );
};

export default RealTimeMetricsDisplay;