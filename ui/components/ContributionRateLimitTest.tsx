'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import GitHubAPI from '@/lib/github-api';
import { useAuth } from '@/contexts/AuthContext';

const ContributionRateLimitTest: React.FC = () => {
  const [status, setStatus] = useState<string>('Ready to test');
  const [loading, setLoading] = useState(false);
  const { token } = useAuth();

  const testRateLimitHandling = async () => {
    if (!token) {
      toast.error('Please log in first to test API calls');
      return;
    }

    setStatus('Testing rate limit handling...');
    setLoading(true);
    
    const githubAPI = new GitHubAPI(token);
    
    try {
      // Make multiple rapid API calls to potentially trigger rate limiting
      const promises = [];
      for (let i = 0; i < 10; i++) {
        promises.push(
          githubAPI.getUserRepositories(1, 10).catch(error => {
            console.log(`Request ${i + 1} failed:`, error.message);
            return { error: error.message };
          })
        );
      }
      
      const results = await Promise.all(promises);
      const errors = results.filter(result => result && 'error' in result);
      
      if (errors.length > 0) {
        const rateLimitErrors = errors.filter(error => 
          error.error.includes('rate limit') || error.error.includes('Rate limit exceeded')
        );
        
        if (rateLimitErrors.length > 0) {
          setStatus('✅ Rate limit error handling working correctly!');
          toast.success('Rate limit handling is working properly');
        } else {
          setStatus('⚠️ Some errors occurred but not rate limit related');
          toast.warning('Some API calls failed but not due to rate limiting');
        }
      } else {
        setStatus('✅ All API calls succeeded - no rate limiting detected');
        toast.success('All API calls completed successfully');
      }
      
    } catch (error: any) {
      console.error('Test error:', error);
      
      if (error.message.includes('rate limit') || error.message.includes('Rate limit exceeded')) {
        setStatus('✅ Rate limit error caught and handled gracefully!');
        toast.success('Rate limit error was handled properly');
      } else {
        setStatus('❌ Unexpected error occurred');
        toast.error(`Test failed: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const testRateLimitSimulation = () => {
    setStatus('Simulating rate limit error...');
    
    // Simulate rate limit by storing fake rate limit info
    const rateLimitInfo = {
      timestamp: Date.now(),
      retryAfter: 60,
      resetTime: Date.now() + (60 * 1000), // 1 minute from now
      errorData: { message: 'Rate limit exceeded for testing' }
    };
    
    try {
      localStorage.setItem('github_rate_limit', JSON.stringify(rateLimitInfo));
      
      // Emit rate limit event
      window.dispatchEvent(new CustomEvent('github-rate-limit-exceeded', {
        detail: { 
          retryAfter: 60, 
          resetTime: rateLimitInfo.resetTime,
          errorData: rateLimitInfo.errorData
        }
      }));
      
      setStatus('✅ Rate limit simulation triggered!');
      toast.success('Rate limit simulation activated - check the overlay');
    } catch (error) {
      setStatus('❌ Failed to simulate rate limit');
      toast.error('Rate limit simulation failed');
    }
  };

  const clearRateLimit = () => {
    try {
      localStorage.removeItem('github_rate_limit');
      setStatus('✅ Rate limit cleared');
      toast.success('Rate limit cleared - page should be accessible again');
      
      // Refresh the page to clear the overlay
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (error) {
      setStatus('❌ Failed to clear rate limit');
      toast.error('Failed to clear rate limit');
    }
  };

  const testAuthError = () => {
    setStatus('Simulating authentication error...');
    
    // Emit auth error event
    window.dispatchEvent(new CustomEvent('github-auth-error', {
      detail: { 
        status: 401, 
        message: 'Authentication required for testing',
        errorData: { message: 'Unauthorized' }
      }
    }));
    
    setStatus('✅ Authentication error simulation triggered!');
    toast.success('Authentication error simulation activated');
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold mb-4">Contribution Page Rate Limit Test</h1>
        
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold mb-2">Status</h2>
            <p className="text-gray-700">{status}</p>
          </div>
          
          <div className="flex flex-col gap-3">
            <button
              onClick={testRateLimitHandling}
              disabled={loading || !token}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading ? 'Testing...' : 'Test Real API Rate Limiting'}
            </button>
            
            <button
              onClick={testRateLimitSimulation}
              className="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
            >
              Simulate Rate Limit (Show Overlay)
            </button>
            
            <button
              onClick={clearRateLimit}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              Clear Rate Limit (Hide Overlay)
            </button>
            
            <button
              onClick={testAuthError}
              className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
            >
              Test Authentication Error
            </button>
          </div>
          
          {!token && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
              <p className="text-yellow-800 text-sm">
                Please log in to test real API rate limiting
              </p>
            </div>
          )}
        </div>
      </div>
      
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="font-semibold mb-2">What This Tests:</h3>
        <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
          <li><strong>Real API Rate Limiting:</strong> Makes multiple API calls to test actual rate limit handling</li>
          <li><strong>Rate Limit Simulation:</strong> Shows the rate limit overlay without hitting actual limits</li>
          <li><strong>Clear Rate Limit:</strong> Removes rate limit state and refreshes the page</li>
          <li><strong>Authentication Error:</strong> Tests authentication error handling</li>
        </ul>
        
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
          <p className="text-sm text-blue-800">
            <strong>Expected Result:</strong> All rate limit and authentication errors should be handled gracefully 
            with user-friendly messages and overlays. No unhandled runtime errors should appear.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ContributionRateLimitTest;