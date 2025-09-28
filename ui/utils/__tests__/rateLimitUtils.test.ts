import {
  isRateLimitError,
  extractRateLimitInfo,
  formatTimeUntilReset,
  calculateRetryDelay,
  shouldRetryRequest
} from '../rateLimitUtils';

describe('rateLimitUtils', () => {
  describe('isRateLimitError', () => {
    it('should detect HTTP 429 errors', () => {
      const error = { response: { status: 429 } };
      expect(isRateLimitError(error)).toBe(true);
    });

    it('should detect RATE_LIMIT_EXCEEDED in message', () => {
      const error = { message: 'Error: RATE_LIMIT_EXCEEDED' };
      expect(isRateLimitError(error)).toBe(true);
    });

    it('should detect errorCode RATE_LIMIT_EXCEEDED', () => {
      const error = { errorCode: 'RATE_LIMIT_EXCEEDED' };
      expect(isRateLimitError(error)).toBe(true);
    });

    it('should return false for non-rate-limit errors', () => {
      const error = { message: 'Some other error' };
      expect(isRateLimitError(error)).toBe(false);
    });
  });

  describe('extractRateLimitInfo', () => {
    it('should extract info from response data', () => {
      const error = {
        response: {
          data: {
            error: {
              error_code: 'RATE_LIMIT_EXCEEDED',
              message: 'Rate limit exceeded',
              retryAfter: 60,
              details: { max_requests: 60 }
            }
          }
        }
      };

      const info = extractRateLimitInfo(error);
      expect(info).toEqual({
        error_code: 'RATE_LIMIT_EXCEEDED',
        message: 'Rate limit exceeded',
        retryAfter: 60,
        details: { max_requests: 60 }
      });
    });

    it('should return null for non-rate-limit errors', () => {
      const error = { message: 'Some other error' };
      expect(extractRateLimitInfo(error)).toBeNull();
    });
  });

  describe('formatTimeUntilReset', () => {
    it('should format seconds only', () => {
      expect(formatTimeUntilReset(30000)).toBe('30s');
    });

    it('should format minutes and seconds', () => {
      expect(formatTimeUntilReset(90000)).toBe('1m 30s');
    });

    it('should handle zero time', () => {
      expect(formatTimeUntilReset(0)).toBe('0s');
    });
  });

  describe('calculateRetryDelay', () => {
    it('should calculate base delay', () => {
      const delay = calculateRetryDelay(60, 0);
      expect(delay).toBeGreaterThanOrEqual(60000);
      expect(delay).toBeLessThan(61000);
    });

    it('should apply exponential backoff', () => {
      const delay1 = calculateRetryDelay(60, 1);
      const delay2 = calculateRetryDelay(60, 2);
      expect(delay2).toBeGreaterThan(delay1);
    });

    it('should cap at maximum delay', () => {
      const delay = calculateRetryDelay(60, 10);
      expect(delay).toBeLessThanOrEqual(300000); // 5 minutes max
    });
  });

  describe('shouldRetryRequest', () => {
    it('should retry rate limit errors within max attempts', () => {
      const error = { errorCode: 'RATE_LIMIT_EXCEEDED' };
      expect(shouldRetryRequest(error, 3, 1)).toBe(true);
    });

    it('should not retry after max attempts', () => {
      const error = { errorCode: 'RATE_LIMIT_EXCEEDED' };
      expect(shouldRetryRequest(error, 3, 3)).toBe(false);
    });

    it('should not retry non-rate-limit errors', () => {
      const error = { message: 'Some other error' };
      expect(shouldRetryRequest(error, 3, 1)).toBe(false);
    });
  });
});