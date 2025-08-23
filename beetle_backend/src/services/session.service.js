/**
 * Session Management Service
 * Handles chat sessions, file context caching, and cleanup operations
 */

const { v4: uuidv4 } = require('uuid');

class SessionService {
  constructor() {
    // Session storage (in production, use Redis or database)
    this.chatSessions = new Map();
    this.sessionTimeout = 30 * 60 * 1000; // 30 minutes
    
    // File context cache
    this.fileContextCache = new Map();
    this.cacheTimeout = 10 * 60 * 1000; // 10 minutes
    this.cleanupInterval = null;
    
    // Start cleanup interval
    this.startCleanupInterval();
  }

  /**
   * Create a new chat session
   */
  createSession(sessionId, userId, repositoryId, files = []) {
    const session = {
      id: sessionId,
      userId,
      repositoryId,
      files: new Map(files.map(f => [f.path, f])),
      messages: [],
      createdAt: new Date(),
      lastActivity: new Date(),
      status: 'active'
    };
    
    this.chatSessions.set(sessionId, session);
    return session;
  }

  /**
   * Get a session by ID
   */
  getSession(sessionId) {
    const session = this.chatSessions.get(sessionId);
    if (session && Date.now() - session.lastActivity.getTime() < this.sessionTimeout) {
      session.lastActivity = new Date();
      return session;
    }
    
    if (session) {
      this.chatSessions.delete(sessionId);
    }
    return null;
  }

  /**
   * Update a session
   */
  updateSession(sessionId, updates) {
    const session = this.chatSessions.get(sessionId);
    if (session) {
      Object.assign(session, updates);
      session.lastActivity = new Date();
    }
    return session;
  }

  /**
   * Delete a session
   */
  deleteSession(sessionId) {
    return this.chatSessions.delete(sessionId);
  }

  /**
   * Get all sessions for a user
   */
  getUserSessions(userId) {
    const sessions = [];
    for (const [sessionId, session] of this.chatSessions) {
      if (session.userId === userId && session.status === 'active') {
        sessions.push({
          id: sessionId,
          repositoryId: session.repositoryId,
          messageCount: session.messages.length,
          lastActivity: session.lastActivity,
          fileCount: session.files.size
        });
      }
    }
    return sessions.sort((a, b) => b.lastActivity - a.lastActivity);
  }

  /**
   * Add message to session
   */
  addMessage(sessionId, message) {
    const session = this.getSession(sessionId);
    if (session) {
      session.messages.push(message);
      this.updateSession(sessionId, { messages: session.messages });
      return true;
    }
    return false;
  }

  /**
   * Update files in session
   */
  updateSessionFiles(sessionId, files) {
    const session = this.getSession(sessionId);
    if (session) {
      files.forEach(file => {
        session.files.set(file.path, file);
        this.cacheFileContext(file);
      });
      this.updateSession(sessionId, { files: session.files });
      return true;
    }
    return false;
  }

  /**
   * Cache file context
   */
  cacheFileContext(fileData) {
    const key = `${fileData.branch}:${fileData.path}`;
    this.fileContextCache.set(key, {
      ...fileData,
      cachedAt: new Date()
    });
  }

  /**
   * Get cached file context
   */
  getCachedFileContext(key) {
    const cached = this.fileContextCache.get(key);
    if (cached && Date.now() - cached.cachedAt.getTime() < this.cacheTimeout) {
      return cached;
    }
    
    if (cached) {
      this.fileContextCache.delete(key);
    }
    return null;
  }

  /**
   * Validate file context
   */
  validateFileContext(files) {
    const errors = [];
    
    if (!Array.isArray(files) || files.length === 0) {
      errors.push('No files provided for context');
      return { valid: false, errors };
    }
    
    files.forEach((file, index) => {
      if (!file.path) {
        errors.push(`File ${index + 1}: Path is required`);
      }
      if (!file.content) {
        errors.push(`File ${index + 1}: Content is required`);
      }
      if (!file.branch) {
        errors.push(`File ${index + 1}: Branch is required`);
      }
      if (file.content && file.content.length > 1000000) {
        errors.push(`File ${index + 1}: Content too large (${file.content.length} characters)`);
      }
    });
    
    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Generate session ID
   */
  generateSessionId() {
    return uuidv4();
  }

  /**
   * Get session statistics
   */
  getStats() {
    return {
      activeSessions: this.chatSessions.size,
      cachedFiles: this.fileContextCache.size,
      sessionTimeout: this.sessionTimeout,
      cacheTimeout: this.cacheTimeout
    };
  }

  /**
   * Cleanup expired sessions and cache
   */
  cleanup() {
    const now = Date.now();
    let sessionsCleaned = 0;
    let cacheCleaned = 0;
    
    // Cleanup expired sessions
    for (const [sessionId, session] of this.chatSessions) {
      if (now - session.lastActivity.getTime() > this.sessionTimeout) {
        this.chatSessions.delete(sessionId);
        sessionsCleaned++;
      }
    }
    
    // Cleanup expired cache
    for (const [key, cached] of this.fileContextCache) {
      if (now - cached.cachedAt.getTime() > this.cacheTimeout) {
        this.fileContextCache.delete(key);
        cacheCleaned++;
      }
    }
    
    if (sessionsCleaned > 0 || cacheCleaned > 0) {
      console.log(`Cleanup: ${sessionsCleaned} sessions, ${cacheCleaned} cache entries removed`);
    }
  }

  /**
   * Start cleanup interval
   */
  startCleanupInterval() {
    // Clear any existing interval
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    
    this.cleanupInterval = setInterval(() => {
      try {
        this.cleanup();
      } catch (error) {
        console.error('Cleanup interval error:', error);
      }
    }, 5 * 60 * 1000); // Every 5 minutes
  }

  /**
   * Stop cleanup interval
   */
  stopCleanupInterval() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }

  /**
   * Force cleanup
   */
  forceCleanup() {
    try {
      this.cleanup();
    } catch (error) {
      console.error('Force cleanup error:', error);
    }
  }

  /**
   * Shutdown service
   */
  shutdown() {
    this.stopCleanupInterval();
    this.chatSessions.clear();
    this.fileContextCache.clear();
  }
}

// Export singleton instance
module.exports = new SessionService();
