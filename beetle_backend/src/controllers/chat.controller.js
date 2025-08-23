const { v4: uuidv4 } = require('uuid');
const pythonBackendService = require('../services/python-backend.service.js');
const sessionService = require('../services/session.service.js');

// Import fetch for Node.js (if not available globally)
let fetch;
if (typeof globalThis.fetch === 'undefined') {
  fetch = require('node-fetch');
} else {
  fetch = globalThis.fetch;
}

class ChatController {
  // Create a new chat session
  createSession = async (req, res) => {
    try {
      const { title = 'New Chat', repositoryId, branch } = req.body;
      const userId = req.user.id;
      const sessionId = sessionService.generateSessionId();
      
      const session = sessionService.createSession(sessionId, userId, repositoryId || 'default', []);
      
      // Add title to session
      session.title = title;
      session.branch = branch;
      
      res.status(201).json({
        success: true,
        session: {
          id: session.id,
          title: session.title,
          repositoryId: session.repositoryId,
          branch: session.branch,
          createdAt: session.createdAt,
          updatedAt: session.updatedAt,
          messages: session.messages,
          selectedFiles: Array.from(session.files.values())
        }
      });
    } catch (error) {
      console.error('Error creating chat session:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to create chat session'
      });
    }
  }

  // Get a chat session by ID
  getSession = async (req, res) => {
    try {
      const { sessionId } = req.params;
      const userId = req.user.id;
      const session = sessionService.getSession(sessionId);
      
      if (!session || session.userId !== userId) {
        return res.status(404).json({
          success: false,
          error: 'Session not found'
        });
      }
      
      res.json({
        success: true,
        session: {
          id: session.id,
          title: session.title,
          repositoryId: session.repositoryId,
          branch: session.branch,
          createdAt: session.createdAt,
          updatedAt: session.updatedAt,
          messages: session.messages,
          selectedFiles: Array.from(session.files.values())
        }
      });
    } catch (error) {
      console.error('Error getting chat session:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get chat session'
      });
    }
  }

  sendMessage = async (req, res) => {
    let sessionId; // Declare sessionId at the top level
    try {
      sessionId = req.params.sessionId;
      const { message, context } = req.body;
      const userId = req.user.id;
      
      if (!sessionId || !message) {
        return res.status(400).json({ error: 'Session ID and message are required' });
      }
      
      // Get or create session
      let session = sessionService.getSession(sessionId);
      if (!session) {
        // Try to extract repository information from files if available
        let repositoryId = 'default';
        let branch = 'main';
        
        if (context?.files && Array.isArray(context.files) && context.files.length > 0) {
          const firstFile = context.files[0];
          
          // Try multiple sources for repository information
          if (firstFile.repository_id && firstFile.repository_id.includes('/')) {
            repositoryId = firstFile.repository_id;
          } else if (firstFile.owner && firstFile.repo) {
            repositoryId = `${firstFile.owner}/${firstFile.repo}`;
          } else if (firstFile.url && firstFile.url.includes('github.com')) {
            const urlMatch = firstFile.url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
            if (urlMatch) {
              repositoryId = `${urlMatch[1]}/${urlMatch[2]}`;
            }
          } else {
            // Try to get repository info from user context
            if (req?.user?.login) {
              // This is a fallback - in a real app, you'd get the user's active repository
              // For now, we'll use a placeholder that will be updated when we get real file content
              repositoryId = `${req.user.login}/unknown-repo`;
            }
          }
          
          if (firstFile.branch) {
            branch = firstFile.branch;
          }
        }
        
        console.log(`Creating session with repository: ${repositoryId}, branch: ${branch}`);
        
        const newSessionId = sessionService.generateSessionId();
        session = sessionService.createSession(newSessionId, userId, repositoryId, context?.files || []);
        session.branch = branch;
        session.title = 'New Chat';
        
        // Update sessionId for response
        sessionId = newSessionId;
        res.setHeader('X-New-Session-Id', newSessionId);
      }
      
      // Process files from context - use frontend-provided content instead of fetching
      const enrichedFiles = [];
      if (context?.files && Array.isArray(context.files)) {
        for (const file of context.files) {
          try {
            // Check if content is placeholder or needs to be fetched
            const isPlaceholderContent = !file.content || 
              file.content === 'Imported file content will be loaded...' ||
              file.content === 'Loading...' ||
              file.content.includes('Error:') ||
              file.content.length < 10; // Very short content likely placeholder
            
            if (file.content && !file.error && !isPlaceholderContent) {
              // Use the content provided by the frontend if available and valid
              const enrichedFile = {
                path: file.path,
                name: file.name || file.path.split('/').pop(),
                content: file.content,
                url: file.url || `https://github.com/${file.owner || 'unknown'}/${file.repo || 'repo'}/blob/${file.branch || 'main'}/${file.path}`,
                raw_url: file.raw_url || `https://raw.githubusercontent.com/${file.owner || 'unknown'}/${file.repo || 'repo'}/${file.branch || 'main'}/${file.path}`,
                branch: file.branch || 'main',
                size: file.content.length,
                repository_id: file.repository_id || session.repositoryId || 'default',
                owner: file.owner || 'unknown',
                repo: file.repo || 'repo',
                last_modified: file.last_modified || new Date().toISOString(),
                is_public: file.is_public !== false,
                language: this.detectLanguage(file.path),
                file_type: this.detectFileType(file.path),
                sha: file.sha || null
              };
              enrichedFiles.push(enrichedFile);
              console.log(`Using frontend-provided content for ${file.path} (${file.content.length} characters)`);
            } else {
              // Content is placeholder or missing, try to fetch it
              try {
                console.log(`Content is placeholder for ${file.path}, attempting to fetch from GitHub...`);
                
                // Ensure we have proper repository information before fetching
                let fetchRepositoryId = session.repositoryId;
                let fetchBranch = session.branch || 'main';
                
                // Use file's repository info if available
                if (file.repository_id && file.repository_id !== 'default') {
                  fetchRepositoryId = file.repository_id;
                } else if (file.owner && file.repo) {
                  fetchRepositoryId = `${file.owner}/${file.repo}`;
                }
                
                if (file.branch) {
                  fetchBranch = file.branch;
                }
                
                console.log(`Fetching ${file.path} from repository: ${fetchRepositoryId}, branch: ${fetchBranch}`);
                
                const fetchedFile = await this.fetchFileContent(file, fetchRepositoryId, fetchBranch, req);
                enrichedFiles.push(fetchedFile);
              } catch (fetchError) {
                console.error(`Failed to fetch content for file ${file.path}:`, fetchError);
                // Add file with error information
                enrichedFiles.push({
                  path: file.path,
                  name: file.name || file.path.split('/').pop(),
                  content: `Error: Failed to fetch file content - ${fetchError.message}`,
                  branch: file.branch || 'main',
                  error: true,
                  language: this.detectLanguage(file.path),
                  file_type: this.detectFileType(file.path)
                });
              }
            }
          } catch (error) {
            console.error(`Failed to process file ${file.path}:`, error);
            // Add file with error information
            enrichedFiles.push({
              path: file.path,
              name: file.name || file.path.split('/').pop(),
              content: `Error: Failed to process file - ${error.message}`,
              branch: file.branch || 'main',
              error: true,
              language: this.detectLanguage(file.path),
              file_type: this.detectFileType(file.path)
            });
          }
        }
      }
      
      // Validate that we have at least some valid file content
      const validFiles = enrichedFiles.filter(f => !f.error && f.content && f.content.length > 10);
      if (enrichedFiles.length > 0 && validFiles.length === 0) {
        throw new Error('No valid file content provided. Please ensure files are properly loaded with complete content.');
      }
      
      // Create user message
      const userMessage = {
        id: uuidv4(),
        type: 'user',
        content: message,
        timestamp: new Date(),
        files: enrichedFiles.map(f => f.path)
      };
      
      // Add user message to session
      sessionService.addMessage(sessionId, userMessage);
      
      // STEP 1: Store files in vector database for RAG functionality
      let ragStorageResult = null;
      if (enrichedFiles.length > 0) {
        try {
          console.log(`Storing ${enrichedFiles.length} files for RAG functionality`);
          ragStorageResult = await pythonBackendService.storeFilesForRAG({
            files: enrichedFiles,
            session_id: sessionId,
            repository_id: session.repositoryId || 'default'
          });
          
          if (ragStorageResult && ragStorageResult.success) {
            console.log(`Successfully stored files for RAG: ${ragStorageResult.data.files_stored} files, ${ragStorageResult.data.total_chunks_added} chunks`);
          } else {
            console.warn(`RAG storage failed: ${ragStorageResult?.error || 'Unknown error'}`);
          }
        } catch (error) {
          console.error('Error storing files for RAG:', error);
          // Continue with chat even if RAG storage fails
        }
      }
      
      // STEP 2: Process message with Python backend (now with RAG enabled)
      const aiResponse = await pythonBackendService.chatWithFiles({
        message,
        files: enrichedFiles,
        session_id: sessionId,
        repository_id: session.repositoryId || 'default'
      });
      
      // Check if response is valid
      if (!aiResponse || !aiResponse.success) {
        throw new Error(aiResponse?.error || 'Failed to get response from AI service');
      }
      
      // Create assistant message
      const assistantMessage = {
        id: uuidv4(),
        type: 'assistant',
        content: aiResponse.success ? aiResponse.response : 'I apologize, but I\'m having trouble processing your request right now. Please try again later.',
        timestamp: new Date(),
        files: aiResponse.referenced_files || [],
        codeSnippets: aiResponse.code_snippets || []
      };
      
      // Add assistant message to session
      sessionService.addMessage(sessionId, assistantMessage);
      
      // Update session files if provided
      if (context?.files) {
        sessionService.updateSessionFiles(sessionId, context.files);
      }
      
      res.json({
        success: true,
        userMessage,
        assistantMessage,
        session: {
          id: session.id,
          title: session.title,
          repositoryId: session.repositoryId,
          branch: session.branch,
          createdAt: session.createdAt,
          updatedAt: session.updatedAt,
          messages: session.messages,
          selectedFiles: Array.from(session.files.values())
        }
      });
      
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Create a fallback response if the AI service is unavailable
      const fallbackResponse = {
        id: uuidv4(),
        type: 'assistant',
        content: 'I apologize, but I\'m having trouble connecting to the AI service right now. Please try again in a moment, or check if the Python backend is running.',
        timestamp: new Date(),
        files: req.body?.context?.files?.map(f => f.path) || [],
        codeSnippets: []
      };
      
      // Add fallback message to session if sessionId is available
      if (sessionId) {
        sessionService.addMessage(sessionId, fallbackResponse);
      }
      
      res.status(503).json({ 
        error: 'AI service temporarily unavailable',
        fallbackMessage: fallbackResponse,
        session: sessionId ? {
          id: sessionId,
          messages: sessionService.getSession(sessionId)?.messages || []
        } : null
      });
    }
  }

  // Helper method to get user's active repository
  getUserActiveRepository = async (req) => {
    try {
      // Try to get repository info from user's session or context
      if (req?.user?.login) {
        const userLogin = req.user.login;
        const githubToken = req.user.accessToken;
        
        // Check if there's any repository information in the request headers or body
        const repoFromHeaders = req.headers['x-active-repository'];
        if (repoFromHeaders) {
          return repoFromHeaders;
        }
        
        // Check if there's repository info in the request body
        if (req.body?.repository_id) {
          return req.body.repository_id;
        }
        
        // If we have a GitHub token, try to get the user's repositories
        if (githubToken) {
          try {
            console.log(`Fetching repositories for user ${userLogin}...`);
            const response = await fetch(`https://api.github.com/user/repos?sort=updated&per_page=1`, {
              headers: {
                'Authorization': `token ${githubToken}`,
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Beetle-AI'
              }
            });
            
            if (response.ok) {
              const repos = await response.json();
              if (repos.length > 0) {
                const mostRecentRepo = repos[0];
                const repoFullName = `${mostRecentRepo.owner.login}/${mostRecentRepo.name}`;
                console.log(`Using most recent repository: ${repoFullName}`);
                return repoFullName;
              }
            }
          } catch (error) {
            console.error('Error fetching user repositories:', error);
          }
        }
        
        console.log(`No active repository found for user ${userLogin}, using default`);
        return null;
      }
      return null;
    } catch (error) {
      console.error('Error getting user active repository:', error);
      return null;
    }
  }

  // Get chat history for a session
  getChatHistory = async (req, res) => {
    try {
      const { sessionId } = req.params;
      const userId = req.user.id;
      const session = sessionService.getSession(sessionId);
      
      if (!session || session.userId !== userId) {
        return res.status(404).json({
          success: false,
          error: 'Session not found'
        });
      }
      
      res.json({
        success: true,
        messages: session.messages,
        session: {
          id: session.id,
          title: session.title,
          repositoryId: session.repositoryId,
          branch: session.branch,
          createdAt: session.createdAt,
          updatedAt: session.updatedAt,
          messages: session.messages,
          selectedFiles: Array.from(session.files.values())
        }
      });
    } catch (error) {
      console.error('Error getting chat history:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get chat history'
      });
    }
  }

  // Update session details
  updateSession = async (req, res) => {
    try {
      const { sessionId } = req.params;
      const userId = req.user.id;
      const updates = req.body;
      
      const session = sessionService.getSession(sessionId);
      if (!session || session.userId !== userId) {
        return res.status(404).json({
          success: false,
          error: 'Session not found'
        });
      }
      
      // Update session with new data
      sessionService.updateSession(sessionId, updates);
      
      // Get updated session
      const updatedSession = sessionService.getSession(sessionId);
      
      res.json({
        success: true,
        session: {
          id: updatedSession.id,
          title: updatedSession.title,
          repositoryId: updatedSession.repositoryId,
          branch: updatedSession.branch,
          createdAt: updatedSession.createdAt,
          updatedAt: updatedSession.updatedAt,
          messages: updatedSession.messages,
          selectedFiles: Array.from(updatedSession.files.values())
        }
      });
    } catch (error) {
      console.error('Error updating session:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to update session'
      });
    }
  }

  // Delete a chat session
  deleteSession = async (req, res) => {
    try {
      const { sessionId } = req.params;
      const userId = req.user.id;
      
      const session = sessionService.getSession(sessionId);
      if (!session || session.userId !== userId) {
        return res.status(404).json({
          success: false,
          error: 'Session not found'
        });
      }
      
      sessionService.deleteSession(sessionId);
      
      res.json({
        success: true,
        message: 'Session deleted successfully'
      });
    } catch (error) {
      console.error('Error deleting session:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to delete session'
      });
    }
  }

  // Get all sessions for a user
  getUserSessions = async (req, res) => {
    try {
      const { userId } = req.params;
      const currentUserId = req.user.id;
      
      // Ensure user can only access their own sessions
      if (userId !== currentUserId) {
        return res.status(403).json({
          success: false,
          error: 'Access denied'
        });
      }
      
      const sessions = sessionService.getUserSessions(userId);
      
      // Transform sessions to match expected format
      const transformedSessions = sessions.map(session => ({
        id: session.id,
        title: session.title,
        repositoryId: session.repositoryId,
        branch: session.branch,
        createdAt: session.createdAt,
        updatedAt: session.updatedAt,
        messages: session.messages,
        selectedFiles: Array.from(session.files.values())
      }));
      
      res.json({
        success: true,
        sessions: transformedSessions
      });
    } catch (error) {
      console.error('Error getting user sessions:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get user sessions'
      });
    }
  }

  // Context management methods (merged from context controller)
  
  // Get session context statistics
  getSessionContextStats = async (req, res) => {
    try {
      const { sessionId } = req.params;
      const userId = req.user.id;
      const session = sessionService.getSession(sessionId);
      
      if (!session || session.userId !== userId) {
        return res.status(404).json({
          success: false,
          error: 'Session not found'
        });
      }
      
      const files = Array.from(session.files.values());
      const totalTokens = this.calculateTokenCount(files);
      
      const stats = {
        totalFiles: files.length,
        totalTokens: totalTokens,
        averageTokensPerFile: files.length > 0 ? 
          Math.round(totalTokens / files.length) : 0,
        createdAt: session.createdAt,
        updatedAt: session.updatedAt,
        repositoryId: session.repositoryId,
        branch: session.branch
      };
      
      res.json({
        success: true,
        stats
      });
    } catch (error) {
      console.error('Error getting session context stats:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get session context stats'
      });
    }
  }

  // Update session file context
  updateSessionContext = async (req, res) => {
    try {
      const { sessionId } = req.params;
      const { action, files, sources } = req.body;
      const userId = req.user.id;
      
      const session = sessionService.getSession(sessionId);
      if (!session || session.userId !== userId) {
        return res.status(404).json({
          success: false,
          error: 'Session not found'
        });
      }

      switch (action) {
        case 'add_files':
          if (files && Array.isArray(files)) {
            // Process files - use frontend-provided content instead of fetching
            const enrichedFiles = [];
            for (const file of files) {
              try {
                // Use the content provided by the frontend if available
                if (file.content && !file.error) {
                  // Enrich the file with additional metadata
                  const enrichedFile = {
                    path: file.path,
                    name: file.name || file.path.split('/').pop(),
                    content: file.content,
                    url: file.url || `https://github.com/${file.owner || 'unknown'}/${file.repo || 'repo'}/blob/${file.branch || 'main'}/${file.path}`,
                    raw_url: file.raw_url || `https://raw.githubusercontent.com/${file.owner || 'unknown'}/${file.repo || 'repo'}/${file.branch || 'main'}/${file.path}`,
                    branch: file.branch || 'main',
                    size: file.content.length,
                    repository_id: file.repository_id || session.repositoryId || 'default',
                    owner: file.owner || 'unknown',
                    repo: file.repo || 'repo',
                    last_modified: file.last_modified || new Date().toISOString(),
                    is_public: file.is_public !== false,
                    language: this.detectLanguage(file.path),
                    file_type: this.detectFileType(file.path),
                    sha: file.sha || null
                  };
                  enrichedFiles.push(enrichedFile);
                } else {
                  // If no content provided, try to fetch it (fallback)
                  try {
                    const fetchedFile = await this.fetchFileContent(file, session.repositoryId || 'default', session.branch || 'main', req);
                    enrichedFiles.push(fetchedFile);
                  } catch (fetchError) {
                    console.error(`Failed to fetch content for file ${file.path}:`, fetchError);
                    // Add file with error information
                    enrichedFiles.push({
                      path: file.path,
                      name: file.name || file.path.split('/').pop(),
                      content: `Error: Failed to fetch file content - ${fetchError.message}`,
                      branch: file.branch || 'main',
                      error: true,
                      language: this.detectLanguage(file.path),
                      file_type: this.detectFileType(file.path)
                    });
                  }
                }
              } catch (error) {
                console.error(`Failed to process file ${file.path}:`, error);
                // Add file with error information
                enrichedFiles.push({
                  path: file.path,
                  name: file.name || file.path.split('/').pop(),
                  content: `Error: Failed to process file - ${error.message}`,
                  branch: file.branch || 'main',
                  error: true,
                  language: this.detectLanguage(file.path),
                  file_type: this.detectFileType(file.path)
                });
              }
            }
            sessionService.updateSessionFiles(sessionId, enrichedFiles);
          }
          break;
        case 'remove_files':
          if (files && Array.isArray(files)) {
            // Remove specific files from session
            const currentFiles = Array.from(session.files.values());
            const filesToKeep = currentFiles.filter(file => 
              !files.some(f => f.path === file.path && f.branch === file.branch)
            );
            sessionService.updateSessionFiles(sessionId, filesToKeep);
          }
          break;
        case 'clear_files':
          sessionService.updateSessionFiles(sessionId, []);
          break;
        default:
          return res.status(400).json({
            success: false,
            error: 'Invalid action. Use: add_files, remove_files, or clear_files'
          });
      }

      // Get updated session
      const updatedSession = sessionService.getSession(sessionId);
      
      res.json({
        success: true,
        message: 'Session context updated successfully',
        session: {
          id: updatedSession.id,
          title: updatedSession.title,
          repositoryId: updatedSession.repositoryId,
          branch: updatedSession.branch,
          createdAt: updatedSession.createdAt,
          updatedAt: updatedSession.updatedAt,
          messages: updatedSession.messages,
          selectedFiles: Array.from(updatedSession.files.values())
        }
      });
    } catch (error) {
      console.error('Error updating session context:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to update session context'
      });
    }
  }

  // Helper method to calculate token count (simplified for MVP)
  calculateTokenCount = (files) => {
    // For MVP, use a simple character-based estimation
    // In production, use a proper tokenizer
    return files.reduce((total, file) => {
      // Estimate 1 token per 4 characters
      return total + Math.ceil((file.content || '').length / 4);
    }, 0);
  }

  // Fetch file content from GitHub
  fetchFileContent = async (file, repositoryId, branch = 'main', req = null) => {
    try {
      // Parse repository ID to get owner and repo
      let owner, repo;
      
      // First, try to get repository info from the user's context
      if (req?.user?.login && req?.user?.accessToken) {
        // If we have user info, try to get repository from user's context
        // This is a fallback when repositoryId is 'default'
        if (repositoryId === 'default' || !repositoryId.includes('/')) {
          // Try to extract from file metadata first
          if (file.repository_id && file.repository_id.includes('/')) {
            [owner, repo] = file.repository_id.split('/');
          } else if (file.owner && file.repo) {
            owner = file.owner;
            repo = file.repo;
          } else if (file.url && file.url.includes('github.com')) {
            const urlMatch = file.url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
            if (urlMatch) {
              [, owner, repo] = urlMatch;
            }
          } else {
            // If we still don't have repository info, we need to get it from the user's repositories
            // For now, let's try to use a common pattern or ask the user to provide repository info
            throw new Error(`Unable to determine repository for file ${file.path}. Please ensure the repository information is properly set.`);
          }
        } else if (repositoryId && repositoryId.includes('/')) {
          [owner, repo] = repositoryId.split('/');
        }
      } else {
        // Fallback to the original logic
        if (repositoryId && repositoryId.includes('/')) {
          [owner, repo] = repositoryId.split('/');
        } else if (file.owner && file.repo) {
          owner = file.owner;
          repo = file.repo;
        } else if (file.repository_id && file.repository_id.includes('/')) {
          [owner, repo] = file.repository_id.split('/');
        } else if (file.url && file.url.includes('github.com')) {
          const urlMatch = file.url.match(/github\.com\/([^\/]+)\/([^\/]+)/);
          if (urlMatch) {
            [, owner, repo] = urlMatch;
          }
        }
      }
      
      if (!owner || !repo) {
        throw new Error(`Invalid repository format. Expected: owner/repo, got: ${repositoryId}. File: ${file.path}. Please ensure repository information is properly configured.`);
      }

      // Construct GitHub API URL for file content
      const fileUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(file.path)}?ref=${encodeURIComponent(branch)}`;
      
      // Get GitHub token for authenticated requests
      const githubToken = req?.user?.accessToken;
      
      const headers = {
        'Accept': 'application/vnd.github.v3.raw',
        'User-Agent': 'Beetle-AI'
      };

      if (githubToken) {
        headers['Authorization'] = `token ${githubToken}`;
      }

      console.log(`Making GitHub API request to: ${fileUrl}`);
      console.log(`Using token: ${githubToken ? 'Yes' : 'No'}`);

      const response = await fetch(fileUrl, { headers });

      if (!response.ok) {
        let errorMsg = `GitHub API error: ${response.status} ${response.statusText}`;
        try {
          const errorBody = await response.json();
          if (errorBody && errorBody.message) {
            errorMsg += ` - ${errorBody.message}`;
          }
        } catch (e) {
          // Ignore JSON parse errors
        }
        throw new Error(errorMsg);
      }

      const content = await response.text();
      
      console.log(`Successfully fetched content for ${file.path} (${content.length} characters)`);
      
      // Return enriched file object with complete metadata
      return {
        path: file.path,
        name: file.name || file.path.split('/').pop(),
        content: content,
        url: `https://github.com/${owner}/${repo}/blob/${branch}/${file.path}`,
        raw_url: `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${file.path}`,
        branch: branch,
        size: content.length,
        repository_id: `${owner}/${repo}`,
        owner: owner,
        repo: repo,
        last_modified: new Date().toISOString(),
        is_public: true,
        language: this.detectLanguage(file.path),
        file_type: this.detectFileType(file.path)
      };

    } catch (error) {
      console.error('Error fetching file content:', error);
      throw new Error(`Failed to fetch file content: ${error.message}`);
    }
  }

  // Detect programming language based on file extension
  detectLanguage = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const languageMap = {
      'js': 'javascript',
      'ts': 'typescript',
      'py': 'python',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'php': 'php',
      'rb': 'ruby',
      'go': 'go',
      'rs': 'rust',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'sass': 'sass',
      'json': 'json',
      'xml': 'xml',
      'yaml': 'yaml',
      'yml': 'yaml',
      'md': 'markdown',
      'txt': 'text',
      'sh': 'bash',
      'bash': 'bash',
      'sql': 'sql',
      'r': 'r',
      'm': 'matlab',
      'pl': 'perl',
      'lua': 'lua',
      'dart': 'dart',
      'vue': 'vue',
      'jsx': 'jsx',
      'tsx': 'tsx'
    };
    return languageMap[ext] || 'text';
  }

  // Detect file type based on extension
  detectFileType = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const codeExtensions = ['js', 'ts', 'py', 'java', 'cpp', 'c', 'cs', 'php', 'rb', 'go', 'rs', 'swift', 'kt', 'scala', 'html', 'css', 'scss', 'sass', 'json', 'xml', 'yaml', 'yml', 'sh', 'bash', 'sql', 'r', 'm', 'pl', 'lua', 'dart', 'vue', 'jsx', 'tsx'];
    const docExtensions = ['md', 'txt', 'rst', 'adoc'];
    
    if (codeExtensions.includes(ext)) return 'code';
    if (docExtensions.includes(ext)) return 'documentation';
    if (ext === 'json' || ext === 'xml' || ext === 'yaml' || ext === 'yml') return 'config';
    return 'text';
  }
}

module.exports = new ChatController();
