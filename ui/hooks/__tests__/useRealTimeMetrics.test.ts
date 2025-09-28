import { renderHook, act, waitFor } from '@testing-library/react';
import useRealTimeMetrics, { RealTimeMetrics } from '../useRealTimeMetrics';
import { performanceMetricsService } from '@/lib/performance-metrics-service';

// Mock the performance metrics service
jest.mock('@/lib/performance-metrics-service', () => ({
  performanceMetricsService: {
    fetchRealTimeMetrics: jest.fn(),
    recordLatencyMetric: jest.fn(),
    recordTokenUsageMetric: jest.fn(),
    recordCacheMetric: jest.fn()
  }
}));

// Mock the WebSocket hook
jest.mock('@/lib/websocket-metrics-service', () => ({
  useWebSocketMetrics: jest.fn(() => ({
    connected: false,
    lastUpdate: null,
    error: null
  }))
}));

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

const mockPerformanceService = performanceMetricsService as jest.Mocked<typeof performanceMetricsService>;

describe('useRealTimeMetrics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Basic Functionality', () => {
    it('initializes with loading state', () => {
      mockPerformanceService.fetchRealTimeMetrics.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session' })
      );

      expect(result.current.loading).toBe(true);
      expect(result.current.metrics).toBeNull();
      expect(result.current.error).toBeNull();
    });

    it('fetches metrics on mount when autoStart is true', async () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session', autoStart: true })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.metrics).toEqual(mockMetrics);
      expect(result.current.error).toBeNull();
      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledWith('test-session');
    });

    it('does not fetch metrics when autoStart is false', () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session', autoStart: false })
      );

      expect(result.current.loading).toBe(true);
      expect(mockPerformanceService.fetchRealTimeMetrics).not.toHaveBeenCalled();
    });

    it('handles fetch errors gracefully', async () => {
      const errorMessage = 'Network error';
      mockPerformanceService.fetchRealTimeMetrics.mockRejectedValue(new Error(errorMessage));

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBe(errorMessage);
      expect(result.current.metrics).toBeNull();
    });

    it('does not fetch when sessionId is empty', () => {
      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: '' })
      );

      expect(mockPerformanceService.fetchRealTimeMetrics).not.toHaveBeenCalled();
      expect(result.current.loading).toBe(true);
    });
  });

  describe('Polling Functionality', () => {
    it('polls metrics at specified interval', async () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enablePolling: true,
          pollingInterval: 1000
        })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledTimes(1);

      // Advance time to trigger polling
      act(() => {
        jest.advanceTimersByTime(1000);
      });

      await waitFor(() => {
        expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledTimes(2);
      });
    });

    it('stops polling when disabled', async () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enablePolling: false
        })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledTimes(1);

      // Advance time - should not trigger more calls
      act(() => {
        jest.advanceTimersByTime(5000);
      });

      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledTimes(1);
    });

    it('cleans up polling interval on unmount', async () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result, unmount } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enablePolling: true,
          pollingInterval: 1000
        })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      unmount();

      // Advance time - should not trigger more calls after unmount
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledTimes(1);
    });
  });

  describe('Control Functions', () => {
    it('starts tracking when startTracking is called', async () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session', autoStart: false })
      );

      expect(result.current.loading).toBe(true);
      expect(mockPerformanceService.fetchRealTimeMetrics).not.toHaveBeenCalled();

      act(() => {
        result.current.startTracking();
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalled();
    });

    it('stops tracking when stopTracking is called', async () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enablePolling: true,
          pollingInterval: 1000
        })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      act(() => {
        result.current.stopTracking();
      });

      // Advance time - should not trigger more calls after stopping
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledTimes(1);
    });

    it('refreshes metrics when refresh is called', async () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledTimes(1);

      await act(async () => {
        await result.current.refresh();
      });

      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalledTimes(2);
    });
  });

  describe('Recording Functions', () => {
    it('records latency metrics', async () => {
      mockPerformanceService.recordLatencyMetric.mockResolvedValue(undefined);

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session' })
      );

      await act(async () => {
        await result.current.recordLatency('request-123', 1500, 'chat_request');
      });

      expect(mockPerformanceService.recordLatencyMetric).toHaveBeenCalledWith(
        'test-session',
        'request-123',
        1500,
        'chat_request',
        true
      );
    });

    it('records token usage metrics', async () => {
      mockPerformanceService.recordTokenUsageMetric.mockResolvedValue(undefined);

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session', userId: 'user-456' })
      );

      await act(async () => {
        await result.current.recordTokenUsage('request-123', 100, 150, 'gpt-4');
      });

      expect(mockPerformanceService.recordTokenUsageMetric).toHaveBeenCalledWith(
        'test-session',
        'request-123',
        100,
        150,
        'gpt-4',
        'user-456'
      );
    });

    it('records cache metrics', async () => {
      mockPerformanceService.recordCacheMetric.mockResolvedValue(undefined);

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session' })
      );

      await act(async () => {
        await result.current.recordCacheMetrics('lookup', 0.85, 120, 256);
      });

      expect(mockPerformanceService.recordCacheMetric).toHaveBeenCalledWith(
        'test-session',
        'lookup',
        0.85,
        120,
        256
      );
    });

    it('handles recording errors gracefully', async () => {
      mockPerformanceService.recordLatencyMetric.mockRejectedValue(new Error('Recording failed'));
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session' })
      );

      await act(async () => {
        await result.current.recordLatency('request-123', 1500);
      });

      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to record latency metric:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });
  });

  describe('WebSocket Integration', () => {
    it('integrates with WebSocket when enabled', () => {
      const mockUseWebSocketMetrics = require('@/lib/websocket-metrics-service').useWebSocketMetrics;
      
      renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enableWebSocket: true
        })
      );

      expect(mockUseWebSocketMetrics).toHaveBeenCalledWith({
        sessionId: 'test-session',
        userId: undefined
      });
    });

    it('does not use WebSocket when disabled', () => {
      const mockUseWebSocketMetrics = require('@/lib/websocket-metrics-service').useWebSocketMetrics;
      mockUseWebSocketMetrics.mockClear();

      renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enableWebSocket: false
        })
      );

      expect(mockUseWebSocketMetrics).not.toHaveBeenCalled();
    });

    it('handles WebSocket updates', async () => {
      const mockUseWebSocketMetrics = require('@/lib/websocket-metrics-service').useWebSocketMetrics;
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      // Mock WebSocket update
      const mockUpdate = {
        type: 'metrics_update',
        session_id: 'test-session',
        timestamp: '2024-01-01T12:00:00Z',
        data: mockMetrics
      };

      mockUseWebSocketMetrics.mockReturnValue({
        connected: true,
        lastUpdate: mockUpdate,
        error: null
      });

      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enableWebSocket: true
        })
      );

      await waitFor(() => {
        expect(result.current.metrics).toEqual(mockMetrics);
      });

      expect(result.current.connected).toBe(true);
    });

    it('falls back to polling when WebSocket fails', async () => {
      const mockUseWebSocketMetrics = require('@/lib/websocket-metrics-service').useWebSocketMetrics;
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      mockUseWebSocketMetrics.mockReturnValue({
        connected: false,
        lastUpdate: null,
        error: new Error('WebSocket failed')
      });

      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enableWebSocket: true,
          enablePolling: true,
          pollingInterval: 1000
        })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Should still fetch via polling
      expect(mockPerformanceService.fetchRealTimeMetrics).toHaveBeenCalled();
      expect(result.current.connected).toBe(false);
    });
  });

  describe('Connection Status', () => {
    it('reports connected when WebSocket is connected', () => {
      const mockUseWebSocketMetrics = require('@/lib/websocket-metrics-service').useWebSocketMetrics;
      
      mockUseWebSocketMetrics.mockReturnValue({
        connected: true,
        lastUpdate: null,
        error: null
      });

      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enableWebSocket: true
        })
      );

      expect(result.current.connected).toBe(true);
    });

    it('reports connected when tracking is active (polling mode)', () => {
      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enableWebSocket: false,
          enablePolling: true
        })
      );

      expect(result.current.connected).toBe(true); // Tracking is active
    });

    it('reports disconnected when not tracking', () => {
      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enableWebSocket: false,
          enablePolling: false,
          autoStart: false
        })
      );

      expect(result.current.connected).toBe(false);
    });
  });

  describe('Last Updated Tracking', () => {
    it('updates lastUpdated timestamp when metrics are fetched', async () => {
      mockPerformanceService.fetchRealTimeMetrics.mockResolvedValue(mockMetrics);

      const { result } = renderHook(() =>
        useRealTimeMetrics({ sessionId: 'test-session' })
      );

      expect(result.current.lastUpdated).toBeNull();

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.lastUpdated).toBeInstanceOf(Date);
    });

    it('updates lastUpdated when WebSocket message is received', async () => {
      const mockUseWebSocketMetrics = require('@/lib/websocket-metrics-service').useWebSocketMetrics;
      
      const mockUpdate = {
        type: 'metrics_update',
        session_id: 'test-session',
        timestamp: '2024-01-01T12:00:00Z',
        data: mockMetrics
      };

      mockUseWebSocketMetrics.mockReturnValue({
        connected: true,
        lastUpdate: mockUpdate,
        error: null
      });

      const { result } = renderHook(() =>
        useRealTimeMetrics({
          sessionId: 'test-session',
          enableWebSocket: true
        })
      );

      await waitFor(() => {
        expect(result.current.lastUpdated).toBeInstanceOf(Date);
      });
    });
  });
});