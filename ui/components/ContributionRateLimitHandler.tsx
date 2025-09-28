'use client';

import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';

interface RateLimitInfo {
  timestamp: number;
  retryAfter: number;
  resetTime: number;
  errorData: any;
}

const ContributionRateLimitHandler: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isRateLimited, setIsRateLimited] = useState(false);
  const [timeUntilReset, setTimeUntilReset] = useState(0);

  useEffect(() => {
    // Check for existing rate limit on mount
    const checkRateLimit = () => {
      try {
        const rateLimitInfo = localStorage.getItem('github_rate_limit');
        if (rateLimitInfo) {
          const info: RateLimitInfo = JSON.parse(rateLimitInfo);
          const now = Date.now();
          
          if (now < info.resetTime) {
            setIsRateLimited(true);
            setTimeUntilReset(info.resetTime - now);
          } else {
            // Rate limit has expired, clear it
            localStorage.removeItem('github_rate_limit');
            setIsRateLimited(false);
          }
        }
      } catch (e) {
        console.warn('Failed to check rate limit status:', e);
      }
    };

    checkRateLimit();

    // Listen for rate limit events
    const handleRateLimitExceeded = (event: CustomEvent) => {
      const { retryAfter, resetTime } = event.detail;
      setIsRateLimited(true);
      setTimeUntilReset(resetTime - Date.now());
      
      toast.error('GitHub API Rate Limit Exceeded', {
        description: `Too many requests to GitHub. Service will resume at ${new Date(resetTime).toLocaleTimeString()}`,
        duration: 10000,
      });
    };

    const handleGitHubAuthError = (event: CustomEvent) => {
      const { status, message } = event.detail;
      
      if (status === 401) {
        toast.error('Authentication Required', {
          description: 'Please log in to view repository details.',
          duration: 5000,
        });
      }
    };

    // Add event listeners
    window.addEventListener('github-rate-limit-exceeded', handleRateLimitExceeded as EventListener);
    window.addEventListener('github-auth-error', handleGitHubAuthError as EventListener);

    // Update countdown timer
    const interval = setInterval(() => {
      if (isRateLimited && timeUntilReset > 0) {
        const newTimeUntilReset = timeUntilReset - 1000;
        setTimeUntilReset(newTimeUntilReset);
        
        if (newTimeUntilReset <= 0) {
          setIsRateLimited(false);
          localStorage.removeItem('github_rate_limit');
          toast.success('GitHub API Rate Limit Reset', {
            description: 'You can now make requests to GitHub again.',
            duration: 3000,
          });
        }
      }
    }, 1000);

    return () => {
      window.removeEventListener('github-rate-limit-exceeded', handleRateLimitExceeded as EventListener);
      window.removeEventListener('github-auth-error', handleGitHubAuthError as EventListener);
      clearInterval(interval);
    };
  }, [isRateLimited, timeUntilReset]);

  // Rate limit overlay
  if (isRateLimited && timeUntilReset > 0) {
    const minutes = Math.floor(timeUntilReset / 60000);
    const seconds = Math.floor((timeUntilReset % 60000) / 1000);
    
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="mb-6">
            <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Rate Limit Exceeded</h2>
            <p className="text-gray-600">
              GitHub API rate limit has been exceeded. This is temporary and will reset automatically.
            </p>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="text-3xl font-bold text-orange-600 mb-1">
              {minutes}:{seconds.toString().padStart(2, '0')}
            </div>
            <div className="text-sm text-gray-500">Time until reset</div>
          </div>
          
          <div className="space-y-3 text-sm text-gray-600">
            <p>• The rate limit typically resets every hour</p>
            <p>• You can continue using other parts of the application</p>
            <p>• Repository data will load automatically when the limit resets</p>
          </div>
          
          <button
            onClick={() => window.location.href = '/hub'}
            className="mt-6 w-full bg-orange-600 text-white py-2 px-4 rounded-lg hover:bg-orange-700 transition-colors"
          >
            Return to Hub
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default ContributionRateLimitHandler;