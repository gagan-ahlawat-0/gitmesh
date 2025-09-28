'use client';

import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: any;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; retry: () => void }>;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Check if this is a rate limit error
    if (error.name === 'RateLimitError' || error.message.includes('Rate limit exceeded')) {
      // Handle rate limit error specifically
      this.handleRateLimitError(error);
    }
    
    this.setState({
      error,
      errorInfo
    });
  }

  handleRateLimitError = (error: Error) => {
    // Try to extract rate limit info from the error
    let retryAfter = 60; // Default
    let details = {};
    
    try {
      // If it's our custom RateLimitError
      if ('retryAfter' in error) {
        retryAfter = (error as any).retryAfter;
        details = (error as any).details || {};
      }
    } catch (e) {
      console.warn('Could not extract rate limit details:', e);
    }

    // Store rate limit info
    const resetTime = new Date(Date.now() + (retryAfter * 1000));
    const rateLimitData = {
      errorData: { error: { message: error.message, details } },
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
  };

  retry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError) {
      const { error } = this.state;
      
      // Use custom fallback if provided
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return <FallbackComponent error={error!} retry={this.retry} />;
      }

      // Check if this is a rate limit error
      const isRateLimitError = error?.name === 'RateLimitError' || 
                              error?.message.includes('Rate limit exceeded') ||
                              error?.message.includes('RATE_LIMIT_EXCEEDED');

      if (isRateLimitError) {
        return (
          <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex items-center mb-4">
                <AlertTriangle className="h-6 w-6 text-red-500 mr-3" />
                <h2 className="text-lg font-semibold text-gray-900">
                  Rate Limit Exceeded
                </h2>
              </div>

              <div className="mb-4">
                <p className="text-gray-700 mb-2">
                  {error?.message || 'GitHub API rate limit has been exceeded.'}
                </p>
                <div className="bg-gray-50 rounded p-3 text-sm">
                  <p>The application has made too many requests to the GitHub API. Please wait a moment before trying again.</p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={() => window.location.href = '/'}
                  className="flex items-center justify-center px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                >
                  <Home className="h-4 w-4 mr-2" />
                  Go to Home
                </button>
                
                <button
                  onClick={this.retry}
                  className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </button>
              </div>
            </div>
          </div>
        );
      }

      // Generic error fallback
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center mb-4">
              <AlertTriangle className="h-6 w-6 text-red-500 mr-3" />
              <h2 className="text-lg font-semibold text-gray-900">
                Something went wrong
              </h2>
            </div>

            <div className="mb-4">
              <p className="text-gray-700 mb-2">
                An unexpected error occurred:
              </p>
              <div className="bg-gray-50 rounded p-3 text-sm font-mono text-red-600">
                {error?.message || 'Unknown error'}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => window.location.href = '/'}
                className="flex items-center justify-center px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
              >
                <Home className="h-4 w-4 mr-2" />
                Go to Home
              </button>
              
              <button
                onClick={this.retry}
                className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;