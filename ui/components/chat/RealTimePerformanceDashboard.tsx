"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  Clock, 
  Database, 
  Zap, 
  TrendingUp, 
  TrendingDown,
  Minus,
  Info,
  Wifi,
  WifiOff,
  RefreshCw,
  AlertTriangle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Alert, AlertDescription } from '@/components/ui/alert';

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

interface RealTimePerformanceDashboardProps {
  sessionId: string;
  userId?: string;
  className?: string;
  compact?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  showDetailedView?: boolean;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  trend?: 'up' | 'down' | 'stable';
  color?: 'green' | 'blue' | 'orange' | 'red' | 'gray';
  tooltip?: string;
  progress?: number;
  loading?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  icon: Icon,
  trend,
  color = 'blue',
  tooltip,
  progress,
  loading = false
}) => {
  const getColorClasses = () => {
    switch (color) {
      case 'green':
        return {
          icon: 'text-green-500',
          bg: 'bg-green-50 dark:bg-green-950',
          border: 'border-green-200 dark:border-green-800'
        };
      case 'orange':
        return {
          icon: 'text-orange-500',
          bg: 'bg-orange-50 dark:bg-orange-950',
          border: 'border-orange-200 dark:border-orange-800'
        };
      case 'red':
        return {
          icon: 'text-red-500',
          bg: 'bg-red-50 dark:bg-red-950',
          border: 'border-red-200 dark:border-red-800'
        };
      case 'gray':
        return {
          icon: 'text-gray-500',
          bg: 'bg-gray-50 dark:bg-gray-950',
          border: 'border-gray-200 dark:border-gray-800'
        };
      default:
        return {
          icon: 'text-blue-500',
          bg: 'bg-blue-50 dark:bg-blue-950',
          border: 'border-blue-200 dark:border-blue-800'
        };
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp size={12} className="text-green-500" />;
      case 'down':
        return <TrendingDown size={12} className="text-red-500" />;
      default:
        return <Minus size={12} className="text-gray-400" />;
    }
  };

  const colorClasses = getColorClasses();

  const content = (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "p-3 rounded-lg border transition-colors relative",
        colorClasses.bg,
        colorClasses.border
      )}
    >
      {loading && (
        <div className="absolute inset-0 bg-white/50 dark:bg-black/50 rounded-lg flex items-center justify-center">
          <RefreshCw size={16} className="animate-spin text-muted-foreground" />
        </div>
      )}
      
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={16} className={colorClasses.icon} />
          <span className="text-xs font-medium text-muted-foreground">
            {title}
          </span>
        </div>
        {trend && getTrendIcon()}
      </div>

      <div className="flex items-baseline gap-1">
        <span className="text-lg font-semibold">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </span>
        {unit && (
          <span className="text-xs text-muted-foreground">
            {unit}
          </span>
        )}
      </div>

      {progress !== undefined && (
        <div className="mt-2">
          <Progress value={progress} className="h-1" />
        </div>
      )}
    </motion.div>
  );

  if (tooltip) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            {content}
          </TooltipTrigger>
          <TooltipContent>
            <p className="text-xs">{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return content;
};

