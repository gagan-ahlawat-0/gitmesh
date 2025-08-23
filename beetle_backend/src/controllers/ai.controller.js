const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const pythonBackendService = require('../services/python-backend.service.js');

// Helper function to make API call to Python backend (legacy support)
async function callPythonBackend(endpoint, data) {
  return pythonBackendService.makeRequest(endpoint, data);
}

// Helper function to check if a repository is public
async function isRepoPublic(owner, repo) {
  try {
    const response = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Beetle-AI'
      }
    });
    
    if (!response.ok) {
      if (response.status === 404) return false;
      throw new Error(`GitHub API error: ${response.status}`);
    }
    
    const repoData = await response.json();
    return !repoData.private;
  } catch (error) {
    console.error('Error checking repository visibility:', error);
    return false;
  }
}

// Helper function to get GitHub token from beetle_db.json
async function getGitHubToken(userId) {
  try {
    const dbPath = path.join(__dirname, '../../data/beetle_db.json');
    const dbData = await fs.readFile(dbPath, 'utf8');
    const db = JSON.parse(dbData);
    
    const user = db.users?.find(u => u.id === userId);
    return user?.githubToken || null;
  } catch (error) {
    console.error('Error reading beetle_db.json:', error);
    return null;
  }
}

// Helper function to fetch file content from GitHub
async function fetchGitHubFileContent(url, githubToken, isPublic) {
  try {
    const headers = {
      'Accept': 'application/vnd.github.v3.raw',
      'User-Agent': 'Beetle-AI'
    };

    if (!isPublic && githubToken) {
      headers['Authorization'] = `token ${githubToken}`;
    }

    const response = await fetch(url, { headers });

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

    return await response.text();
  } catch (error) {
    console.error('Error fetching file from GitHub:', error);
    throw new Error(`Failed to fetch file from GitHub: ${error.message}`);
  }
}

// Main controller functions
const aiController = {
  // Expose services for use in routes
  callPythonBackend,
  pythonBackendService,
  // Chat functionality has been moved to dedicated chat.controller.js
  // This controller now focuses on AI processing and GitHub integration

  // Import files from GitHub
  async importFromGitHub(req, res) {
    try {
      const { 
        repository_id: repoFullName,
        branch = 'main',
        files = []
      } = req.body;
      
      if (!repoFullName) {
        return res.status(400).json({
          success: false,
          error: 'Repository name is required (format: owner/repo)'
        });
      }
      
      if (!Array.isArray(files) || files.length === 0) {
        return res.status(400).json({
          success: false,
          error: 'No files specified for import'
        });
      }
      
      const [owner, repo] = repoFullName.split('/');
      if (!owner || !repo) {
        return res.status(400).json({
          success: false,
          error: 'Invalid repository format. Expected format: owner/repo'
        });
      }
      
      // Check if repository is public
      const isPublic = await isRepoPublic(owner, repo);
      if (!isPublic) {
        return res.status(400).json({
          success: false,
          error: 'Only public GitHub repositories are supported'
        });
      }
      
      // Process files
      const processedFiles = [];
      const errors = [];
      
      for (const file of files) {
        try {
          const filePath = file.path;
          const fileBranch = file.branch || branch;
          
          const fileUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(filePath)}?ref=${encodeURIComponent(fileBranch)}`;
          const content = await fetchGitHubFileContent(fileUrl);
          
          processedFiles.push({
            path: filePath,
            branch: fileBranch,
            content: content,
            size: content.length,
            is_public: true
          });
        } catch (error) {
          errors.push({
            path: file.path,
            error: error.message
          });
        }
      }
      
      if (processedFiles.length === 0) {
        return res.status(400).json({
          success: false,
          error: 'Failed to process any files',
          errors: errors
        });
      }
      
      // Send to Python backend
      const payload = {
        repository: repoFullName,
        repository_id: repoFullName.replace(/[^a-zA-Z0-9_-]/g, '_'),
        branch: branch,
        source_type: 'github',
        files: processedFiles,
        timestamp: new Date().toISOString()
      };
      
      const result = await pythonBackendService.processRepository(payload);
      
      res.json({
        success: true,
        message: `Successfully processed ${processedFiles.length} files from GitHub`,
        data: {
          repository: repoFullName,
          branch: branch,
          files_processed: processedFiles.length,
          files_failed: errors.length,
          timestamp: new Date().toISOString()
        },
        warnings: errors.length > 0 ? errors : undefined
      });
      
    } catch (error) {
      console.error('GitHub import error:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  },

  // Search functionality
  async search(req, res) {
    try {
      const { query, repository_id, branch, max_results, similarity_threshold } = req.body;
      
      if (!query) {
        return res.status(400).json({
          success: false,
          error: 'Query is required'
        });
      }
      
      const searchData = {
        query: query,
        repository_id: repository_id || 'default',
        branch: branch || 'main',
        max_results: max_results || 10,
        similarity_threshold: similarity_threshold || 0.3
      };
      
      const result = await pythonBackendService.search(searchData);
      
      if (result.success) {
        res.json({
          success: true,
          results: result.data.results,
          total_found: result.data.total_found
        });
      } else {
        res.status(500).json({
          success: false,
          error: result.error || 'Failed to search'
        });
      }
      
    } catch (error) {
      console.error('Search error:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  },

  // Test Python backend connection
  async testConnection(req, res) {
    try {
      console.log('Testing Python backend connection...');
      const result = await pythonBackendService.testConnection();
      
      console.log('Test result:', result);
      
      if (result.status === 'ok') {
        res.json({
          success: true,
          message: 'Python backend connection successful',
          data: result
        });
      } else {
        res.status(500).json({
          success: false,
          error: result.error || 'Failed to connect to Python backend',
          data: result
        });
      }
      
    } catch (error) {
      console.error('Test connection error:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  },

  // Get system status
  async getStatus(req, res) {
    try {
      const result = await pythonBackendService.getStatus();
      
      if (result.success) {
        res.json({
          success: true,
          status: result.data,
          sessions: sessionService.getStats()
        });
      } else {
        res.status(500).json({
          success: false,
          error: result.error || 'Failed to get status'
        });
      }
      
    } catch (error) {
      console.error('Status error:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  },

  // Cleanup function moved to session service

  // Get system status and health
  async getStatus(req, res) {
    try {
      const pythonBackendHealth = await pythonBackendService.healthCheck();
      
      res.json({
        success: true,
        status: 'healthy',
        pythonBackend: pythonBackendHealth,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Status check error:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  }
};

module.exports = aiController;
