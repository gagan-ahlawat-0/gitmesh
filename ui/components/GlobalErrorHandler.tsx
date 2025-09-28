'use client';

import { useEffect } from 'react';
import { setupGlobalErrorHandler } from '@/lib/global-error-handler';

const GlobalErrorHandler: React.FC = () => {
  useEffect(() => {
    // Setup global error handling
    setupGlobalErrorHandler();
    
    console.log('Global error handler initialized');
    
    // Cleanup is not needed as these are global handlers
    // that should persist for the entire app lifecycle
  }, []);

  // This component doesn't render anything
  return null;
};

export default GlobalErrorHandler;