export const RealTimePerformanceDashboard: React.FC<RealTimePerformanceDashboardProps> = ({
  sessionId,
  userId,
  className,
  compact = false,
  autoRefresh = true,
  refreshInterval = 5000,
  showDetailedView = false
}) => {
  const [metrics, setMetrics] = useState<RealTimeMetrics | null>(null);
  const [previousMetrics, setPreviousMetrics] = useState<RealTimeMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Fetch metrics from backend
  const fetchMetrics = useCallback(async () => {
    if (!sessionId) return;

    try {
      setError(null);
      const response = await fetch(`/api/v1/performance/realtime/${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch metrics: ${response.statusText}`);
      }

      const data: RealTimeMetrics = await response.json();
      
      // Store previous metrics for trend calculation
      if (metrics) {
        setPreviousMetrics(metrics);
      }
      
      setMetrics(data);
      setConnected(true);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
      setConnected(false);
      setLoading(false);
    }
  }, [sessionId, metrics]);

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh || !sessionId) return;

    // Initial fetch
    fetchMetrics();

    // Set up interval
    const interval = setInterval(fetchMetrics, refreshInterval);

    return () => clearInterval(interval);
  }, [fetchMetrics, autoRefresh, refreshInterval, sessionId]);

  // Calculate trends
  const getTrend = (current: number, previous: number): 'up' | 'down' | 'stable' => {
    if (!previous || current === previous) return 'stable';
    return current > previous ? 'up' : 'down';
  };

  // Format values
  const formatLatency = (ms: number) => {
    if (ms < 1000) return Math.round(ms);
    return `${(ms / 1000).toFixed(1)}k`;
  };

  const formatTokens = (tokens: number) => {
    if (tokens < 1000) return tokens;
    if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}k`;
    return `${(tokens / 1000000).toFixed(1)}M`;
  };

  const formatCost = (cost: number) => {
    return `$${cost.toFixed(4)}`;
  };

  // Handle manual refresh
  const handleRefresh = () => {
    setLoading(true);
    fetchMetrics();
  };

  if (error) {
    return (
      <Alert className={cn("border-red-200 bg-red-50 dark:bg-red-950", className)}>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>Failed to load performance metrics: {error}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="ml-2"
          >
            <RefreshCw size={14} className="mr-1" />
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!metrics && loading) {
    return (
      <div className={cn("text-center py-4", className)}>
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <RefreshCw size={16} className="animate-spin" />
          Loading performance metrics...
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className={cn("text-center py-4", className)}>
        <div className="text-sm text-muted-foreground">
          No performance data available
        </div>
      </div>
    );
  }

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn("flex items-center gap-4 text-xs text-muted-foreground", className)}
      >
        <div className="flex items-center gap-1">
          <Clock size={12} />
          <span>{formatLatency(metrics.latency.average_ms)}ms</span>
        </div>
        <div className="flex items-center gap-1">
          <Zap size={12} />
          <span>{formatTokens(metrics.token_usage.total_tokens)} tokens</span>
        </div>
        <div className="flex items-center gap-1">
          <Database size={12} />
          <span>{Math.round(metrics.cache_performance.hit_rate * 100)}% cache</span>
        </div>
        <div className="flex items-center gap-1">
          <Activity size={12} />
          <span>{metrics.requests_per_minute.toFixed(1)} req/min</span>
        </div>
        <div className="flex items-center gap-1">
          {connected ? (
            <Wifi size={12} className="text-green-500" />
          ) : (
            <WifiOff size={12} className="text-red-500" />
          )}
        </div>
      </motion.div>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className={cn("space-y-4", className)}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium">Real-Time Performance</h3>
            {connected ? (
              <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                <Wifi size={10} className="mr-1" />
                Live
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs bg-red-50 text-red-700 border-red-200">
                <WifiOff size={10} className="mr-1" />
                Disconnected
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-muted-foreground">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={loading}
            >
              <RefreshCw size={14} className={cn("mr-1", loading && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Main Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            title="Avg Response Time"
            value={formatLatency(metrics.latency.average_ms)}
            unit="ms"
            icon={Clock}
            color={metrics.latency.average_ms < 2000 ? 'green' : metrics.latency.average_ms < 5000 ? 'orange' : 'red'}
            trend={previousMetrics ? getTrend(metrics.latency.average_ms, previousMetrics.latency.average_ms) : 'stable'}
            tooltip="Average response time for requests in this session"
            loading={loading}
          />

          <MetricCard
            title="Total Tokens"
            value={formatTokens(metrics.token_usage.total_tokens)}
            unit="tokens"
            icon={Zap}
            color="blue"
            trend={previousMetrics ? getTrend(metrics.token_usage.total_tokens, previousMetrics.token_usage.total_tokens) : 'stable'}
            tooltip={`Total cost: ${formatCost(metrics.token_usage.total_cost)}`}
            loading={loading}
          />

          <MetricCard
            title="Cache Hit Rate"
            value={Math.round(metrics.cache_performance.hit_rate * 100)}
            unit="%"
            icon={Database}
            color={metrics.cache_performance.hit_rate > 0.8 ? 'green' : metrics.cache_performance.hit_rate > 0.5 ? 'orange' : 'red'}
            progress={metrics.cache_performance.hit_rate * 100}
            tooltip="Percentage of requests served from cache"
            loading={loading}
          />

          <MetricCard
            title="Requests/Min"
            value={metrics.requests_per_minute.toFixed(1)}
            unit="req/min"
            icon={Activity}
            color={metrics.requests_per_minute > 10 ? 'green' : metrics.requests_per_minute > 5 ? 'orange' : 'gray'}
            trend={previousMetrics ? getTrend(metrics.requests_per_minute, previousMetrics.requests_per_minute) : 'stable'}
            tooltip="Current request rate"
            loading={loading}
          />
        </div>

        {/* Detailed View */}
        {showDetailedView && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="space-y-3"
          >
            {/* Latency Percentiles */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Latency Distribution</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-lg font-semibold">{formatLatency(metrics.latency.percentiles.p50)}ms</div>
                    <div className="text-xs text-muted-foreground">50th percentile</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold">{formatLatency(metrics.latency.percentiles.p95)}ms</div>
                    <div className="text-xs text-muted-foreground">95th percentile</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold">{formatLatency(metrics.latency.percentiles.p99)}ms</div>
                    <div className="text-xs text-muted-foreground">99th percentile</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Additional Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <MetricCard
                title="Error Rate"
                value={metrics.error_rate.toFixed(1)}
                unit="%"
                icon={Info}
                color={metrics.error_rate === 0 ? 'green' : metrics.error_rate < 5 ? 'orange' : 'red'}
                tooltip="Percentage of requests that resulted in errors"
                loading={loading}
              />

              <MetricCard
                title="Avg Tokens/Request"
                value={Math.round(metrics.token_usage.average_tokens_per_request)}
                unit="tokens"
                icon={Zap}
                color="blue"
                tooltip="Average tokens consumed per request"
                loading={loading}
              />

              <MetricCard
                title="Cache Response Time"
                value={formatLatency(metrics.cache_performance.avg_response_time_ms)}
                unit="ms"
                icon={Database}
                color={metrics.cache_performance.avg_response_time_ms < 100 ? 'green' : 'orange'}
                tooltip="Average response time for cached requests"
                loading={loading}
              />
            </div>

            {/* Session Summary */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Session Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Total Requests:</span>
                  <span>{metrics.token_usage.request_count}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Total Cost:</span>
                  <span>{formatCost(metrics.token_usage.total_cost)}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Session ID:</span>
                  <span className="font-mono text-xs">{sessionId.slice(0, 8)}...</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default RealTimePerformanceDashboard;