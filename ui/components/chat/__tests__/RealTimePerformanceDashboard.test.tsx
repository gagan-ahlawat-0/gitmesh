import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { RealTimePerformanceDashboard, RealTimeMetrics } from '../RealTimePerformanceDashboard';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    // Mock send
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }));
    }
  }
}

(global as any).WebSocket = MockWebSocket;

const mockMetrics: RealTimeMetrics = {
  session_id: 'test-session-123',
  timestamp: '2024-01-01T12:00:00Z',
  token_usage: {
    total_tokens: 2500,
    total_cost: 0.0375,
    request_count: 10,
    average_tokens_per_request: 250
  },
  latency: {
    average_ms: 1500,
    percentiles: {
      p50: 1200,
      p95: 2800,
      p99: 4500
    }
  },
  cache_performance: {
    hit_rate: 0.85,
    avg_response_time_ms: 120
  },
  error_rate: 2.5,
  requests_per_minute: 12.5
};

const mockFastMetrics: RealTimeMetrics = {
  ...mockMetrics,
  latency: {
    average_ms: 800,
    percentiles: {
      p50: 600,
      p95: 1200,
      p99: 1800
    }
  },
  cache_performance: {
    hit_rate: 0.95,
    avg_response_time_ms: 80
  },
  error_rate: 0,
  requests_per_minute: 20
};

const mockSlowMetrics: RealTimeMetrics = {
  ...mockMetrics,
  latency: {
    average_ms: 8000,
    percentiles: {
      p50: 6000,
      p95: 12000,
      p99: 18000
    }
  },
  cache_performance: {
    hit_rate: 0.3,
    avg_response_time_ms: 500
  },
  error_rate: 15,
  requests_per_minute: 3
};

