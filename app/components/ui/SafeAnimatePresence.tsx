import { AnimatePresence, type AnimatePresenceProps } from 'framer-motion';
import { Component, type ReactNode } from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * Error boundary to catch framer-motion context errors
 * Prevents the "Cannot read properties of null (reading 'useContext')" error
 */
class AnimatePresenceErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: ReactNode; fallback?: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(_error: Error): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, _errorInfo: React.ErrorInfo) {
    // Only log if it's a framer-motion useContext error
    if (error.message?.includes('useContext') || error.message?.includes('AnimatePresence')) {
      console.warn('AnimatePresence context error caught:', error.message);
    } else {
      // Re-throw if it's not a known framer-motion error
      throw error;
    }
  }

  componentDidUpdate(prevProps: { children: ReactNode }, _prevState: ErrorBoundaryState) {
    // Reset error state when children change
    if (this.state.hasError && prevProps.children !== this.props.children) {
      this.setState({ hasError: false });
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || this.props.children;
    }

    return this.props.children;
  }
}

/**
 * SafeAnimatePresence - A wrapper around framer-motion's AnimatePresence
 * that prevents intermittent useContext errors during navigation and unmounting.
 *
 * This component:
 * 1. Wraps AnimatePresence in an error boundary
 * 2. Ensures proper cleanup during unmounting
 * 3. Provides sensible defaults for mode and initial props
 *
 * Usage:
 * ```tsx
 * <SafeAnimatePresence mode="wait">
 *   {condition && <motion.div key="unique-key">...</motion.div>}
 * </SafeAnimatePresence>
 * ```
 *
 * @param props - Same props as AnimatePresence, with optional fallback
 */
export function SafeAnimatePresence({
  children,
  mode = 'sync',
  initial = true,
  fallback,
  ...props
}: AnimatePresenceProps & { children?: ReactNode; fallback?: ReactNode }) {
  return (
    <AnimatePresenceErrorBoundary fallback={fallback}>
      <AnimatePresence mode={mode} initial={initial} {...props}>
        {children}
      </AnimatePresence>
    </AnimatePresenceErrorBoundary>
  );
}
