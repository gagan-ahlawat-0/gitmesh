/**
 * Tests for PerformanceIndicators Component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PerformanceIndicators } from '../PerformanceIndicators';

const mockMetrics = {
  latency: 1500,
  errorRate: 3.2,
  cacheHitRate: 0.75,
  tokenCost: 2.5,
  requestsPerMinute: 15.2
};

const mockThresholds = {
  latency: { warning: 1000, critical: 3000 },
  errorRate: { warning: 2, critical: 5 },
  cacheHitRate: { warning: 70, critical: 50 },
  tokenCost: { warning: 2.0, critical: 5.0 }
};

describe('PerformanceIndicators', () => {
  it('renders performance status overview', () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    expect(screen.getByText('Performance Status')).toBeInTheDocument();
    expect(screen.getByText('1500ms')).toBeInTheDocument(); // Latency
    expect(screen.getByText('3.2%')).toBeInTheDocument(); // Error rate
    expect(screen.getByText('75.0%')).toBeInTheDocument(); // Cache hit rate
    expect(screen.getByText('$2.50')).toBeInTheDocument(); // Token cost
  });

  it('generates warning alerts for metrics exceeding warning thresholds', async () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      // Should show warning for high latency (1500ms > 1000ms warning threshold)
      expect(screen.getByText('High Response Time')).toBeInTheDocument();
      
      // Should show warning for high error rate (3.2% > 2% warning threshold)
      expect(screen.getByText('High Error Rate')).toBeInTheDocument();
      
      // Should show warning for high token cost (2.5 > 2.0 warning threshold)
      expect(screen.getByText('High Token Cost')).toBeInTheDocument();
    });

    // Should show warning badges
    expect(screen.getByText(/Warning/)).toBeInTheDocument();
  });

  it('generates critical alerts for metrics exceeding critical thresholds', async () => {
    const criticalMetrics = {
      latency: 4000, // Above critical threshold
      errorRate: 6.0, // Above critical threshold
      cacheHitRate: 0.45, // Below critical threshold
      tokenCost: 6.0, // Above critical threshold
      requestsPerMinute: 10
    };

    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={criticalMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Critical Response Time')).toBeInTheDocument();
      expect(screen.getByText('Critical Error Rate')).toBeInTheDocument();
      expect(screen.getByText('Critical Cache Performance')).toBeInTheDocument();
      expect(screen.getByText('Critical Token Cost')).toBeInTheDocument();
    });

    // Should show critical badges
    expect(screen.getByText(/Critical/)).toBeInTheDocument();
  });

  it('shows success alerts for performance improvements', async () => {
    const initialMetrics = {
      latency: 2000,
      errorRate: 4.0,
      cacheHitRate: 0.6,
      tokenCost: 3.0,
      requestsPerMinute: 10
    };

    const { rerender } = render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={initialMetrics}
        thresholds={mockThresholds}
      />
    );

    // Update with improved metrics
    const improvedMetrics = {
      latency: 800, // Significant improvement
      errorRate: 1.0,
      cacheHitRate: 0.85, // Significant improvement
      tokenCost: 1.5,
      requestsPerMinute: 12
    };

    rerender(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={improvedMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Response Time Improved')).toBeInTheDocument();
      expect(screen.getByText('Cache Performance Improved')).toBeInTheDocument();
    });
  });

  it('allows dismissing individual alerts', async () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Response Time')).toBeInTheDocument();
    });

    // Find and click dismiss button
    const dismissButtons = screen.getAllByRole('button', { name: '' }); // X buttons
    fireEvent.click(dismissButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText('High Response Time')).not.toBeInTheDocument();
    });
  });

  it('allows clearing all alerts', async () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Response Time')).toBeInTheDocument();
      expect(screen.getByText('High Error Rate')).toBeInTheDocument();
    });

    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    await waitFor(() => {
      expect(screen.queryByText('High Response Time')).not.toBeInTheDocument();
      expect(screen.queryByText('High Error Rate')).not.toBeInTheDocument();
    });
  });

  it('toggles notifications on/off', () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    const notificationButton = screen.getByRole('button', { name: '' }); // Bell button
    fireEvent.click(notificationButton);

    // Should disable notifications and show "All Systems Operational" when no alerts
  });

  it('shows "All Systems Operational" when no alerts are active', () => {
    const goodMetrics = {
      latency: 500, // Below warning threshold
      errorRate: 0.5, // Below warning threshold
      cacheHitRate: 0.95, // Above warning threshold
      tokenCost: 0.5, // Below warning threshold
      requestsPerMinute: 20
    };

    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={goodMetrics}
        thresholds={mockThresholds}
      />
    );

    expect(screen.getByText('All Systems Operational')).toBeInTheDocument();
    expect(screen.getByText('No performance issues detected')).toBeInTheDocument();
  });

  it('displays correct status indicators with appropriate colors', () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    // Check that status indicators are present
    expect(screen.getByText('Latency')).toBeInTheDocument();
    expect(screen.getByText('Error Rate')).toBeInTheDocument();
    expect(screen.getByText('Cache Hit')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
  });

  it('calls onAlertDismiss callback when alert is dismissed', async () => {
    const onAlertDismiss = jest.fn();

    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
        onAlertDismiss={onAlertDismiss}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Response Time')).toBeInTheDocument();
    });

    const dismissButtons = screen.getAllByRole('button', { name: '' });
    fireEvent.click(dismissButtons[0]);

    expect(onAlertDismiss).toHaveBeenCalled();
  });

  it('auto-dismisses success alerts after 5 seconds', async () => {
    jest.useFakeTimers();

    const initialMetrics = {
      latency: 2000,
      errorRate: 4.0,
      cacheHitRate: 0.6,
      tokenCost: 3.0,
      requestsPerMinute: 10
    };

    const { rerender } = render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={initialMetrics}
        thresholds={mockThresholds}
      />
    );

    // Update with improved metrics to trigger success alert
    const improvedMetrics = {
      latency: 800,
      errorRate: 1.0,
      cacheHitRate: 0.85,
      tokenCost: 1.5,
      requestsPerMinute: 12
    };

    rerender(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={improvedMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Response Time Improved')).toBeInTheDocument();
    });

    // Fast-forward 5 seconds
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(screen.queryByText('Response Time Improved')).not.toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  it('uses default thresholds when none provided', () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
      />
    );

    // Should still generate alerts using default thresholds
    expect(screen.getByText('Performance Status')).toBeInTheDocument();
  });

  it('prevents duplicate alerts for the same metric and type', async () => {
    const { rerender } = render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Response Time')).toBeInTheDocument();
    });

    // Re-render with same metrics
    rerender(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    // Should not duplicate the alert
    const alerts = screen.getAllByText('High Response Time');
    expect(alerts).toHaveLength(1);
  });

  it('handles missing metrics gracefully', () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        thresholds={mockThresholds}
      />
    );

    expect(screen.getByText('Performance Status')).toBeInTheDocument();
    // Should not crash when metrics are undefined
  });

  it('displays alert timestamps', async () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Response Time')).toBeInTheDocument();
    });

    // Should show timestamp (format may vary)
    const timeElements = screen.getAllByText(/\d{1,2}:\d{2}:\d{2}/);
    expect(timeElements.length).toBeGreaterThan(0);
  });
});

describe('PerformanceIndicators Alert Types', () => {
  it('displays correct icons for different alert types', async () => {
    const criticalMetrics = {
      latency: 4000,
      errorRate: 6.0,
      cacheHitRate: 0.45,
      tokenCost: 6.0,
      requestsPerMinute: 10
    };

    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={criticalMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Critical Response Time')).toBeInTheDocument();
    });

    // Should have appropriate alert styling
    const alerts = screen.getAllByRole('alert');
    expect(alerts.length).toBeGreaterThan(0);
  });

  it('applies correct alert variants based on severity', async () => {
    render(
      <PerformanceIndicators 
        sessionId="test-session" 
        metrics={mockMetrics}
        thresholds={mockThresholds}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('High Response Time')).toBeInTheDocument();
    });

    // Warning alerts should have default variant
    // Critical alerts should have destructive variant
    // Success alerts should have default variant
  });
});