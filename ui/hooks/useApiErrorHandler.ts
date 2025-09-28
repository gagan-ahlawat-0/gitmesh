'use client';

import { useCallback } from 'react';
import { RateLimitError } from '../lib/chat-api';

interface UseApiErrorHandlerReturn {
  handleApiError: (error: any) => boolean;
  isRateLimitError: (error: any) => boolean;
}

export const useApiErrorHandler = (): UseApiErrorHandlerReturn => {
  const isRateLimitError = useCallback((error: any): boolean => {
    return (
      error instanceof RateLimitError ||
      error?.name === 'RateLimitError' ||
      error?.message?.includes('Rate limit exceeded') ||
      error?.message?.includes('RATE_LIMIT_EXCEEDED') ||
      error?.response?.status === 429
    );
  }, []);

  const handleApiError = useCallback((error: any): boolean => {
    console.error('API Error:', error);

    // Handle rate limit errors
    if (isRateLimitError(error)) {
      console.warn('Rate limit error detected, handling gracefully');
      
      // Extract rate limit info
      let retryAfter = 60;
      let details = {};
      let message = 'Rate limit exceeded';

      if (error instanceof RateLimitError) {
        retryAfter = error.retryAfter;
        details = error.details;
        message = error.message;
      } else if (error?.response?.data?.error) {
        const errorData = error.response.data.error;
        retryAfter = errorData.retry_after || 60;
        details = errorData.details || {};
        message = errorData.message || 'Rate limit exceeded';
      } else if (error?.detail?.error) {
        const errorData = error.detail.error;
        retryAfter = errorData.retry_after || 60;
        details = errorData.details || {};
        message = errorData.message || 'Rate limit exceeded';
      }

      // Store rate limit info
      const resetTime = new Date(Date.now() + (retryAfter * 1000));
      const rateLimitData = {
        errorData: { error: { message, details } },
        retryAfter,
        resetTime: resetTime.toISOString()
      };
      
      try {
        localStorage.setItem('github_rate_limit', JSON.stringify(rateLimitData));
      } catch (e) {
        console.warn('Failed to store rate limit info:', e);
      }

      // Emit custom event
      if (typeof window !== 'undefined') {
        const event = new CustomEvent('github-rate-limit-exceeded', {
          detail: {
            errorData: rateLimitData.errorData,
            retryAfter,
            resetTime: resetTime.toISOString()
          }
        });
        window.dispatchEvent(event);
      }

      return true; // Handled
    }

    // Handle other API errors
    if (error?.response?.status >= 400) {
      console.error(`API Error ${error.response.status}:`, error.response.data);
      return false; // Not handled, let caller deal with it
    }

    // Network errors
    if (error?.code === 'NETWORK_ERROR' || error?.message?.includes('fetch')) {
      console.error('Network error:', error.message);
      return false; // Not handled
    }

    return false; // Not handled
  }, [isRateLimitError]);

  return {
    handleApiError,
    isRateLimitError
  };
};

export default useApiErrorHandler;