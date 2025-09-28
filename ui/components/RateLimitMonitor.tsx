'use client';

import React, { useState, useEffect } from 'react';
import { AlertTriangle, Clock, Activity } from 'lucide-react';

interface RateLimitStatus {
  isLimited: boolean;
  remaining: number;
  limit: number;
  resetTime?: Date;
  retryAfter?: number;
}

interface RateLimitMonitorProps {
  className?: string;
}

const RateLimitMonitor: React.FC<RateLimitMonitorProps> = ({ className = '' }) => {
  const [status, setStatus] = useState<RateLimitStatus | null>(null);
  const [timeUntilReset, setTimeUntilReset] = useState<number>(0);

  useEffect(() => {
    // Check for existing rate limit info
    checkRateLimitStatus();

    // Listen for rate limit events
    const handleRateLimitEvent = (event: CustomEvent) => {
      const { retryAfter, resetTime } = event.detail;
      setStatus({
        isLimited: true,
        remaining: 0,
        limit: 60, // Default GitHub limit
        resetTime: new Date(resetTime),
        retryAfter
      });
    };

    window.addEventListener('github-rate-limit-exceeded', handleRateLimitEvent as EventListener);

    return () => {
      window.removeEventListener('github-rate-limit-exceeded', handleRateLimitEvent as EventListener);
    };
  }, []);

  useEffect(() => {
    if (!status?.resetTime) return;

    const updateTimer = () => {
      const now = Date.now();
      const timeLeft = Math.max(0, status.resetTime!.getTime() - now);
      setTimeUntilReset(timeLeft);

      if (timeLeft === 0) {
        setStatus(null);
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [status]);

  const checkRateLimitStatus = () => {
    try {
      const rateLimitData = localStorage.getItem('github_rate_limit');
      if (rateLimitData) {
        const info = JSON.parse(rateLimitData);
        const resetTime = new Date(info.resetTime);
        
        if (Date.now() < resetTime.getTime()) {
          setStatus({
            isLimited: true,
            remaining: 0,
            limit: info.errorData?.error?.details?.max_requests || 60,
            resetTime,
            retryAfter: info.retryAfter
          });
        } else {
          localStorage.removeItem('github_rate_limit');
        }
      }
    } catch (e) {
      console.warn('Failed to check rate limit status:', e);
    }
  };

  const formatTime = (milliseconds: number): string => {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
  };

  if (!status?.isLimited) {
    return null;
  }

  return (
    <div className={`bg-red-50 border border-red-200 rounded-lg p-3 ${className}`}>
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-red-500" />
        <div className="flex-1">
          <p className="text-sm font-medium text-red-800">
            Rate Limit Active
          </p>
          <div className="flex items-center gap-4 mt-1">
            <div className="flex items-center gap-1 text-xs text-red-600">
              <Activity className="h-3 w-3" />
              <span>{status.remaining}/{status.limit} requests</span>
            </div>
            <div className="flex items-center gap-1 text-xs text-red-600">
              <Clock className="h-3 w-3" />
              <span>Reset in {formatTime(timeUntilReset)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RateLimitMonitor;