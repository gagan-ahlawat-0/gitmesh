const { body, param, validationResult } = require('express-validator');

// Validation middleware
const validate = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      success: false,
      error: 'Validation failed',
      details: errors.array()
    });
  }
  next();
};

// Chat session validation rules
const validateCreateSession = [
  body('title').optional().isString().trim().isLength({ min: 1, max: 100 }),
  body('repositoryId').optional().isString().trim(),
  body('branch').optional().isString().trim(),
  validate
];

const validateUpdateSession = [
  param('sessionId').isUUID().withMessage('Invalid session ID'),
  body('title').optional().isString().trim().isLength({ min: 1, max: 100 }),
  validate
];

const validateSessionId = [
  param('sessionId').isUUID().withMessage('Invalid session ID'),
  validate
];

const validateUserId = [
  param('userId').isString().trim().notEmpty().withMessage('User ID is required'),
  validate
];

// Chat message validation rules
const validateSendMessage = [
  param('sessionId').isUUID().withMessage('Invalid session ID'),
  body('message').isString().trim().notEmpty().withMessage('Message is required'),
  body('context.files').optional().isArray(),
  body('context.files.*.path').optional().isString(),
  body('context.files.*.content').optional().isString(),
  body('context.files.*.branch').optional().isString(),
  validate
];

// Context validation rules
const validateCreateContext = [
  body('files').optional().isArray(),
  body('files.*.path').optional().isString(),
  body('files.*.content').optional().isString(),
  body('files.*.branch').optional().isString(),
  body('sources').optional().isArray(),
  body('repositoryId').optional().isString().trim(),
  body('branch').optional().isString().trim(),
  validate
];

const validateUpdateContext = [
  param('contextId').isUUID().withMessage('Invalid context ID'),
  body('action').isIn(['add_file', 'remove_file', 'update_files', 'update_sources']).withMessage('Invalid action'),
  body('fileId').optional().isString(),
  body('files').optional().isArray(),
  body('sources').optional().isArray(),
  validate
];

const validateContextId = [
  param('contextId').isUUID().withMessage('Invalid context ID'),
  validate
];

const validateRepositoryId = [
  param('repositoryId').isString().trim().notEmpty().withMessage('Repository ID is required'),
  validate
];

module.exports = {
  validateCreateSession,
  validateUpdateSession,
  validateSessionId,
  validateUserId,
  validateSendMessage,
  validateCreateContext,
  validateUpdateContext,
  validateContextId,
  validateRepositoryId
};
