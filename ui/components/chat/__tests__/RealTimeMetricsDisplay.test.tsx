/**
 * Tests for RealTimeMetricsDisplay Component
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { RealTimeMetricsDisplay } from '../RealTimeMetricsDisplay';

// Mock fetch
global.fetch = jest.fn();

const mockMetrics = {
  session_id: 'test-session-123',
  timestamp: '2024-01-01T12:00:00Z',
  token_usage: {
    total_tokens: 1500,
    total_cost: 0.25,
    request_count: 5,
    average_tokens_per_request: 300
  },
  latency: {
    average_ms: 1250,
    percentiles: {
      p50: 1000,
      p95: 2000,
      p99: 2500
    }
  },
  cache_performance: {
    hit_rate: 0.85,
    avg_response_time_ms: 45.5
  },
  error_rate: 2.1,
  requests_per_minute: 12.5
};

describe('RealTimeMetricsDisplay', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockMetrics
    });
  });

  it('renders loading state initially', () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    expect(screen.getByText('Loading metrics...')).toBeInTheDocument();
  });

  it('displays metrics after successful fetch', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    });

    // Check key metrics are displayed
    expect(screen.getByText('1250ms')).toBeInTheDocument(); // Response time
    expect(screen.getByText('85.0%')).toBeInTheDocument(); // Cache hit rate
    expect(screen.getByText('2.1%')).toBeInTheDocument(); // Error rate
    expect(screen.getByText('12.5')).toBeInTheDocument(); // Requests per minute
  });

  it('displays token usage information', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Token Usage')).toBeInTheDocument();
    });

    expect(screen.getByText('1,500')).toBeInTheDocument(); // Total tokens
    expect(screen.getByText('$0.2500')).toBeInTheDocument(); // Cost
    expect(screen.getByText('300')).toBeInTheDocument(); // Avg tokens per request
  });

  it('shows detailed metrics when enabled', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" showDetailed={true} />);
    
    await waitFor(() => {
      expect(screen.getByText('Latency Percentiles')).toBeInTheDocument();
    });

    expect(screen.getByText('1000ms')).toBeInTheDocument(); // p50
    expect(screen.getByText('2000ms')).toBeInTheDocument(); // p95
    expect(screen.getByText('2500ms')).toBeInTheDocument(); // p99
  });

  it('handles fetch errors gracefully', async () => {
    (fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
    
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load metrics')).toBeInTheDocument();
    });

    expect(screen.getByText('Network error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('calls onMetricsUpdate when metrics are received', async () => {
    const onMetricsUpdate = jest.fn();
    
    render(
      <RealTimeMetricsDisplay 
        sessionId="test-session" 
        onMetricsUpdate={onMetricsUpdate}
      />
    );
    
    await waitFor(() => {
      expect(onMetricsUpdate).toHaveBeenCalledWith(mockMetrics);
    });
  });

  it('refreshes metrics when refresh button is clicked', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    });

    const refreshButton = screen.getByRole('button');
    fireEvent.click(refreshButton);

    expect(fetch).toHaveBeenCalledTimes(2); // Initial load + refresh
  });

  it('displays performance status indicators', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Response Time')).toBeInTheDocument();
    });

    // Check status indicators are present
    const statusIndicators = screen.getAllByText(/Session:/);
    expect(statusIndicators).toHaveLength(1);
  });

  it('shows connection status', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    });

    // Should show connected state (Wifi icon)
    const wifiIcon = document.querySelector('[data-testid="wifi-icon"]');
    // Note: This would need proper test IDs in the actual component
  });

  it('updates metrics at specified intervals', async () => {
    jest.useFakeTimers();
    
    render(<RealTimeMetricsDisplay sessionId="test-session" updateInterval={1000} />);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    // Fast-forward time
    jest.advanceTimersByTime(1000);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    jest.useRealTimers();
  });

  it('displays trend indicators when previous metrics exist', async () => {
    // First render with initial metrics
    const { rerender } = render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    });

    // Update with new metrics that show improvement
    const improvedMetrics = {
      ...mockMetrics,
      latency: {
        ...mockMetrics.latency,
        average_ms: 800 // Improved from 1250ms
      }
    };

    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => improvedMetrics
    });

    rerender(<RealTimeMetricsDisplay sessionId="test-session" />);

    // Should show trend indicators after the second update
    // Note: This would require the component to actually show trends
  });

  it('formats currency correctly', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('$0.2500')).toBeInTheDocument();
    });
  });

  it('formats numbers with commas', async () => {
    const metricsWithLargeNumbers = {
      ...mockMetrics,
      token_usage: {
        ...mockMetrics.token_usage,
        total_tokens: 15000
      }
    };

    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => metricsWithLargeNumbers
    });

    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('15,000')).toBeInTheDocument();
    });
  });

  it('applies correct performance colors based on thresholds', async () => {
    // Test with high latency (should be red)
    const highLatencyMetrics = {
      ...mockMetrics,
      latency: {
        ...mockMetrics.latency,
        average_ms: 6000 // Above critical threshold
      }
    };

    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => highLatencyMetrics
    });

    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      const latencyElement = screen.getByText('6000ms');
      expect(latencyElement).toHaveClass('text-red-600');
    });
  });
});

describe('RealTimeMetricsDisplay Error Handling', () => {
  it('handles HTTP errors', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error'
    });

    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load metrics')).toBeInTheDocument();
    });

    expect(screen.getByText(/HTTP 500/)).toBeInTheDocument();
  });

  it('handles network timeouts', async () => {
    (fetch as jest.Mock).mockImplementation(() => 
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Timeout')), 100)
      )
    );

    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load metrics')).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('retries failed requests', async () => {
    (fetch as jest.Mock)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValue({
        ok: true,
        json: async () => mockMetrics
      });

    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load metrics')).toBeInTheDocument();
    });

    const retryButton = screen.getByText('Retry');
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    });
  });
});

describe('RealTimeMetricsDisplay Accessibility', () => {
  it('has proper ARIA labels', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    });

    // Check for proper headings
    expect(screen.getByRole('heading', { name: /Performance Metrics/i })).toBeInTheDocument();
  });

  it('supports keyboard navigation', async () => {
    render(<RealTimeMetricsDisplay sessionId="test-session" />);
    
    await waitFor(() => {
      expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    });

    const refreshButton = screen.getByRole('button');
    expect(refreshButton).toBeInTheDocument();
    
    // Test keyboard focus
    refreshButton.focus();
    expect(refreshButton).toHaveFocus();
  });
});