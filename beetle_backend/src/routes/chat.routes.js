const express = require('express');
const router = express.Router();
const chatController = require('../controllers/chat.controller');
const { authMiddleware } = require('../middleware/auth.cjs');
const {
  validateCreateSession,
  validateUpdateSession,
  validateSessionId,
  validateUserId,
  validateSendMessage
} = require('../middleware/validation.cjs');

// Health check endpoint (no auth required)
router.get('/health', (req, res) => {
  res.json({
    success: true,
    message: 'Chat system is healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Apply authentication middleware to all routes below
router.use(authMiddleware);

// Chat session routes
router.post('/sessions', validateCreateSession, chatController.createSession);
router.get('/sessions/:sessionId', validateSessionId, chatController.getSession);
router.put('/sessions/:sessionId', validateUpdateSession, chatController.updateSession);
router.delete('/sessions/:sessionId', validateSessionId, chatController.deleteSession);
router.get('/users/:userId/sessions', validateUserId, chatController.getUserSessions);

// Chat message routes
router.post('/sessions/:sessionId/messages', validateSendMessage, chatController.sendMessage);
router.get('/sessions/:sessionId/messages', validateSessionId, chatController.getChatHistory);

// Context management routes (merged from context controller)
router.get('/sessions/:sessionId/context/stats', validateSessionId, chatController.getSessionContextStats);
router.put('/sessions/:sessionId/context', validateSessionId, chatController.updateSessionContext);

module.exports = router;
