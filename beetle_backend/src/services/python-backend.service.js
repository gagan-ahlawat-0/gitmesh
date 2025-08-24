/**
 * Python Backend Service
 * Handles all communication with the Python AI backend
 */

class PythonBackendService {
  constructor() {
    this.baseUrl = process.env.PYTHON_SERVER || 'http://localhost:8000';
    this.timeout = 60000; // 60 seconds (increased from 30)
    this.maxRetries = 1; // Reduced from 3 to prevent multiple calls
    this.retryDelay = 1000; // 1 second
  }

  /**
   * Make a request to the Python backend
   */
  async makeRequest(endpoint, data, retryCount = 0) {
    try {
      let url;
      if (endpoint === 'process-repo') {
        url = `${this.baseUrl}/api/v1/process-repo`;
      } else if (endpoint === 'status') {
        url = `${this.baseUrl}/health`;
      } else {
        url = `${this.baseUrl}/api/v1/${endpoint}`;
      }
        
      console.log(`Calling Python backend at: ${url}`);
      console.log(`Request data:`, JSON.stringify(data, null, 2));
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMsg = `HTTP error! status: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMsg = errorData.detail || errorData.error || errorMsg;
        } catch (e) {
          errorMsg = response.statusText || errorMsg;
        }
        throw new Error(errorMsg);
      }

      return await response.json();
    } catch (error) {
      console.error(`Error calling Python backend (${endpoint}):`, error);
      
      // Retry logic for network errors
      if (retryCount < this.maxRetries && this.isRetryableError(error)) {
        const delay = this.retryDelay * Math.pow(2, retryCount);
        console.log(`Retrying in ${delay}ms (attempt ${retryCount + 1})`);
        await this.delay(delay);
        return this.makeRequest(endpoint, data, retryCount + 1);
      }
      
      throw new Error(`Failed to communicate with AI service: ${error.message}`);
    }
  }

  /**
   * Check if an error is retryable
   */
  isRetryableError(error) {
    if (error.name === 'AbortError') return true;
    if (error.message.includes('fetch')) return true;
    if (error.message.includes('ECONNRESET')) return true;
    if (error.message.includes('ETIMEDOUT')) return true;
    if (error.message.includes('ENOTFOUND')) return true;
    return false;
  }

  /**
   * Delay utility
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Chat with files
   */
  async chatWithFiles(data) {
    return this.makeRequest('chat-with-files', data);
  }

  /**
   * Store files for RAG functionality
   */
  async storeFilesForRAG(data) {
    return this.makeRequest('store-files', data);
  }

  /**
   * Get vector store status
   */
  async getVectorStoreStatus() {
    return this.makeRequest('vector-store-status', {});
  }

  /**
   * Process repository
   */
  async processRepository(data) {
    return this.makeRequest('process-repo', data);
  }

  /**
   * Import files
   */
  async importFiles(data) {
    return this.makeRequest('import', data);
  }

  /**
   * Search documents
   */
  async search(data) {
    return this.makeRequest('search', data);
  }

  /**
   * Get system status
   */
  async getStatus() {
    return this.makeRequest('status', {});
  }

  /**
   * Health check
   */
  async healthCheck() {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Python backend health check failed:', error);
      return {
        status: 'unhealthy',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Test connection
   */
  async testConnection() {
    try {
      const response = await fetch(`${this.baseUrl}/test`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });

      if (!response.ok) {
        throw new Error(`Test failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Python backend test failed:', error);
      return {
        status: 'failed',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }
}

// Export singleton instance
module.exports = new PythonBackendService();
