'use client';

import { useState, useEffect, useCallback } from 'react';

interface RateLimitInfo {
  isLimited: boolean;
  remaining: number;
  limit: number;
  resetTime?: Date;
  retryAfter?: number;
  message?: string;
}

interface UseRateLimitReturn {
  rateLimitInfo: RateLimitInfo | null;
  isRateLimited: boolean;
  timeUntilReset: number;
  clearRateLimit: () => void;
  checkRateLimit: () => void;
}

export const useRateLimit = (): UseRateLimitReturn => {
  const [rateLimitInfo, setRateLimitInfo] = useState<RateLimitInfo | null>(null);
  const [timeUntilReset, setTimeUntilReset] = useState<number>(0);

  const checkRateLimit = useCallback(() => {
    try {
      const rateLimitData = localStorage.getItem('github_rate_limit');
      if (rateLimitData) {
        const info = JSON.parse(rateLimitData);
        const resetTime = new Date(info.resetTime);
        
        if (Date.now() < resetTime.getTime()) {
          const details = info.errorData?.error?.details || {};
          setRateLimitInfo({
            isLimited: true,
            remaining: 0,
            limit: details.max_requests || 60,
            resetTime,
            retryAfter: info.retryAfter,
            message: info.errorData?.error?.message || 'Rate limit exceeded'
          });
        } else {
          // Rate limit has expired
          localStorage.removeItem('github_rate_limit');
          setRateLimitInfo(null);
        }
      }
    } catch (e) {
      console.warn('Failed to check rate limit status:', e);
    }
  }, []);

  const clearRateLimit = useCallback(() => {
    localStorage.removeItem('github_rate_limit');
    setRateLimitInfo(null);
    setTimeUntilReset(0);
  }, []);

  // Check for existing rate limit on mount
  useEffect(() => {
    checkRateLimit();
  }, [checkRateLimit]);

  // Listen for rate limit events
  useEffect(() => {
    const handleRateLimitEvent = (event: CustomEvent) => {
      const { errorData, retryAfter, resetTime } = event.detail;
      const details = errorData?.error?.details || {};
      
      setRateLimitInfo({
        isLimited: true,
        remaining: 0,
        limit: details.max_requests || 60,
        resetTime: new Date(resetTime),
        retryAfter,
        message: errorData?.error?.message || 'Rate limit exceeded'
      });
    };

    window.addEventListener('github-rate-limit-exceeded', handleRateLimitEvent as EventListener);

    return () => {
      window.removeEventListener('github-rate-limit-exceeded', handleRateLimitEvent as EventListener);
    };
  }, []);

  // Update countdown timer
  useEffect(() => {
    if (!rateLimitInfo?.resetTime) {
      setTimeUntilReset(0);
      return;
    }

    const updateTimer = () => {
      const now = Date.now();
      const timeLeft = Math.max(0, rateLimitInfo.resetTime!.getTime() - now);
      setTimeUntilReset(timeLeft);

      if (timeLeft === 0) {
        clearRateLimit();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [rateLimitInfo, clearRateLimit]);

  return {
    rateLimitInfo,
    isRateLimited: rateLimitInfo?.isLimited || false,
    timeUntilReset,
    clearRateLimit,
    checkRateLimit
  };
};

export default useRateLimit;