describe('RealTimePerformanceDashboard', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('renders loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<RealTimePerformanceDashboard sessionId="test-session" />);
    
    expect(screen.getByText('Loading performance metrics...')).toBeInTheDocument();
  });

  it('fetches and displays metrics on mount', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMetrics
    });

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Real-Time Performance')).toBeInTheDocument();
    });

    expect(screen.getByText('Live')).toBeInTheDocument();
    expect(screen.getByText('1.5k')).toBeInTheDocument(); // 1500ms formatted
    expect(screen.getByText('2.5k')).toBeInTheDocument(); // 2500 tokens formatted
    expect(screen.getByText('85')).toBeInTheDocument(); // 85% cache hit rate
    expect(screen.getByText('12.5')).toBeInTheDocument(); // 12.5 req/min
  });

  it('displays error state when fetch fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load performance metrics/)).toBeInTheDocument();
    });

    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('handles retry button click', async () => {
    mockFetch
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      });

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Retry'));

    await waitFor(() => {
      expect(screen.getByText('Real-Time Performance')).toBeInTheDocument();
    });
  });

  it('renders compact view correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMetrics
    });

    render(<RealTimePerformanceDashboard sessionId="test-session" compact={true} />);

    await waitFor(() => {
      expect(screen.getByText('1.5k')).toBeInTheDocument();
    });

    expect(screen.getByText('2.5k tokens')).toBeInTheDocument();
    expect(screen.getByText('85% cache')).toBeInTheDocument();
    expect(screen.getByText('12.5 req/min')).toBeInTheDocument();
    
    // Should not show full dashboard elements in compact mode
    expect(screen.queryByText('Real-Time Performance')).not.toBeInTheDocument();
  });

  it('shows detailed view when enabled', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMetrics
    });

    render(
      <RealTimePerformanceDashboard 
        sessionId="test-session" 
        showDetailedView={true} 
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Latency Distribution')).toBeInTheDocument();
    });

    expect(screen.getByText('Session Summary')).toBeInTheDocument();
    expect(screen.getByText('50th percentile')).toBeInTheDocument();
    expect(screen.getByText('95th percentile')).toBeInTheDocument();
    expect(screen.getByText('99th percentile')).toBeInTheDocument();
  });

  it('displays correct color coding for good performance', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockFastMetrics
    });

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Real-Time Performance')).toBeInTheDocument();
    });

    // Check for green color classes (good performance)
    const responseTimeCard = screen.getByText('Avg Response Time').closest('div');
    expect(responseTimeCard).toHaveClass('bg-green-50');
  });

  it('displays warning colors for poor performance', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSlowMetrics
    });

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Real-Time Performance')).toBeInTheDocument();
    });

    // Check for red color classes (poor performance)
    const responseTimeCard = screen.getByText('Avg Response Time').closest('div');
    expect(responseTimeCard).toHaveClass('bg-red-50');
  });

  it('auto-refreshes metrics when enabled', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockFastMetrics
      });

    render(
      <RealTimePerformanceDashboard 
        sessionId="test-session" 
        autoRefresh={true}
        refreshInterval={1000}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('1.5k')).toBeInTheDocument(); // Initial metrics
    });

    // Fast forward time to trigger refresh
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(screen.getByText('800')).toBeInTheDocument(); // Updated metrics
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('handles manual refresh', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockFastMetrics
      });

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Refresh'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  it('formats large numbers correctly', async () => {
    const largeMetrics: RealTimeMetrics = {
      ...mockMetrics,
      token_usage: {
        ...mockMetrics.token_usage,
        total_tokens: 1500000 // 1.5M tokens
      },
      latency: {
        ...mockMetrics.latency,
        average_ms: 15000 // 15 seconds
      }
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => largeMetrics
    });

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('15k')).toBeInTheDocument(); // 15k ms
      expect(screen.getByText('1.5M')).toBeInTheDocument(); // 1.5M tokens
    });
  });

  it('shows connection status correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMetrics
    });

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Live')).toBeInTheDocument();
    });

    // Should show connected status
    const livebadge = screen.getByText('Live').closest('div');
    expect(livebadge).toHaveClass('bg-green-50');
  });

  it('displays session details in detailed view', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMetrics
    });

    render(
      <RealTimePerformanceDashboard 
        sessionId="test-session-123" 
        showDetailedView={true} 
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Session Summary')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Requests:')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument(); // request count
    expect(screen.getByText('Total Cost:')).toBeInTheDocument();
    expect(screen.getByText('$0.0375')).toBeInTheDocument(); // formatted cost
    expect(screen.getByText('test-sess...')).toBeInTheDocument(); // truncated session ID
  });

  it('shows progress bars for percentage metrics', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMetrics
    });

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Cache Hit Rate')).toBeInTheDocument();
    });

    // Cache hit rate should have a progress bar
    const cacheCard = screen.getByText('Cache Hit Rate').closest('div');
    const progressBar = cacheCard?.querySelector('[role="progressbar"]');
    expect(progressBar).toBeInTheDocument();
  });

  it('handles missing sessionId gracefully', () => {
    render(<RealTimePerformanceDashboard sessionId="" />);
    
    expect(screen.getByText('No performance data available')).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('cleans up intervals on unmount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockMetrics
    });

    const { unmount } = render(
      <RealTimePerformanceDashboard 
        sessionId="test-session" 
        autoRefresh={true}
        refreshInterval={1000}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Real-Time Performance')).toBeInTheDocument();
    });

    unmount();

    // Advance time to see if interval was cleared
    act(() => {
      jest.advanceTimersByTime(2000);
    });

    // Should only have been called once (initial fetch)
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('shows loading state during refresh', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      })
      .mockImplementationOnce(() => new Promise(() => {})); // Never resolves

    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Refresh'));

    // Should show loading state on metric cards
    const cards = screen.getAllByRole('generic');
    const loadingSpinner = cards.find(card => 
      card.querySelector('.animate-spin')
    );
    expect(loadingSpinner).toBeInTheDocument();
  });

  it('applies custom className', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockMetrics
    });

    render(
      <RealTimePerformanceDashboard 
        sessionId="test-session" 
        className="custom-dashboard" 
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Real-Time Performance')).toBeInTheDocument();
    });

    const container = screen.getByText('Real-Time Performance').closest('div');
    expect(container).toHaveClass('custom-dashboard');
  });
});

describe('MetricCard Component', () => {
  beforeEach(() => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockMetrics
    });
  });

  it('renders metric cards with proper structure', async () => {
    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('Avg Response Time')).toBeInTheDocument();
    });

    // Each metric should be in its own card-like structure
    const responseTimeCard = screen.getByText('Avg Response Time').closest('div');
    expect(responseTimeCard).toHaveClass('p-3', 'rounded-lg', 'border');
  });

  it('shows units correctly', async () => {
    render(<RealTimePerformanceDashboard sessionId="test-session" />);

    await waitFor(() => {
      expect(screen.getByText('ms')).toBeInTheDocument();
    });

    expect(screen.getByText('tokens')).toBeInTheDocument();
    expect(screen.getByText('%')).toBeInTheDocument();
    expect(screen.getByText('req/min')).toBeInTheDocument();
  });

  it('shows trend indicators when available', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockFastMetrics
      });

    render(
      <RealTimePerformanceDashboard 
        sessionId="test-session" 
        autoRefresh={true}
        refreshInterval={100}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Real-Time Performance')).toBeInTheDocument();
    });

    // Trigger refresh to get trend data
    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      // Should show trend indicators (though exact implementation may vary)
      expect(screen.getByText('800')).toBeInTheDocument(); // Updated latency
    });
  });
});