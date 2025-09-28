"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Loader2, 
  CheckCircle, 
  AlertCircle, 
  Clock, 
  Database, 
  GitBranch, 
  Search,
  Cpu,
  Activity,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

// Types for real-time status updates
export interface OperationStatus {
  operation_id: string;
  operation_type: 'gitingest' | 'redis_cache' | 'api_call' | 'file_processing' | 'context_building' | 'ai_processing';
  description: string;
  status: 'starting' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  progress_message: string;
  started_at: string;
  duration?: number;
  details?: Record<string, any>;
  error?: string;
}

export interface StatusMessage {
  type: 'operation_start' | 'operation_progress' | 'operation_complete' | 'operation_error' | 'system_status';
  operation_id?: string;
  operation_type?: string;
  description?: string;
  status?: string;
  progress?: number;
  progress_message?: string;
  error?: string;
  details?: Record<string, any>;
  timestamp: string;
}

interface RealTimeStatusIndicatorProps {
  sessionId?: string;
  userId?: string;
  className?: string;
  onStatusUpdate?: (status: OperationStatus) => void;
}

// WebSocket connection for real-time status updates
class StatusWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Set<(message: StatusMessage) => void> = new Set();
  private connectionListeners: Set<(connected: boolean) => void> = new Set();
  private isConnected = false;

  constructor(private sessionId?: string, private userId?: string) {}

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const wsUrl = new URL('/api/v1/status/ws', window.location.origin);
      wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      
      if (this.sessionId) {
        wsUrl.searchParams.set('session_id', this.sessionId);
      }
      if (this.userId) {
        wsUrl.searchParams.set('user_id', this.userId);
      }

      this.ws = new WebSocket(wsUrl.toString());

      this.ws.onopen = () => {
        console.log('Status WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.connectionListeners.forEach(listener => listener(true));
      };

      this.ws.onmessage = (event) => {
        try {
          const message: StatusMessage = JSON.parse(event.data);
          this.listeners.forEach(listener => listener(message));
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('Status WebSocket disconnected');
        this.isConnected = false;
        this.connectionListeners.forEach(listener => listener(false));
        this.scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('Status WebSocket error:', error);
        this.isConnected = false;
        this.connectionListeners.forEach(listener => listener(false));
      };

    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      
      setTimeout(() => {
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        this.connect();
      }, delay);
    }
  }

  addListener(listener: (message: StatusMessage) => void) {
    this.listeners.add(listener);
  }

  removeListener(listener: (message: StatusMessage) => void) {
    this.listeners.delete(listener);
  }

  addConnectionListener(listener: (connected: boolean) => void) {
    this.connectionListeners.add(listener);
  }

  removeConnectionListener(listener: (connected: boolean) => void) {
    this.connectionListeners.delete(listener);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  getConnectionStatus() {
    return this.isConnected;
  }
}

