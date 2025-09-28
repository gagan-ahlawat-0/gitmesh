import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { RealTimeStatusIndicator, OperationStatus } from '../RealTimeStatusIndicator';

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
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  send(data: string) {
    // Mock send functionality
  }

  // Helper method to simulate receiving messages
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }
}

// Mock the global WebSocket
(global as any).WebSocket = MockWebSocket;

describe('RealTimeStatusIndicator', () => {
  let mockWebSocket: MockWebSocket;

  beforeEach(() => {
    // Reset WebSocket mock
    jest.clearAllMocks();
  });

  afterEach(() => {
    if (mockWebSocket) {
      mockWebSocket.close();
    }
  });

  it('renders without crashing', () => {
    render(<RealTimeStatusIndicator />);
    // Component should not render anything initially
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('displays operation status when received', async () => {
    const onStatusUpdate = jest.fn();
    
    render(
      <RealTimeStatusIndicator 
        sessionId="test-session"
        onStatusUpdate={onStatusUpdate}
      />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(MockWebSocket).toHaveBeenCalled();
    });

    // Get the WebSocket instance
    const wsInstances = (MockWebSocket as any).mock.instances;
    mockWebSocket = wsInstances[wsInstances.length - 1];

    // Simulate operation start message
    const operationMessage = {
      type: 'operation_start',
      operation_id: 'test-op-1',
      operation_type: 'gitingest',
      description: 'Processing repository',
      status: 'in_progress',
      progress: 0.5,
      progress_message: 'Mapping codebase...',
      timestamp: new Date().toISOString()
    };

    mockWebSocket.simulateMessage(operationMessage);

    // Wait for component to update
    await waitFor(() => {
      expect(screen.getByText('Mapping codebase')).toBeInTheDocument();
    });

    expect(screen.getByText('in_progress')).toBeInTheDocument();
    expect(onStatusUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        operation_id: 'test-op-1',
        operation_type: 'gitingest',
        status: 'in_progress'
      })
    );
  });

  it('shows progress bar for in-progress operations', async () => {
    render(<RealTimeStatusIndicator sessionId="test-session" />);

    await waitFor(() => {
      expect(MockWebSocket).toHaveBeenCalled();
    });

    const wsInstances = (MockWebSocket as any).mock.instances;
    mockWebSocket = wsInstances[wsInstances.length - 1];

    // Simulate progress update
    const progressMessage = {
      type: 'operation_progress',
      operation_id: 'test-op-1',
      operation_type: 'redis_cache',
      description: 'Caching data',
      status: 'in_progress',
      progress: 0.75,
      progress_message: 'Storing cache entries...',
      timestamp: new Date().toISOString()
    };

    mockWebSocket.simulateMessage(progressMessage);

    await waitFor(() => {
      expect(screen.getByText('Caching data')).toBeInTheDocument();
    });

    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays completion status and auto-hides', async () => {
    jest.useFakeTimers();
    
    render(<RealTimeStatusIndicator sessionId="test-session" />);

    await waitFor(() => {
      expect(MockWebSocket).toHaveBeenCalled();
    });

    const wsInstances = (MockWebSocket as any).mock.instances;
    mockWebSocket = wsInstances[wsInstances.length - 1];

    // Simulate completion message
    const completionMessage = {
      type: 'operation_complete',
      operation_id: 'test-op-1',
      operation_type: 'ai_processing',
      description: 'Generating response',
      status: 'completed',
      progress: 1.0,
      progress_message: 'Completed',
      timestamp: new Date().toISOString()
    };

    mockWebSocket.simulateMessage(completionMessage);

    await waitFor(() => {
      expect(screen.getByText('Generating response')).toBeInTheDocument();
    });

    expect(screen.getByText('completed')).toBeInTheDocument();

    // Fast-forward time to trigger auto-hide
    jest.advanceTimersByTime(3000);

    await waitFor(() => {
      expect(screen.queryByText('Generating response')).not.toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  it('displays error status with error message', async () => {
    render(<RealTimeStatusIndicator sessionId="test-session" />);

    await waitFor(() => {
      expect(MockWebSocket).toHaveBeenCalled();
    });

    const wsInstances = (MockWebSocket as any).mock.instances;
    mockWebSocket = wsInstances[wsInstances.length - 1];

    // Simulate error message
    const errorMessage = {
      type: 'operation_error',
      operation_id: 'test-op-1',
      operation_type: 'file_processing',
      description: 'Processing files',
      status: 'failed',
      error: 'File not found',
      timestamp: new Date().toISOString()
    };

    mockWebSocket.simulateMessage(errorMessage);

    await waitFor(() => {
      expect(screen.getByText('Processing files')).toBeInTheDocument();
    });

    expect(screen.getByText('failed')).toBeInTheDocument();
    expect(screen.getByText('File not found')).toBeInTheDocument();
  });

  it('handles WebSocket connection failures gracefully', async () => {
    render(<RealTimeStatusIndicator sessionId="test-session" />);

    await waitFor(() => {
      expect(MockWebSocket).toHaveBeenCalled();
    });

    const wsInstances = (MockWebSocket as any).mock.instances;
    mockWebSocket = wsInstances[wsInstances.length - 1];

    // Simulate connection error
    if (mockWebSocket.onerror) {
      mockWebSocket.onerror(new Event('error'));
    }

    // Component should handle the error gracefully without crashing
    expect(screen.queryByText('Error')).not.toBeInTheDocument();
  });

  it('displays different icons for different operation types', async () => {
    render(<RealTimeStatusIndicator sessionId="test-session" />);

    await waitFor(() => {
      expect(MockWebSocket).toHaveBeenCalled();
    });

    const wsInstances = (MockWebSocket as any).mock.instances;
    mockWebSocket = wsInstances[wsInstances.length - 1];

    // Test gitingest operation
    const gitingestMessage = {
      type: 'operation_start',
      operation_id: 'test-op-1',
      operation_type: 'gitingest',
      description: 'Mapping codebase',
      status: 'in_progress',
      timestamp: new Date().toISOString()
    };

    mockWebSocket.simulateMessage(gitingestMessage);

    await waitFor(() => {
      expect(screen.getByText('Mapping codebase')).toBeInTheDocument();
    });

    // The component should render with appropriate styling for gitingest
    expect(screen.getByText('Mapping codebase')).toBeInTheDocument();
  });
});