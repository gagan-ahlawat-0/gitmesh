/**
 * Performance Indicators Component
 * 
 * Displays performance alerts, warnings, and status indicators
 * with real-time updates and threshold-based notifications.
 */

import React, { useState, useEffect } from 'react';
import { Alert, AlertDescription } from '../ui/alert';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Zap, 
  Database,
  TrendingUp,
  TrendingDown,
  X,
  Bell,
  BellOff
} from 'lucide-react';

interface PerformanceAlert {
  id: string;
  type: 'warning' | 'error' | 'info' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  metric: string;
  currentValue: number;
  threshold: number;
  dismissed?: boolean;
}

interface PerformanceThresholds {
  latency: {
    warning: number;
    critical: number;
  };
  errorRate: {
    warning: number;
    critical: number;
  };
  cacheHitRate: {
    warning: number;
    critical: number;
  };
  tokenCost: {
    warning: number;
    critical: number;
  };
}

interface PerformanceIndicatorsProps {
  sessionId: string;
  metrics?: {
    latency: number;
    errorRate: number;
    cacheHitRate: number;
    tokenCost: number;
    requestsPerMinute: number;
  };
  thresholds?: Partial<PerformanceThresholds>;
  showNotifications?: boolean;
  onAlertDismiss?: (alertId: string) => void;
  className?: string;
}

const DEFAULT_THRESHOLDS: PerformanceThresholds = {
  latency: { warning: 2000, critical: 5000 }, // milliseconds
  errorRate: { warning: 2, critical: 5 }, // percentage
  cacheHitRate: { warning: 70, critical: 50 }, // percentage
  tokenCost: { warning: 1.0, critical: 5.0 } // dollars
};

