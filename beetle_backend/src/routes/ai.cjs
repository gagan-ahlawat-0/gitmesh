const express = require('express');
const router = express.Router();
const { authMiddleware } = require('../middleware/auth.cjs');
const aiController = require('../controllers/ai.controller.js');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs').promises;

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: async (req, file, cb) => {
    const uploadDir = path.join(__dirname, '../../data/uploads');
    try {
      await fs.mkdir(uploadDir, { recursive: true });
      cb(null, uploadDir);
    } catch (error) {
      cb(error);
    }
  },
  filename: (req, file, cb) => {
    const uniqueName = `${Date.now()}-${uuidv4()}-${file.originalname}`;
    cb(null, uniqueName);
  }
});

const upload = multer({ storage });

// Chat functionality has been moved to dedicated chat.routes.js
// This route now focuses on AI processing and GitHub integration

// Test Python backend connection
router.get('/test-connection', authMiddleware, aiController.testConnection);

// Import files and embed them in vector database
router.post('/import', authMiddleware, upload.array('files'), async (req, res) => {
  try {
    const { repository_id, branch, source_type } = req.body;
    const files = req.files || [];
    
    if (!Array.isArray(files)) {
      return res.status(400).json({ error: 'Invalid files parameter: must be an array' });
    }
    if (files.length === 0) {
      return res.status(400).json({ error: 'No files provided' });
    }
    
    // Prepare data for Python pipeline
    const importData = {
      repository_id: repository_id || 'default',
      branch: branch || 'main',
      source_type: source_type || 'file',
      files: files.map(file => ({
        path: file.path,
        originalName: file.originalname,
        size: file.size,
        mimetype: file.mimetype
      }))
    };
    
    // Call Python embedding pipeline
    const result = await aiController.pythonBackendService.importFiles(importData);
    
    if (result.success) {
      res.json({
        success: true,
        message: `Successfully imported and embedded ${files.length} files`,
        data: result.data
      });
    } else {
      res.status(500).json({
        success: false,
        error: result.error || 'Failed to import files'
      });
    }
    
  } catch (error) {
    console.error('Import error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Import files from GitHub
router.post('/import-github', authMiddleware, aiController.importFromGitHub);

// Search functionality
router.post('/search', authMiddleware, aiController.search);

// Get AI system status
router.get('/status', authMiddleware, aiController.getStatus);

// Health check endpoint (no auth required)
router.get('/health', aiController.getStatus);

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    service: 'AI Backend',
    version: '1.0.0'
  });
});

// WebSocket server for real-time chat
let wss = null;

// Initialize WebSocket server
function initializeWebSocket(server) {
  const WebSocket = require('ws');
  wss = new WebSocket.Server({ server, path: '/api/ai/chat/ws' });
  
  console.log('WebSocket server initialized on /api/ai/chat/ws');
  
  wss.on('connection', (ws, req) => {
    console.log('WebSocket client connected');
    
    // Extract session ID from query parameters
    const url = new URL(req.url, `http://${req.headers.host}`);
    const sessionId = url.searchParams.get('session_id');
    
    if (sessionId) {
      ws.sessionId = sessionId;
      console.log(`Client connected for session: ${sessionId}`);
    }
    
    ws.on('message', async (data) => {
      try {
        const message = JSON.parse(data);
        console.log('Received WebSocket message:', message);
        
        if (message.type === 'message' && message.data?.message) {
          // Handle chat message
          const chatData = {
            message: message.data.message,
            files: message.data.files || [],
            repository_id: message.data.repository_id || 'default',
            session_id: sessionId,
      timestamp: new Date().toISOString()
    };

          try {
            // Send to Python backend
            const result = await aiController.pythonBackendService.chatWithFiles(chatData);
            
            if (result.success) {
              // Send response back to client
              ws.send(JSON.stringify({
                type: 'message',
        data: {
                  response: result.response,
                  referenced_files: result.referenced_files || [],
                  code_snippets: result.code_snippets || []
                },
                session_id: sessionId
              }));
            } else {
              ws.send(JSON.stringify({
                type: 'error',
                data: { error: result.error || 'Failed to get response' },
                session_id: sessionId
              }));
            }
  } catch (error) {
            console.error('WebSocket chat error:', error);
            ws.send(JSON.stringify({
              type: 'error',
              data: { error: error.message },
              session_id: sessionId
            }));
          }
        }
      } catch (error) {
        console.error('WebSocket message parsing error:', error);
        ws.send(JSON.stringify({
          type: 'error',
          data: { error: 'Invalid message format' }
        }));
      }
    });
    
    ws.on('close', () => {
      console.log(`WebSocket client disconnected from session: ${sessionId}`);
    });
    
    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
  });
}

// Export the router and WebSocket initialization function
module.exports = { router, initializeWebSocket }; 