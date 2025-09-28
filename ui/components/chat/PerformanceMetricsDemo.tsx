"use client";

import React, { useState } from 'react';
import RealTimePerformanceDashboard from './RealTimePerformanceDashboard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Demo component to showcase the Real-Time Performance Dashboard
 * This demonstrates the functionality without requiring a full backend setup
 */
export const PerformanceMetricsDemo: React.FC = () => {
  const [sessionId, setSessionId] = useState('demo-session-123');
  const [showDetailed, setShowDetailed] = useState(false);
  const [compact, setCompact] = useState(false);

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Real-Time Performance Dashboard Demo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4 flex-wrap">
            <Button
              variant={compact ? "default" : "outline"}
              onClick={() => setCompact(!compact)}
            >
              {compact ? "Full View" : "Compact View"}
            </Button>
            <Button
              variant={showDetailed ? "default" : "outline"}
              onClick={() => setShowDetailed(!showDetailed)}
            >
              {showDetailed ? "Hide Details" : "Show Details"}
            </Button>
            <Button
              variant="outline"
              onClick={() => setSessionId(`demo-session-${Date.now()}`)}
            >
              New Session
            </Button>
          </div>

          <div className="text-sm text-muted-foreground">
            Session ID: {sessionId}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Performance Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <RealTimePerformanceDashboard
            sessionId={sessionId}
            userId="demo-user-456"
            compact={compact}
            showDetailedView={showDetailed}
            autoRefresh={true}
            refreshInterval={10000}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Implementation Notes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div>
            <strong>Features Implemented:</strong>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>Real-time metrics fetching from backend API</li>
              <li>WebSocket support for live updates</li>
              <li>Automatic polling fallback when WebSocket fails</li>
              <li>Comprehensive error handling and retry logic</li>
              <li>Responsive design with compact and detailed views</li>
              <li>Color-coded performance indicators</li>
              <li>Progress bars for percentage metrics</li>
              <li>Trend indicators for metric changes</li>
              <li>Session management and cleanup</li>
              <li>Comprehensive test coverage</li>
            </ul>
          </div>
          <div>
            <strong>Metrics Displayed:</strong>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>Response time (average, percentiles)</li>
              <li>Token usage (total, cost, per request)</li>
              <li>Cache performance (hit rate, response time)</li>
              <li>Error rates and request counts</li>
              <li>Real-time connection status</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PerformanceMetricsDemo;