export const PerformanceIndicators: React.FC<PerformanceIndicatorsProps> = ({
  sessionId,
  metrics,
  thresholds = {},
  showNotifications = true,
  onAlertDismiss,
  className = ''
}) => {
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([]);
  const [notificationsEnabled, setNotificationsEnabled] = useState(showNotifications);
  const [previousMetrics, setPreviousMetrics] = useState<typeof metrics | null>(null);

  // Merge default thresholds with provided ones
  const mergedThresholds: PerformanceThresholds = {
    latency: { ...DEFAULT_THRESHOLDS.latency, ...thresholds.latency },
    errorRate: { ...DEFAULT_THRESHOLDS.errorRate, ...thresholds.errorRate },
    cacheHitRate: { ...DEFAULT_THRESHOLDS.cacheHitRate, ...thresholds.cacheHitRate },
    tokenCost: { ...DEFAULT_THRESHOLDS.tokenCost, ...thresholds.tokenCost }
  };

  // Generate alerts based on current metrics
  const generateAlerts = (currentMetrics: typeof metrics) => {
    if (!currentMetrics) return [];

    const newAlerts: PerformanceAlert[] = [];
    const timestamp = new Date();

    // Latency alerts
    if (currentMetrics.latency >= mergedThresholds.latency.critical) {
      newAlerts.push({
        id: `latency-critical-${timestamp.getTime()}`,
        type: 'error',
        title: 'Critical Response Time',
        message: `Response time is ${currentMetrics.latency.toFixed(0)}ms, exceeding critical threshold of ${mergedThresholds.latency.critical}ms`,
        timestamp,
        metric: 'latency',
        currentValue: currentMetrics.latency,
        threshold: mergedThresholds.latency.critical
      });
    } else if (currentMetrics.latency >= mergedThresholds.latency.warning) {
      newAlerts.push({
        id: `latency-warning-${timestamp.getTime()}`,
        type: 'warning',
        title: 'High Response Time',
        message: `Response time is ${currentMetrics.latency.toFixed(0)}ms, exceeding warning threshold of ${mergedThresholds.latency.warning}ms`,
        timestamp,
        metric: 'latency',
        currentValue: currentMetrics.latency,
        threshold: mergedThresholds.latency.warning
      });
    }

    // Error rate alerts
    if (currentMetrics.errorRate >= mergedThresholds.errorRate.critical) {
      newAlerts.push({
        id: `error-rate-critical-${timestamp.getTime()}`,
        type: 'error',
        title: 'Critical Error Rate',
        message: `Error rate is ${currentMetrics.errorRate.toFixed(1)}%, exceeding critical threshold of ${mergedThresholds.errorRate.critical}%`,
        timestamp,
        metric: 'errorRate',
        currentValue: currentMetrics.errorRate,
        threshold: mergedThresholds.errorRate.critical
      });
    } else if (currentMetrics.errorRate >= mergedThresholds.errorRate.warning) {
      newAlerts.push({
        id: `error-rate-warning-${timestamp.getTime()}`,
        type: 'warning',
        title: 'High Error Rate',
        message: `Error rate is ${currentMetrics.errorRate.toFixed(1)}%, exceeding warning threshold of ${mergedThresholds.errorRate.warning}%`,
        timestamp,
        metric: 'errorRate',
        currentValue: currentMetrics.errorRate,
        threshold: mergedThresholds.errorRate.warning
      });
    }

    // Cache hit rate alerts (lower is worse)
    const cacheHitRatePercent = currentMetrics.cacheHitRate * 100;
    if (cacheHitRatePercent <= mergedThresholds.cacheHitRate.critical) {
      newAlerts.push({
        id: `cache-critical-${timestamp.getTime()}`,
        type: 'error',
        title: 'Critical Cache Performance',
        message: `Cache hit rate is ${cacheHitRatePercent.toFixed(1)}%, below critical threshold of ${mergedThresholds.cacheHitRate.critical}%`,
        timestamp,
        metric: 'cacheHitRate',
        currentValue: cacheHitRatePercent,
        threshold: mergedThresholds.cacheHitRate.critical
      });
    } else if (cacheHitRatePercent <= mergedThresholds.cacheHitRate.warning) {
      newAlerts.push({
        id: `cache-warning-${timestamp.getTime()}`,
        type: 'warning',
        title: 'Low Cache Performance',
        message: `Cache hit rate is ${cacheHitRatePercent.toFixed(1)}%, below warning threshold of ${mergedThresholds.cacheHitRate.warning}%`,
        timestamp,
        metric: 'cacheHitRate',
        currentValue: cacheHitRatePercent,
        threshold: mergedThresholds.cacheHitRate.warning
      });
    }

    // Token cost alerts
    if (currentMetrics.tokenCost >= mergedThresholds.tokenCost.critical) {
      newAlerts.push({
        id: `cost-critical-${timestamp.getTime()}`,
        type: 'error',
        title: 'Critical Token Cost',
        message: `Token cost is $${currentMetrics.tokenCost.toFixed(2)}, exceeding critical threshold of $${mergedThresholds.tokenCost.critical}`,
        timestamp,
        metric: 'tokenCost',
        currentValue: currentMetrics.tokenCost,
        threshold: mergedThresholds.tokenCost.critical
      });
    } else if (currentMetrics.tokenCost >= mergedThresholds.tokenCost.warning) {
      newAlerts.push({
        id: `cost-warning-${timestamp.getTime()}`,
        type: 'warning',
        title: 'High Token Cost',
        message: `Token cost is $${currentMetrics.tokenCost.toFixed(2)}, exceeding warning threshold of $${mergedThresholds.tokenCost.warning}`,
        timestamp,
        metric: 'tokenCost',
        currentValue: currentMetrics.tokenCost,
        threshold: mergedThresholds.tokenCost.warning
      });
    }

    // Performance improvement alerts
    if (previousMetrics) {
      if (currentMetrics.latency < previousMetrics.latency * 0.8) {
        newAlerts.push({
          id: `latency-improved-${timestamp.getTime()}`,
          type: 'success',
          title: 'Response Time Improved',
          message: `Response time improved by ${(((previousMetrics.latency - currentMetrics.latency) / previousMetrics.latency) * 100).toFixed(1)}%`,
          timestamp,
          metric: 'latency',
          currentValue: currentMetrics.latency,
          threshold: previousMetrics.latency
        });
      }

      if (currentMetrics.cacheHitRate > previousMetrics.cacheHitRate * 1.1) {
        newAlerts.push({
          id: `cache-improved-${timestamp.getTime()}`,
          type: 'success',
          title: 'Cache Performance Improved',
          message: `Cache hit rate improved to ${(currentMetrics.cacheHitRate * 100).toFixed(1)}%`,
          timestamp,
          metric: 'cacheHitRate',
          currentValue: currentMetrics.cacheHitRate * 100,
          threshold: previousMetrics.cacheHitRate * 100
        });
      }
    }

    return newAlerts;
  };

  // Get alert icon
  const getAlertIcon = (type: PerformanceAlert['type']) => {
    switch (type) {
      case 'error':
        return <AlertTriangle className="w-4 h-4" />;
      case 'warning':
        return <Clock className="w-4 h-4" />;
      case 'success':
        return <CheckCircle className="w-4 h-4" />;
      default:
        return <Zap className="w-4 h-4" />;
    }
  };

  // Get alert variant
  const getAlertVariant = (type: PerformanceAlert['type']) => {
    switch (type) {
      case 'error':
        return 'destructive';
      case 'warning':
        return 'default';
      case 'success':
        return 'default';
      default:
        return 'default';
    }
  };

  // Dismiss alert
  const dismissAlert = (alertId: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, dismissed: true } : alert
    ));
    
    if (onAlertDismiss) {
      onAlertDismiss(alertId);
    }
  };

  // Clear all alerts
  const clearAllAlerts = () => {
    setAlerts(prev => prev.map(alert => ({ ...alert, dismissed: true })));
  };

  // Update alerts when metrics change
  useEffect(() => {
    if (metrics && notificationsEnabled) {
      const newAlerts = generateAlerts(metrics);
      
      // Only add alerts that don't already exist (to prevent duplicates)
      const existingAlertTypes = new Set(alerts.map(a => `${a.metric}-${a.type}`));
      const uniqueNewAlerts = newAlerts.filter(alert => 
        !existingAlertTypes.has(`${alert.metric}-${alert.type}`)
      );
      
      if (uniqueNewAlerts.length > 0) {
        setAlerts(prev => [...prev, ...uniqueNewAlerts]);
      }
      
      setPreviousMetrics(metrics);
    }
  }, [metrics, notificationsEnabled]);

  // Auto-dismiss success alerts after 5 seconds
  useEffect(() => {
    const successAlerts = alerts.filter(alert => alert.type === 'success' && !alert.dismissed);
    
    if (successAlerts.length > 0) {
      const timer = setTimeout(() => {
        successAlerts.forEach(alert => dismissAlert(alert.id));
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [alerts]);

  const activeAlerts = alerts.filter(alert => !alert.dismissed);
  const criticalAlerts = activeAlerts.filter(alert => alert.type === 'error');
  const warningAlerts = activeAlerts.filter(alert => alert.type === 'warning');

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <h3 className="text-lg font-semibold">Performance Status</h3>
          {criticalAlerts.length > 0 && (
            <Badge variant="destructive">{criticalAlerts.length} Critical</Badge>
          )}
          {warningAlerts.length > 0 && (
            <Badge variant="secondary">{warningAlerts.length} Warning</Badge>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => setNotificationsEnabled(!notificationsEnabled)}
            variant="ghost"
            size="sm"
          >
            {notificationsEnabled ? (
              <Bell className="w-4 h-4" />
            ) : (
              <BellOff className="w-4 h-4" />
            )}
          </Button>
          {activeAlerts.length > 0 && (
            <Button onClick={clearAllAlerts} variant="ghost" size="sm">
              Clear All
            </Button>
          )}
        </div>
      </div>

      {/* Performance Status Overview */}
      {metrics && (
        <Card>
          <CardContent className="p-4">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Latency Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  metrics.latency < mergedThresholds.latency.warning 
                    ? 'bg-green-500' 
                    : metrics.latency < mergedThresholds.latency.critical 
                    ? 'bg-yellow-500' 
                    : 'bg-red-500'
                }`} />
                <div>
                  <p className="text-xs text-gray-500">Latency</p>
                  <p className="text-sm font-semibold">{metrics.latency.toFixed(0)}ms</p>
                </div>
              </div>

              {/* Error Rate Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  metrics.errorRate < mergedThresholds.errorRate.warning 
                    ? 'bg-green-500' 
                    : metrics.errorRate < mergedThresholds.errorRate.critical 
                    ? 'bg-yellow-500' 
                    : 'bg-red-500'
                }`} />
                <div>
                  <p className="text-xs text-gray-500">Error Rate</p>
                  <p className="text-sm font-semibold">{metrics.errorRate.toFixed(1)}%</p>
                </div>
              </div>

              {/* Cache Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  metrics.cacheHitRate * 100 > mergedThresholds.cacheHitRate.warning 
                    ? 'bg-green-500' 
                    : metrics.cacheHitRate * 100 > mergedThresholds.cacheHitRate.critical 
                    ? 'bg-yellow-500' 
                    : 'bg-red-500'
                }`} />
                <div>
                  <p className="text-xs text-gray-500">Cache Hit</p>
                  <p className="text-sm font-semibold">{(metrics.cacheHitRate * 100).toFixed(1)}%</p>
                </div>
              </div>

              {/* Cost Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  metrics.tokenCost < mergedThresholds.tokenCost.warning 
                    ? 'bg-green-500' 
                    : metrics.tokenCost < mergedThresholds.tokenCost.critical 
                    ? 'bg-yellow-500' 
                    : 'bg-red-500'
                }`} />
                <div>
                  <p className="text-xs text-gray-500">Cost</p>
                  <p className="text-sm font-semibold">${metrics.tokenCost.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <div className="space-y-2">
          {activeAlerts.map((alert) => (
            <Alert key={alert.id} variant={getAlertVariant(alert.type)}>
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-2">
                  {getAlertIcon(alert.type)}
                  <div>
                    <h4 className="font-semibold">{alert.title}</h4>
                    <AlertDescription>{alert.message}</AlertDescription>
                    <p className="text-xs text-gray-500 mt-1">
                      {alert.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                <Button
                  onClick={() => dismissAlert(alert.id)}
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </Alert>
          ))}
        </div>
      )}

      {/* No Alerts State */}
      {activeAlerts.length === 0 && notificationsEnabled && (
        <Card>
          <CardContent className="flex items-center justify-center py-8">
            <div className="text-center">
              <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <p className="text-green-600 font-semibold">All Systems Operational</p>
              <p className="text-sm text-gray-500">No performance issues detected</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PerformanceIndicators;