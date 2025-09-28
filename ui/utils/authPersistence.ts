/**
 * Authentication persistence utility to maintain auth state across route transitions
 * Helps prevent authentication loss when navigating between different layouts
 */

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';

interface AuthPersistenceState {
  isTransitioning: boolean;
  lastValidatedAt: number | null;
  stableAuthState: boolean;
}

/**
 * Hook to manage authentication state persistence during navigation
 */
export function useAuthPersistence() {
  const { isAuthenticated, loading, token } = useAuth();
  const [persistenceState, setPersistenceState] = useState<AuthPersistenceState>({
    isTransitioning: false,
    lastValidatedAt: null,
    stableAuthState: false
  });

  // Track when auth state becomes stable
  useEffect(() => {
    if (!loading && isAuthenticated && token) {
      setPersistenceState(prev => ({
        ...prev,
        stableAuthState: true,
        lastValidatedAt: Date.now()
      }));
    }
  }, [loading, isAuthenticated, token]);

  // Provide a stable auth check that considers loading states
  const isStableAuthenticated = useCallback(() => {
    // If we're still loading, check if we have a stable auth state from before
    if (loading && persistenceState.stableAuthState) {
      const timeSinceLastValidation = persistenceState.lastValidatedAt 
        ? Date.now() - persistenceState.lastValidatedAt 
        : Infinity;
      
      // If last validation was recent (< 30 seconds), consider it stable
      if (timeSinceLastValidation < 30000) {
        return true;
      }
    }
    
    // Otherwise, use current auth state
    return !loading && isAuthenticated;
  }, [loading, isAuthenticated, persistenceState]);

  // Mark as transitioning during navigation
  const markTransitioning = useCallback(() => {
    setPersistenceState(prev => ({
      ...prev,
      isTransitioning: true
    }));
  }, []);

  // Clear transitioning state
  const clearTransitioning = useCallback(() => {
    setPersistenceState(prev => ({
      ...prev,
      isTransitioning: false
    }));
  }, []);

  return {
    isStableAuthenticated,
    isTransitioning: persistenceState.isTransitioning,
    markTransitioning,
    clearTransitioning,
    stableAuthState: persistenceState.stableAuthState
  };
}

/**
 * Higher-order component to wrap pages that need persistent authentication
 */
interface WithAuthPersistenceProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  redirectTo?: string;
}

export function WithAuthPersistence({ 
  children, 
  fallback = null, 
  redirectTo = '/' 
}: WithAuthPersistenceProps) {
  const router = useRouter();
  const { isStableAuthenticated, clearTransitioning } = useAuthPersistence();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    clearTransitioning();
  }, [clearTransitioning]);

  useEffect(() => {
    if (mounted && !isStableAuthenticated()) {
      // Add a small delay to prevent immediate redirects during auth validation
      const redirectTimer = setTimeout(() => {
        if (!isStableAuthenticated()) {
          console.log('Auth persistence: redirecting due to stable unauthenticated state');
          router.push(redirectTo);
        }
      }, 1000);

      return () => clearTimeout(redirectTimer);
    }
  }, [mounted, isStableAuthenticated, router, redirectTo]);

  // Don't render anything until mounted to prevent hydration issues
  if (!mounted) {
    return fallback;
  }

  // Don't render if not authenticated
  if (!isStableAuthenticated()) {
    return fallback;
  }

  return children as React.ReactElement;
}

/**
 * Navigation wrapper that preserves auth state during route transitions
 */
export function useAuthAwareNavigation() {
  const router = useRouter();
  const { markTransitioning } = useAuthPersistence();

  const navigateWithAuthPersistence = useCallback((href: string) => {
    markTransitioning();
    router.push(href);
  }, [router, markTransitioning]);

  return {
    push: navigateWithAuthPersistence,
    replace: (href: string) => {
      markTransitioning();
      router.replace(href);
    }
  };
}

/**
 * Debug utilities for authentication persistence
 */
export function useAuthDebug() {
  const { isAuthenticated, loading, token, user } = useAuth();
  const { isStableAuthenticated, stableAuthState, isTransitioning } = useAuthPersistence();

  const logAuthState = useCallback((context: string) => {
    console.log(`[AuthDebug:${context}]`, {
      isAuthenticated,
      loading,
      hasToken: !!token,
      hasUser: !!user,
      isStableAuthenticated: isStableAuthenticated(),
      stableAuthState,
      isTransitioning,
      timestamp: new Date().toISOString()
    });
  }, [isAuthenticated, loading, token, user, isStableAuthenticated, stableAuthState, isTransitioning]);

  return { logAuthState };
}