export const RealTimeStatusIndicator: React.FC<RealTimeStatusIndicatorProps> = ({
  sessionId,
  userId,
  className,
  onStatusUpdate
}) => {
  const [currentOperation, setCurrentOperation] = useState<OperationStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [wsInstance, setWsInstance] = useState<StatusWebSocket | null>(null);

  // Initialize WebSocket connection
  useEffect(() => {
    const ws = new StatusWebSocket(sessionId, userId);
    setWsInstance(ws);

    const handleStatusMessage = (message: StatusMessage) => {
      if (message.type === 'operation_start' || message.type === 'operation_progress') {
        const operation: OperationStatus = {
          operation_id: message.operation_id || '',
          operation_type: message.operation_type as any || 'api_call',
          description: message.description || '',
          status: message.status as any || 'in_progress',
          progress: (message.progress || 0) * 100, // Convert from 0-1 to 0-100
          progress_message: message.progress_message || '',
          started_at: message.timestamp,
          details: message.details
        };

        setCurrentOperation(operation);
        onStatusUpdate?.(operation);
      } else if (message.type === 'operation_complete') {
        const operation: OperationStatus = {
          operation_id: message.operation_id || '',
          operation_type: message.operation_type as any || 'api_call',
          description: message.description || '',
          status: 'completed',
          progress: 100,
          progress_message: 'Completed',
          started_at: message.timestamp,
          details: message.details
        };

        setCurrentOperation(operation);
        onStatusUpdate?.(operation);

        // Clear the operation after a delay
        setTimeout(() => {
          setCurrentOperation(null);
        }, 3000);
      } else if (message.type === 'operation_error') {
        const operation: OperationStatus = {
          operation_id: message.operation_id || '',
          operation_type: message.operation_type as any || 'api_call',
          description: message.description || '',
          status: 'failed',
          progress: 0,
          progress_message: 'Failed',
          started_at: message.timestamp,
          error: message.error,
          details: message.details
        };

        setCurrentOperation(operation);
        onStatusUpdate?.(operation);

        // Clear the operation after a delay
        setTimeout(() => {
          setCurrentOperation(null);
        }, 5000);
      }
    };

    const handleConnectionChange = (connected: boolean) => {
      setIsConnected(connected);
    };

    ws.addListener(handleStatusMessage);
    ws.addConnectionListener(handleConnectionChange);
    ws.connect();

    return () => {
      ws.removeListener(handleStatusMessage);
      ws.removeConnectionListener(handleConnectionChange);
      ws.disconnect();
    };
  }, [sessionId, userId, onStatusUpdate]);

  // Get operation icon
  const getOperationIcon = (operationType: string) => {
    switch (operationType) {
      case 'gitingest':
        return GitBranch;
      case 'redis_cache':
        return Database;
      case 'api_call':
        return Activity;
      case 'file_processing':
        return Search;
      case 'context_building':
        return Cpu;
      case 'ai_processing':
        return Zap;
      default:
        return Activity;
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'starting':
      case 'in_progress':
        return 'text-blue-500';
      case 'completed':
        return 'text-green-500';
      case 'failed':
        return 'text-red-500';
      case 'cancelled':
        return 'text-gray-500';
      default:
        return 'text-gray-500';
    }
  };

  // Get friendly operation name
  const getFriendlyOperationName = (operationType: string) => {
    switch (operationType) {
      case 'gitingest':
        return 'Mapping codebase';
      case 'redis_cache':
        return 'Caching data';
      case 'api_call':
        return 'Processing request';
      case 'file_processing':
        return 'Analyzing files';
      case 'context_building':
        return 'Building context';
      case 'ai_processing':
        return 'Generating response';
      default:
        return 'Processing';
    }
  };

  if (!currentOperation) {
    return null;
  }

  const Icon = getOperationIcon(currentOperation.operation_type);
  const statusColor = getStatusColor(currentOperation.status);
  const friendlyName = getFriendlyOperationName(currentOperation.operation_type);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className={cn(
          "flex items-center gap-3 p-3 bg-muted/50 rounded-lg border",
          className
        )}
      >
        {/* Operation Icon */}
        <div className={cn("flex items-center justify-center", statusColor)}>
          {currentOperation.status === 'starting' || currentOperation.status === 'in_progress' ? (
            <Loader2 size={16} className="animate-spin" />
          ) : currentOperation.status === 'completed' ? (
            <CheckCircle size={16} />
          ) : currentOperation.status === 'failed' ? (
            <AlertCircle size={16} />
          ) : (
            <Icon size={16} />
          )}
        </div>

        {/* Operation Details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium">
              {friendlyName}
            </span>
            <Badge variant="outline" className="text-xs">
              {currentOperation.status}
            </Badge>
            {!isConnected && (
              <Badge variant="destructive" className="text-xs">
                Disconnected
              </Badge>
            )}
          </div>

          {/* Progress Message */}
          {currentOperation.progress_message && (
            <p className="text-xs text-muted-foreground mb-2">
              {currentOperation.progress_message}
            </p>
          )}

          {/* Progress Bar */}
          {(currentOperation.status === 'starting' || currentOperation.status === 'in_progress') && (
            <div className="space-y-1">
              <Progress 
                value={currentOperation.progress} 
                className="h-1.5"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{Math.round(currentOperation.progress)}%</span>
                <span className="flex items-center gap-1">
                  <Clock size={10} />
                  {new Date(currentOperation.started_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                  })}
                </span>
              </div>
            </div>
          )}

          {/* Error Message */}
          {currentOperation.error && (
            <p className="text-xs text-red-500 mt-1">
              {currentOperation.error}
            </p>
          )}

          {/* Additional Details */}
          {currentOperation.details && Object.keys(currentOperation.details).length > 0 && (
            <div className="mt-2 text-xs text-muted-foreground">
              {Object.entries(currentOperation.details).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span>{key}:</span>
                  <span>{String(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default RealTimeStatusIndicator;