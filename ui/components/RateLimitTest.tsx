'use client';

import React, { useState } from 'react';
import ChatAPI from '../lib/chat-api';
import ErrorBoundary from './ErrorBoundary';
import RateLimitHandler from './RateLimitHandler';

const RateLimitTest: React.FC = () => {
  const [status, setStatus] = useState<string>('Ready to test');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const testRateLimit = async () => {
    setLoading(true);
    setError(null);
    setStatus('Testing rate limit...');

    const chatAPI = new ChatAPI('test-token');

    try {
      // This will likely fail due to authentication, but should trigger rate limit handling
      await chatAPI.sendMessage('test-session', {
        message: 'Test message',
        model: 'gpt-4o-mini'
      });
      
      setStatus('Request completed successfully');
    } catch (err: any) {
      setError(err.message);
      setStatus('Error occurred - check if rate limit handling worked');
      console.log('Test error (this is expected):', err);
    } finally {
      setLoading(false);
    }
  };

  const simulateRateLimit = () => {
    // Simulate a rate limit by emitting the event directly
    const resetTime = new Date(Date.now() + 60000); // 1 minute from now
    const rateLimitData = {
      errorData: { 
        error: { 
          message: 'Rate limit exceeded for requests_per_minute',
          details: {
            limit_type: 'requests_per_minute',
            max_requests: 60,
            current_count: 70,
            reset_time: resetTime.toISOString()
          }
        }
      },
      retryAfter: 60,
      resetTime: resetTime.toISOString()
    };
    
    localStorage.setItem('github_rate_limit', JSON.stringify(rateLimitData));
    
    const event = new CustomEvent('github-rate-limit-exceeded', {
      detail: {
        errorData: rateLimitData.errorData,
        retryAfter: 60,
        resetTime: resetTime.toISOString()
      }
    });
    window.dispatchEvent(event);
    
    setStatus('Rate limit simulation triggered - you should see the overlay');
  };

  const clearRateLimit = () => {
    localStorage.removeItem('github_rate_limit');
    const event = new CustomEvent('github-rate-limit-cleared');
    window.dispatchEvent(event);
    setStatus('Rate limit cleared');
    setError(null);
  };

  return (
    <ErrorBoundary>
      <RateLimitHandler>
        <div className="max-w-2xl mx-auto p-6 space-y-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h1 className="text-2xl font-bold mb-4">Rate Limit Testing</h1>
            
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold mb-2">Status</h2>
                <p className="text-gray-700">{status}</p>
                {error && (
                  <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded text-red-700">
                    <strong>Error:</strong> {error}
                  </div>
                )}
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={testRateLimit}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Testing...' : 'Test API Call'}
                </button>
                
                <button
                  onClick={simulateRateLimit}
                  className="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
                >
                  Simulate Rate Limit
                </button>
                
                <button
                  onClick={clearRateLimit}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Clear Rate Limit
                </button>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold mb-2">How to Test:</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm text-gray-700">
              <li>Click "Simulate Rate Limit" to see the rate limit handler overlay</li>
              <li>Observe the countdown timer and user interface</li>
              <li>Click "Clear Rate Limit" to reset the state</li>
              <li>The "Test API Call" will likely fail due to auth, but won't crash the app</li>
            </ol>
          </div>
        </div>
      </RateLimitHandler>
    </ErrorBoundary>
  );
};

export default RateLimitTest;