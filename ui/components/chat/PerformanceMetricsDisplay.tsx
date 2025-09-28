"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  Clock, 
  Database, 
  Zap, 
  TrendingUp, 
  TrendingDown,
  Minus,
  Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

export interface PerformanceMetrics {
  latency_ms: number;
  tokens_used: number;
  tokens_per_second: number;
  cache_hit_rate: number;
  cache_miss_rate: number;
  memory_usage_mb: number;
  response_time_ms: number;
  error_count: number;
  request_count: number;
  timestamp: string;
}

interface PerformanceMetricsDisplayProps {
  metrics?: PerformanceMetrics;
  showDetailed?: boolean;
  className?: string;
  compact?: boolean;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  trend?: 'up' | 'down' | 'stable';
  color?: 'green' | 'blue' | 'orange' | 'red' | 'gray';
  tooltip?: string;
  progress?: number; // 0-100 for progress bars
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  icon: Icon,
  trend,
  color = 'blue',
  tooltip,
  progress
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
        "p-3 rounded-lg border transition-colors",
        colorClasses.bg,
        colorClasses.border
      )}
    >
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

export const PerformanceMetricsDisplay: React.FC<PerformanceMetricsDisplayProps> = ({
  metrics,
  showDetailed = false,
  className,
  compact = false
}) => {
  const [previousMetrics, setPreviousMetrics] = useState<PerformanceMetrics | null>(null);

  // Update previous metrics when new metrics arrive
  useEffect(() => {
    if (metrics && previousMetrics) {
      // Only update if metrics are actually different
      if (metrics.timestamp !== previousMetrics.timestamp) {
        setPreviousMetrics(metrics);
      }
    } else if (metrics) {
      setPreviousMetrics(metrics);
    }
  }, [metrics, previousMetrics]);

  // Calculate trends
  const getTrend = (current: number, previous: number): 'up' | 'down' | 'stable' => {
    if (!previous || current === previous) return 'stable';
    return current > previous ? 'up' : 'down';
  };

  // Format values
  const formatLatency = (ms: number) => {
    if (ms < 1000) return `${Math.round(ms)}`;
    return `${(ms / 1000).toFixed(1)}k`;
  };

  const formatTokens = (tokens: number) => {
    if (tokens < 1000) return tokens.toString();
    if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}k`;
    return `${(tokens / 1000000).toFixed(1)}M`;
  };

  const formatMemory = (mb: number) => {
    if (mb < 1024) return `${Math.round(mb)}`;
    return `${(mb / 1024).toFixed(1)}`;
  };

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
          <span>{formatLatency(metrics.latency_ms)}ms</span>
        </div>
        <div className="flex items-center gap-1">
          <Zap size={12} />
          <span>{formatTokens(metrics.tokens_used)} tokens</span>
        </div>
        <div className="flex items-center gap-1">
          <Database size={12} />
          <span>{Math.round(metrics.cache_hit_rate * 100)}% cache</span>
        </div>
        <div className="flex items-center gap-1">
          <Activity size={12} />
          <span>{Math.round(metrics.tokens_per_second)} t/s</span>
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
          <h3 className="text-sm font-medium">Performance Metrics</h3>
          <Badge variant="outline" className="text-xs">
            Live
          </Badge>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            title="Response Time"
            value={formatLatency(metrics.latency_ms)}
            unit="ms"
            icon={Clock}
            color={metrics.latency_ms < 2000 ? 'green' : metrics.latency_ms < 5000 ? 'orange' : 'red'}
            trend={previousMetrics ? getTrend(metrics.latency_ms, previousMetrics.latency_ms) : 'stable'}
            tooltip="Time taken to generate response"
          />

          <MetricCard
            title="Tokens Used"
            value={formatTokens(metrics.tokens_used)}
            unit="tokens"
            icon={Zap}
            color="blue"
            trend={previousMetrics ? getTrend(metrics.tokens_used, previousMetrics.tokens_used) : 'stable'}
            tooltip="Total tokens consumed in this request"
          />

          <MetricCard
            title="Cache Hit Rate"
            value={Math.round(metrics.cache_hit_rate * 100)}
            unit="%"
            icon={Database}
            color={metrics.cache_hit_rate > 0.8 ? 'green' : metrics.cache_hit_rate > 0.5 ? 'orange' : 'red'}
            progress={metrics.cache_hit_rate * 100}
            tooltip="Percentage of requests served from cache"
          />

          <MetricCard
            title="Processing Speed"
            value={Math.round(metrics.tokens_per_second)}
            unit="t/s"
            icon={Activity}
            color={metrics.tokens_per_second > 50 ? 'green' : metrics.tokens_per_second > 20 ? 'orange' : 'red'}
            trend={previousMetrics ? getTrend(metrics.tokens_per_second, previousMetrics.tokens_per_second) : 'stable'}
            tooltip="Tokens processed per second"
          />
        </div>

        {/* Detailed Metrics */}
        {showDetailed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="space-y-3"
          >
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <MetricCard
                title="Memory Usage"
                value={formatMemory(metrics.memory_usage_mb)}
                unit={metrics.memory_usage_mb < 1024 ? 'MB' : 'GB'}
                icon={Database}
                color="gray"
                tooltip="Current memory consumption"
              />

              <MetricCard
                title="Error Count"
                value={metrics.error_count}
                unit="errors"
                icon={Info}
                color={metrics.error_count === 0 ? 'green' : 'red'}
                tooltip="Number of errors in current session"
              />

              <MetricCard
                title="Requests"
                value={metrics.request_count}
                unit="total"
                icon={Activity}
                color="blue"
                tooltip="Total requests in current session"
              />
            </div>

            {/* Additional Details */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Session Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Cache Miss Rate:</span>
                  <span>{Math.round(metrics.cache_miss_rate * 100)}%</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Last Updated:</span>
                  <span>{new Date(metrics.timestamp).toLocaleTimeString()}</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default PerformanceMetricsDisplay;