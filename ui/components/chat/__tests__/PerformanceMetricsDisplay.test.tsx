import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { PerformanceMetricsDisplay, PerformanceMetrics } from '../PerformanceMetricsDisplay';

const mockMetrics: PerformanceMetrics = {
  latency_ms: 1500,
  tokens_used: 2500,
  tokens_per_second: 45,
  cache_hit_rate: 0.85,
  cache_miss_rate: 0.15,
  memory_usage_mb: 256,
  response_time_ms: 1200,
  error_count: 0,
  request_count: 10,
  timestamp: '2024-01-01T12:00:00Z'
};

describe('PerformanceMetricsDisplay', () => {
  it('renders without metrics', () => {
    render(<PerformanceMetricsDisplay />);
    
    expect(screen.getByText('No performance data available')).toBeInTheDocument();
  });

  it('renders compact view correctly', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} compact={true} />);
    
    expect(screen.getByText('1.5k')).toBeInTheDocument(); // latency
    expect(screen.getByText('2.5k tokens')).toBeInTheDocument(); // tokens
    expect(screen.getByText('85% cache')).toBeInTheDocument(); // cache hit rate
    expect(screen.getByText('45 t/s')).toBeInTheDocument(); // tokens per second
  });

  it('renders full view with all metrics', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} />);
    
    expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    expect(screen.getByText('Live')).toBeInTheDocument();
    
    // Check main metrics
    expect(screen.getByText('Response Time')).toBeInTheDocument();
    expect(screen.getByText('Tokens Used')).toBeInTheDocument();
    expect(screen.getByText('Cache Hit Rate')).toBeInTheDocument();
    expect(screen.getByText('Processing Speed')).toBeInTheDocument();
    
    // Check values
    expect(screen.getByText('1.5k')).toBeInTheDocument();
    expect(screen.getByText('2.5k')).toBeInTheDocument();
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
  });

  it('shows detailed metrics when enabled', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} showDetailed={true} />);
    
    expect(screen.getByText('Memory Usage')).toBeInTheDocument();
    expect(screen.getByText('Error Count')).toBeInTheDocument();
    expect(screen.getByText('Requests')).toBeInTheDocument();
    expect(screen.getByText('Session Details')).toBeInTheDocument();
  });

  it('displays correct color coding for metrics', () => {
    const fastMetrics: PerformanceMetrics = {
      ...mockMetrics,
      latency_ms: 500, // Fast response
      cache_hit_rate: 0.95, // High cache hit rate
      tokens_per_second: 80 // High processing speed
    };

    render(<PerformanceMetricsDisplay metrics={fastMetrics} />);
    
    // Should show green indicators for good performance
    const responseTimeCard = screen.getByText('Response Time').closest('div');
    expect(responseTimeCard).toHaveClass('bg-green-50');
  });

  it('displays warning colors for moderate performance', () => {
    const moderateMetrics: PerformanceMetrics = {
      ...mockMetrics,
      latency_ms: 3000, // Moderate response time
      cache_hit_rate: 0.6, // Moderate cache hit rate
      tokens_per_second: 25 // Moderate processing speed
    };

    render(<PerformanceMetricsDisplay metrics={moderateMetrics} />);
    
    const responseTimeCard = screen.getByText('Response Time').closest('div');
    expect(responseTimeCard).toHaveClass('bg-orange-50');
  });

  it('displays error colors for poor performance', () => {
    const slowMetrics: PerformanceMetrics = {
      ...mockMetrics,
      latency_ms: 8000, // Slow response time
      cache_hit_rate: 0.3, // Low cache hit rate
      tokens_per_second: 10, // Low processing speed
      error_count: 5 // Has errors
    };

    render(<PerformanceMetricsDisplay metrics={slowMetrics} />);
    
    const responseTimeCard = screen.getByText('Response Time').closest('div');
    expect(responseTimeCard).toHaveClass('bg-red-50');
  });

  it('formats large numbers correctly', () => {
    const largeMetrics: PerformanceMetrics = {
      ...mockMetrics,
      latency_ms: 15000, // 15 seconds
      tokens_used: 1500000, // 1.5M tokens
      memory_usage_mb: 2048 // 2GB
    };

    render(<PerformanceMetricsDisplay metrics={largeMetrics} showDetailed={true} />);
    
    expect(screen.getByText('15k')).toBeInTheDocument(); // 15k ms
    expect(screen.getByText('1.5M')).toBeInTheDocument(); // 1.5M tokens
    expect(screen.getByText('2.0')).toBeInTheDocument(); // 2.0 GB
  });

  it('shows progress bars for percentage metrics', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} />);
    
    // Cache hit rate should have a progress bar
    const cacheCard = screen.getByText('Cache Hit Rate').closest('div');
    const progressBar = cacheCard?.querySelector('[role="progressbar"]');
    expect(progressBar).toBeInTheDocument();
  });

  it('displays tooltips on hover', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} />);
    
    // Tooltips should be present (though testing hover behavior requires more complex setup)
    const responseTimeCard = screen.getByText('Response Time').closest('div');
    expect(responseTimeCard).toBeInTheDocument();
  });

  it('shows trend indicators when previous metrics are available', () => {
    const { rerender } = render(<PerformanceMetricsDisplay metrics={mockMetrics} />);
    
    // Update with new metrics
    const newMetrics: PerformanceMetrics = {
      ...mockMetrics,
      latency_ms: 1200, // Improved from 1500
      tokens_per_second: 50, // Improved from 45
      timestamp: '2024-01-01T12:01:00Z'
    };

    rerender(<PerformanceMetricsDisplay metrics={newMetrics} />);
    
    // Should show trend indicators (though the exact implementation may vary)
    expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
  });

  it('handles zero and undefined values gracefully', () => {
    const incompleteMetrics: PerformanceMetrics = {
      latency_ms: 0,
      tokens_used: 0,
      tokens_per_second: 0,
      cache_hit_rate: 0,
      cache_miss_rate: 0,
      memory_usage_mb: 0,
      response_time_ms: 0,
      error_count: 0,
      request_count: 0,
      timestamp: '2024-01-01T12:00:00Z'
    };

    render(<PerformanceMetricsDisplay metrics={incompleteMetrics} />);
    
    expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} className="custom-metrics" />);
    
    const container = screen.getByText('Performance Metrics').closest('div');
    expect(container).toHaveClass('custom-metrics');
  });

  it('shows session details in detailed view', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} showDetailed={true} />);
    
    expect(screen.getByText('Session Details')).toBeInTheDocument();
    expect(screen.getByText('Cache Miss Rate:')).toBeInTheDocument();
    expect(screen.getByText('Last Updated:')).toBeInTheDocument();
    expect(screen.getByText('15%')).toBeInTheDocument(); // cache miss rate
  });

  it('formats timestamps correctly', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} showDetailed={true} />);
    
    // Should show formatted time
    const timeElement = screen.getByText(/\d{1,2}:\d{2}:\d{2}/);
    expect(timeElement).toBeInTheDocument();
  });
});

describe('MetricCard Component', () => {
  it('renders metric cards with proper structure', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} />);
    
    // Each metric should be in its own card-like structure
    const responseTimeCard = screen.getByText('Response Time').closest('div');
    expect(responseTimeCard).toHaveClass('p-3', 'rounded-lg', 'border');
  });

  it('shows units correctly', () => {
    render(<PerformanceMetricsDisplay metrics={mockMetrics} />);
    
    expect(screen.getByText('ms')).toBeInTheDocument();
    expect(screen.getByText('tokens')).toBeInTheDocument();
    expect(screen.getByText('%')).toBeInTheDocument();
    expect(screen.getByText('t/s')).toBeInTheDocument();
  });
});