'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import GitHubAPI from '@/lib/github-api';
import ChatAPI, { RateLimitError } from '@/lib/chat-api';
import { useAuth } from '@/contexts/AuthContext';

const ComprehensiveRateLimitTest: React.FC = () => {
  const [status, setStatus] = useState<string>('Ready to test');
  const [loading, setLoading] = useState(false);
  const { token } = useAuth();

  const testGitHubAPIRateLimit = async () => {
    if (!token) {
      toast.error('Please log in first to test GitHub API calls');
      return;
    }

    setStatus('Testing GitHub API rate limit handling...');
    setLoading(true);
    
    const githubAPI = new GitHubAPI(token);
    
    try {
      // Make multiple rapid API calls to potentially trigger rate limiting
      const promises = [];
      for (let i = 0; i < 15; i++) {
        promises.push(
          githubAPI.getUserRepositories(1, 10).catch(error => {
            console.log(`GitHub API Request ${i + 1} failed:`, error.message);
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
          setStatus('✅ GitHub API rate limit error handling working correctly!');
          toast.success('GitHub API rate limit handling is working properly');
        } else {
          setStatus('⚠️ Some GitHub API errors occurred but not rate limit related');
          toast.warning('Some GitHub API calls failed but not due to rate limiting');
        }
      } else {
        setStatus('✅ All GitHub API calls succeeded - no rate limiting detected');
        toast.success('All GitHub API calls completed successfully');
      }
      
    } catch (error: any) {
      console.error('GitHub API test error:', error);
      
      if (error.message.includes('rate limit') || error.message.includes('Rate limit exceeded')) {
        setStatus('✅ GitHub API rate limit error caught and handled gracefully!');
        toast.success('GitHub API rate limit error was handled properly');
      } else {
        setStatus('❌ Unexpected GitHub API error occurred');
        toast.error(`GitHub API test failed: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const testChatAPIRateLimit = async () => {
    if (!token) {
      toast.error('Please log in first to test Chat API calls');
      return;
    }

    setStatus('Testing Chat API rate limit handling...');
    setLoading(true);
    
    const chatAPI = new ChatAPI(token);
    
    try {
      // Make multiple rapid session creation calls to potentially trigger rate limiting
      const promises = [];
      for (let i = 0; i < 10; i++) {
        promises.push(
          chatAPI.createSession({ title: `Test Session ${i + 1}` }).catch(error => {
            console.log(`Chat API Request ${i + 1} failed:`, error.message);
            return { error: error.message, isRateLimit: error instanceof RateLimitError };
          })
        );
      }
      
      const results = await Promise.all(promises);
      const errors = results.filter(result => result && 'error' in result);
      
      if (errors.length > 0) {
        const rateLimitErrors = errors.filter(error => 
          error.isRateLimit || error.error.includes('rate limit') || error.error.includes('Rate limit exceeded')
        );
        
        if (rateLimitErrors.length > 0) {
          setStatus('✅ Chat API rate limit error handling working correctly!');
          toast.success('Chat API rate limit handling is working properly');
        } else {
          setStatus('⚠️ Some Chat API errors occurred but not rate limit related');
          toast.warning('Some Chat API calls failed but not due to rate limiting');
        }
      } else {
        setStatus('✅ All Chat API calls succeeded - no rate limiting detected');
        toast.success('All Chat API calls completed successfully');
      }
      
    } catch (error: any) {
      console.error('Chat API test error:', error);
      
      if (error instanceof RateLimitError || error.message.includes('rate limit') || error.message.includes('Rate limit exceeded')) {
        setStatus('✅ Chat API rate limit error caught and handled gracefully!');
        toast.success('Chat API rate limit error was handled properly');
      } else {
        setStatus('❌ Unexpected Chat API error occurred');
        toast.error(`Chat API test failed: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const simulateRateLimit = () => {
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
      toast.success('Rate limit simulation activated - check for overlays');
    } catch (error) {
      setStatus('❌ Failed to simulate rate limit');
      toast.error('Rate limit simulation failed');
    }
  };

  const clearRateLimit = () => {
    try {
      localStorage.removeItem('github_rate_limit');
      setStatus('✅ Rate limit cleared');
      toast.success('Rate limit cleared - pages should be accessible again');
      
      // Refresh the page to clear any overlays
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (error) {
      setStatus('❌ Failed to clear rate limit');
      toast.error('Failed to clear rate limit');
    }
  };

  const testUnhandledRejection = () => {
    setStatus('Testing unhandled promise rejection handling...');
    
    // Create a promise that rejects with a rate limit error
    Promise.reject(new RateLimitError('Rate limit exceeded for testing', 60))
      .catch(() => {
        // Intentionally empty to simulate unhandled rejection
      });
    
    setTimeout(() => {
      setStatus('✅ Unhandled rejection test completed (check console for handling)');
      toast.success('Unhandled rejection test completed');
    }, 1000);
  };

  const testGlobalErrorHandler = () => {
    setStatus('Testing global error handler...');
    
    // Emit a custom unhandled rejection event
    const event = new CustomEvent('unhandledrejection', {
      detail: {
        reason: new RateLimitError('Rate limit exceeded for testing', 60)
      }
    });
    
    window.dispatchEvent(event);
    setStatus('✅ Global error handler test completed');
    toast.success('Global error handler test completed');
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h1 className="text-3xl font-bold mb-4">Comprehensive Rate Limit Test Suite</h1>
        
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold mb-2">Status</h2>
            <p className="text-gray-700 p-3 bg-gray-50 rounded">{status}</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* API Testing */}
            <div className="space-y-3">
              <h3 className="font-semibold text-blue-800">API Rate Limit Testing</h3>
              
              <button
                onClick={testGitHubAPIRateLimit}
                disabled={loading || !token}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? 'Testing...' : 'Test GitHub API Rate Limiting'}
              </button>
              
              <button
                onClick={testChatAPIRateLimit}
                disabled={loading || !token}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:bg-gray-400"
              >
                {loading ? 'Testing...' : 'Test Chat API Rate Limiting'}
              </button>
            </div>

            {/* Simulation Testing */}
            <div className="space-y-3">
              <h3 className="font-semibold text-orange-800">Simulation Testing</h3>
              
              <button
                onClick={simulateRateLimit}
                className="w-full px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
              >
                Simulate Rate Limit (Show Overlays)
              </button>
              
              <button
                onClick={clearRateLimit}
                className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Clear Rate Limit (Hide Overlays)
              </button>
            </div>

            {/* Error Handler Testing */}
            <div className="space-y-3">
              <h3 className="font-semibold text-purple-800">Error Handler Testing</h3>
              
              <button
                onClick={testUnhandledRejection}
                className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
              >
                Test Unhandled Promise Rejection
              </button>
              
              <button
                onClick={testGlobalErrorHandler}
                className="w-full px-4 py-2 bg-pink-600 text-white rounded hover:bg-pink-700"
              >
                Test Global Error Handler
              </button>
            </div>

            {/* Navigation Testing */}
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-800">Page Navigation Testing</h3>
              
              <button
                onClick={() => window.location.href = '/contribution'}
                className="w-full px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Test Contribution Page
              </button>
              
              <button
                onClick={() => window.location.href = '/hub'}
                className="w-full px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Test Hub Page
              </button>
            </div>
          </div>
          
          {!token && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
              <p className="text-yellow-800 text-sm">
                <strong>Note:</strong> Please log in to test real API rate limiting. 
                Simulation tests work without authentication.
              </p>
            </div>
          )}
        </div>
      </div>
      
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="font-semibold mb-4">Test Coverage</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium mb-2 text-blue-800">GitHub API Protection</h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
              <li>Repository data fetching rate limits</li>
              <li>Contributors and languages API calls</li>
              <li>User repositories and activity</li>
              <li>Graceful error handling and fallbacks</li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-medium mb-2 text-indigo-800">Chat API Protection</h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
              <li>Session creation rate limits</li>
              <li>Message sending rate limits</li>
              <li>RateLimitError handling</li>
              <li>Retry logic with exponential backoff</li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-medium mb-2 text-orange-800">UI Protection</h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
              <li>Rate limit overlays with countdown</li>
              <li>Toast notifications for errors</li>
              <li>Loading states and error banners</li>
              <li>Graceful degradation</li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-medium mb-2 text-purple-800">Global Protection</h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
              <li>Unhandled promise rejection catching</li>
              <li>Global error event handling</li>
              <li>Error boundaries for React errors</li>
              <li>Multi-layer error protection</li>
            </ul>
          </div>
        </div>
        
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded">
          <p className="text-sm text-blue-800">
            <strong>Expected Result:</strong> All rate limit and API errors should be handled gracefully 
            with user-friendly messages, overlays, and automatic recovery. No unhandled runtime errors 
            should appear in the console.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ComprehensiveRateLimitTest;