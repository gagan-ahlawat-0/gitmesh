const API_BASE_URL = 'http://localhost:8000/api/v1';

export class RateLimitError extends Error {
  public retryAfter: number;
  public details: any;

  constructor(message: string, retryAfter: number, details: any = {}) {
    super(message);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
    this.details = details;
  }
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  files?: string[];
  model?: string;
  metadata?: {
    confidence?: number;
    knowledge_used?: number;
    sources_count?: number;
    cosmos_available?: boolean;
    requested_files?: Array<{
      path: string;
      reason: string;
      branch?: string;
      auto_add?: boolean;
      metadata?: Record<string, any>;
    }>;
    interactive_elements?: Array<{
      element_type: string;
      value: string;
      label: string;
      metadata?: Record<string, any>;
    }>;
    file_requests_count?: number;
  };
  codeSnippets?: Array<{
    language: string;
    code: string;
    filePath?: string;
  }>;
}

export interface ChatSession {
  id: string;
  title: string;
  repositoryId?: string;
  branch?: string;
  messages: ChatMessage[];
  selectedFiles: Array<{branch: string, path: string, content: string}>;
  createdAt: Date;
  updatedAt: Date;
}

export interface Context {
  id: string;
  files: Array<{
    path: string;
    content: string;
    branch: string;
    repository_id?: string;
    owner?: string;
    repo?: string;
    url?: string;
    raw_url?: string;
  }>;
  sources: string[];
  repositoryId?: string;
  branch?: string;
  totalTokens: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface ContextStats {
  totalFiles: number;
  totalSources: number;
  totalTokens: number;
  averageTokensPerFile: number;
  createdAt: Date;
  updatedAt: Date;
}

class ChatAPI {
  private token: string;

  constructor(token: string) {
    this.token = token;
  }



  private async makeRequest(endpoint: string, options: RequestInit = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    console.log(`ChatAPI: Making request to ${url}`);
    console.log(`ChatAPI: Using token: ${this.token ? 'Token available' : 'No token'}`);
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`,
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      console.log(`ChatAPI: Response status: ${response.status}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(`ChatAPI: Error response:`, errorData);
        
        // Handle rate limiting specifically
        if (response.status === 429 || (errorData.error && errorData.error.error_code === 'RATE_LIMIT_EXCEEDED')) {
          const rateLimitError = errorData.error || errorData;
          const retryAfter = rateLimitError.retry_after || 60;
          const details = rateLimitError.details || {};
          
          // Handle rate limit error and store info
          const resetTime = new Date(Date.now() + (retryAfter * 1000));
          const rateLimitData = {
            timestamp: Date.now(),
            retryAfter,
            resetTime: resetTime.getTime(),
            errorData: { error: { message: rateLimitError.message || 'Rate limit exceeded', details } }
          };
          
          try {
            localStorage.setItem('github_rate_limit', JSON.stringify(rateLimitData));
          } catch (e) {
            console.warn('Failed to store rate limit info:', e);
          }

          // Emit custom event for the rate limit handler
          if (typeof window !== 'undefined') {
            const event = new CustomEvent('github-rate-limit-exceeded', {
              detail: {
                errorData: rateLimitData.errorData,
                retryAfter,
                resetTime: resetTime.getTime()
              }
            });
            window.dispatchEvent(event);
          }
          
          // Create a specific RateLimitError that can be caught and handled
          const error = new RateLimitError(
            `Rate limit exceeded. Please wait ${retryAfter} seconds before trying again.`,
            retryAfter,
            details
          );
          throw error;
        }
        
        // Handle different error response formats
        let errorMessage = `HTTP error! status: ${response.status}`;
        
        if (errorData) {
          if (typeof errorData === 'string') {
            errorMessage = errorData;
          } else if (errorData.error) {
            errorMessage = typeof errorData.error === 'string' ? errorData.error : JSON.stringify(errorData.error);
          } else if (errorData.detail) {
            errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
          } else if (errorData.message) {
            errorMessage = typeof errorData.message === 'string' ? errorData.message : JSON.stringify(errorData.message);
          }
        }
        
        throw new Error(errorMessage);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      
      // Handle rate limit errors from backend
      if (error instanceof Error && error.message.includes('RATE_LIMIT_EXCEEDED')) {
        try {
          const errorMatch = error.message.match(/GitHub API error: 429 Too Many Requests - (.+)/);
          if (errorMatch) {
            const errorData = JSON.parse(errorMatch[1]);
            const rateLimitInfo = errorData.error;
            
            // Handle rate limit error and store info
            const retryAfter = rateLimitInfo.retry_after || 60;
            const resetTime = new Date(Date.now() + (retryAfter * 1000));
            const rateLimitData = {
              timestamp: Date.now(),
              retryAfter,
              resetTime: resetTime.getTime(),
              errorData: { error: { message: rateLimitInfo.message, details: rateLimitInfo.details || {} } }
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
                  resetTime: resetTime.getTime()
                }
              });
              window.dispatchEvent(event);
            }
            
            // Create a specific RateLimitError that can be caught and handled
            const rateLimitError = new RateLimitError(
              `Rate limit exceeded. Please wait ${retryAfter} seconds before trying again.`,
              retryAfter,
              rateLimitInfo.details || {}
            );
            throw rateLimitError;
          }
        } catch (parseError) {
          // If parsing fails, fall through to generic error
        }
      }
      
      // Ensure we always throw a proper Error with a string message
      if (error instanceof Error) {
        throw error;
      } else {
        throw new Error(`API request failed: ${String(error)}`);
      }
    }
  }

  // Chat Session Management
  async createSession(data: {
    title?: string;
    repositoryId?: string;
    branch?: string;
  }): Promise<{ success: boolean; session: ChatSession }> {
    return this.makeRequest('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSession(sessionId: string): Promise<{ success: boolean; session: ChatSession }> {
    return this.makeRequest(`/chat/sessions/${sessionId}`);
  }

  async updateSession(sessionId: string, updates: Partial<ChatSession>): Promise<{ success: boolean; session: ChatSession }> {
    return this.makeRequest(`/chat/sessions/${sessionId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    return this.makeRequest(`/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  async getUserSessions(userId: string): Promise<{ success: boolean; sessions: ChatSession[] }> {
    return this.makeRequest(`/chat/users/${userId}/sessions`);
  }

  // Chat Messages
  async sendMessage(sessionId: string, data: {
    message: string;
    model?: string;
    context?: {
      files?: Array<{
        path: string;
        content: string;
        branch: string;
        repository_id?: string;
        owner?: string;
        repo?: string;
        url?: string;
        raw_url?: string;
      }>;
    };
    repository_id?: string;
  }): Promise<{
    success: boolean;
    userMessage: ChatMessage;
    assistantMessage: ChatMessage;
    session: ChatSession;
  }> {
    return this.makeRequest(`/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getChatHistory(sessionId: string): Promise<{
    success: boolean;
    messages: ChatMessage[];
    session: ChatSession;
  }> {
    return this.makeRequest(`/chat/sessions/${sessionId}/messages`);
  }

  // Context Management (now part of chat sessions)
  async getSessionContextStats(sessionId: string): Promise<{ success: boolean; stats: ContextStats }> {
    return this.makeRequest(`/chat/sessions/${sessionId}/context/stats`);
  }

  async updateSessionContext(sessionId: string, data: {
    action: 'add_files' | 'remove_files' | 'clear_files';
    files?: Array<{path: string, content: string, branch: string}>;
  }): Promise<{ success: boolean; session: ChatSession }> {
    return this.makeRequest(`/chat/sessions/${sessionId}/context`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
}

export default ChatAPI;