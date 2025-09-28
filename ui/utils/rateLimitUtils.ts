export interface RateLimitDetails {
  limitType: string;
  maxRequests: number;
  currentCount: number;
  resetTime: string;
}

export interface RateLimitError {
  errorCode: string;
  message: string;
  category: string;
  retryAfter: number;
  details: RateLimitDetails;
}

export const formatTimeUntilReset = (milliseconds: number): string => {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
};

export const isRateLimitError = (error: any): boolean => {
  return (
    error?.response?.status === 429 ||
    error?.message?.includes('RATE_LIMIT_EXCEEDED') ||
    error?.errorCode === 'RATE_LIMIT_EXCEEDED'
  );
};

export const extractRateLimitInfo = (error: any): RateLimitError | null => {
  try {
    // Handle different error formats
    if (error?.response?.data?.error) {
      const errorData = error.response.data.error;
      if (errorData.error_code === 'RATE_LIMIT_EXCEEDED') {
        return errorData;
      }
    }

    if (error?.detail?.error) {
      const errorData = error.detail.error;
      if (errorData.error_code === 'RATE_LIMIT_EXCEEDED') {
        return errorData;
      }
    }

    // Handle direct rate limit error objects
    if (error?.errorCode === 'RATE_LIMIT_EXCEEDED') {
      return error;
    }

    // Try to parse from error message
    if (error?.message?.includes('RATE_LIMIT_EXCEEDED')) {
      const match = error.message.match(/GitHub API error: 429 Too Many Requests - (.+)/);
      if (match) {
        const errorData = JSON.parse(match[1]);
        return errorData.error;
      }
    }

    return null;
  } catch (e) {
    console.warn('Failed to extract rate limit info:', e);
    return null;
  }
};

export const storeRateLimitInfo = (rateLimitError: RateLimitError): void => {
  try {
    const resetTime = new Date(Date.now() + (rateLimitError.retryAfter * 1000));
    const rateLimitData = {
      errorData: { error: rateLimitError },
      retryAfter: rateLimitError.retryAfter,
      resetTime: resetTime.toISOString()
    };
    
    localStorage.setItem('github_rate_limit', JSON.stringify(rateLimitData));
    
    // Emit custom event
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('github-rate-limit-exceeded', {
        detail: {
          errorData: rateLimitData.errorData,
          retryAfter: rateLimitError.retryAfter,
          resetTime: resetTime.toISOString()
        }
      });
      window.dispatchEvent(event);
    }
  } catch (e) {
    console.warn('Failed to store rate limit info:', e);
  }
};

export const clearRateLimitInfo = (): void => {
  try {
    localStorage.removeItem('github_rate_limit');
    
    // Emit clear event
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('github-rate-limit-cleared');
      window.dispatchEvent(event);
    }
  } catch (e) {
    console.warn('Failed to clear rate limit info:', e);
  }
};

export const getRateLimitInfo = (): any | null => {
  try {
    const rateLimitData = localStorage.getItem('github_rate_limit');
    if (rateLimitData) {
      const info = JSON.parse(rateLimitData);
      const resetTime = new Date(info.resetTime);
      
      if (Date.now() < resetTime.getTime()) {
        return info;
      } else {
        // Rate limit has expired, clear it
        clearRateLimitInfo();
      }
    }
    return null;
  } catch (e) {
    console.warn('Failed to get rate limit info:', e);
    return null;
  }
};

export const calculateRetryDelay = (retryAfter: number, attempt: number = 0): number => {
  // Base delay from retry_after, with exponential backoff for multiple attempts
  const baseDelay = retryAfter * 1000; // Convert to milliseconds
  const backoffMultiplier = Math.pow(2, attempt);
  const jitter = Math.random() * 1000; // Add up to 1 second of jitter
  
  return Math.min(baseDelay * backoffMultiplier + jitter, 300000); // Max 5 minutes
};

export const shouldRetryRequest = (error: any, maxRetries: number = 3, currentAttempt: number = 0): boolean => {
  if (!isRateLimitError(error)) {
    return false;
  }
  
  return currentAttempt < maxRetries;
};

export const createRateLimitAwareRequest = async <T>(
  requestFn: () => Promise<T>,
  maxRetries: number = 3
): Promise<T> => {
  let attempt = 0;
  
  while (attempt <= maxRetries) {
    try {
      return await requestFn();
    } catch (error) {
      if (isRateLimitError(error) && attempt < maxRetries) {
        const rateLimitInfo = extractRateLimitInfo(error);
        if (rateLimitInfo) {
          const delay = calculateRetryDelay(rateLimitInfo.retryAfter, attempt);
          console.log(`Rate limit hit, retrying in ${delay}ms (attempt ${attempt + 1}/${maxRetries + 1})`);
          
          await new Promise(resolve => setTimeout(resolve, delay));
          attempt++;
          continue;
        }
      }
      
      // If it's a rate limit error, store the info
      if (isRateLimitError(error)) {
        const rateLimitInfo = extractRateLimitInfo(error);
        if (rateLimitInfo) {
          storeRateLimitInfo(rateLimitInfo);
        }
      }
      
      throw error;
    }
  }
  
  throw new Error('Max retries exceeded');
};