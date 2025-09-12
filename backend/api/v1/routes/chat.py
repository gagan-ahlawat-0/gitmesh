"""
Chat API routes that bridge to TARS v1 AI Import system
"""
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import structlog

from .dependencies import get_current_user
from models.api.auth_models import User
from models.api.ai_import_models import (
    TarsImportRequest, ImportSourceType, ImportStatus
)

# Safe imports for TARS integration
try:
    from .ai_import import TarsImportService
    from integrations.tars.v1.tars_wrapper import GitMeshTarsWrapper
    TARS_IMPORT_AVAILABLE = True
except ImportError:
    TARS_IMPORT_AVAILABLE = False
    TarsImportService = None
    GitMeshTarsWrapper = None

logger = structlog.get_logger(__name__)
router = APIRouter()

# In-memory storage for demo (in production, use database)
chat_sessions: Dict[str, Dict[str, Any]] = {}
chat_messages: Dict[str, List[Dict[str, Any]]] = {}

class ChatTarsService:
    """Service to bridge chat interface to TARS import system"""
    
    def __init__(self):
        if TARS_IMPORT_AVAILABLE:
            self.tars_service = TarsImportService()
        else:
            self.tars_service = None
    
    def _generate_intelligent_response(self, message: str, context: Dict[str, Any] = None) -> str:
        """Generate an intelligent response based on message content when TARS is not available"""
        message_lower = message.lower().strip()
        
        # Code-related queries
        if any(word in message_lower for word in ['code', 'function', 'class', 'method', 'variable', 'bug', 'error', 'debug']):
            return f"I can help you analyze the code. Based on your message about '{message}', I'd need to examine the relevant files in your repository. Could you share more context about which files or components you're working with?"
        
        # Repository queries
        elif any(word in message_lower for word in ['repo', 'repository', 'branch', 'commit', 'file', 'directory']):
            return f"I can help you explore the repository structure. For your question about '{message}', I can analyze the codebase and provide insights. What specific aspect would you like me to focus on?"
        
        # Documentation queries
        elif any(word in message_lower for word in ['how', 'what', 'why', 'explain', 'documentation', 'readme']):
            return f"I'll help explain that for you. Regarding '{message}', let me analyze the available documentation and code to provide you with a comprehensive answer. What level of detail would be most helpful?"
        
        # Implementation queries
        elif any(word in message_lower for word in ['implement', 'create', 'build', 'develop', 'add', 'feature']):
            return f"I can assist with implementation. For '{message}', I'll need to understand the current codebase structure and requirements. Could you provide more details about what you're trying to achieve?"
        
        # General questions
        elif any(word in message_lower for word in ['help', 'support', 'assist', 'guide']):
            return f"I'm here to help! Regarding '{message}', I can analyze your codebase, explain functionality, help with debugging, or assist with implementation. What would be most useful for you right now?"
        
        # Default intelligent response
        else:
            return f"I understand you're asking about: '{message}'. I can analyze your codebase and provide insights. Could you provide a bit more context about what you're trying to accomplish or which part of the project you're focusing on?"
    
    async def create_session(self, user_id: str, title: str = None, repository_id: str = None, branch: str = None):
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "title": title or f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "repositoryId": repository_id,
            "branch": branch,
            "messages": [],
            "selectedFiles": [],
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat(),
            "userId": user_id
        }
        
        chat_sessions[session_id] = session
        chat_messages[session_id] = []
        
        return session
    
    async def get_session(self, session_id: str, user_id: str):
        """Get a chat session"""
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = chat_sessions[session_id]
        if session.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Include messages
        session["messages"] = chat_messages.get(session_id, [])
        return session
    
    async def send_message(self, session_id: str, user_id: str, message: str, context: Dict[str, Any] = None):
        """Send a message and get AI response via TARS"""
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = chat_sessions[session_id]
        if session.get("userId") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Debug: Log the incoming request
        logger.info(f"Chat request - session: {session_id}, message: {message[:100]}...")
        logger.info(f"Chat context received: {context}")
        if context and context.get("files"):
            files = context.get("files", [])
            logger.info(f"Files in context: {len(files)} files")
            for i, file in enumerate(files[:3]):  # Log first 3 files
                logger.info(f"  File {i+1}: {file.get('path', 'unknown')} - content length: {len(file.get('content', ''))}")
        
        # Create user message
        user_message = {
            "id": str(uuid.uuid4()),
            "type": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "files": []
        }
        
        # Add user message to history
        if session_id not in chat_messages:
            chat_messages[session_id] = []
        chat_messages[session_id].append(user_message)
        
        # Generate AI response via TARS with full knowledge base integration
        confidence = 0.6
        knowledge_used = 0
        sources = []
        
        try:
            if self.tars_service and TARS_IMPORT_AVAILABLE:
                # Create TARS wrapper for this session
                wrapper = GitMeshTarsWrapper(
                    user_id=user_id,
                    project_id=session.get("repositoryId", "default"),
                    repository_id=session.get("repositoryId"),
                    branch=session.get("branch", "main")
                )
                
                # Get chat history for context
                session_history = chat_messages.get(session_id, [])
                
                # Process message through comprehensive TARS system
                tars_response = await wrapper.process_chat_message(
                    message=message,
                    context=context or {},
                    session_history=session_history
                )
                
                # Extract content and metadata
                assistant_content = tars_response.get("content", "I'm processing your request...")
                confidence = tars_response.get("confidence", 0.7)
                sources = tars_response.get("sources", [])
                knowledge_used = tars_response.get("knowledge_entries_used", 0)
                
                # Add metadata to response if available
                if knowledge_used > 0:
                    assistant_content += f"\n\n*Based on {knowledge_used} knowledge base entries*"
                
                if sources:
                    assistant_content += f"\n\n*Sources: {', '.join(sources[:3])}*"
                
            else:
                # Intelligent fallback when TARS is not available
                assistant_content = self._generate_intelligent_response(message, context)
        
        except Exception as e:
            logger.error(f"Error processing message with TARS: {e}")
            assistant_content = f"I encountered an error accessing the knowledge base. Let me help you with: '{message}'. Could you provide more context about what you're trying to accomplish?"
        
        # Create assistant message
        assistant_message = {
            "id": str(uuid.uuid4()),
            "type": "assistant", 
            "content": assistant_content,
            "timestamp": datetime.now().isoformat(),
            "files": [],
            "metadata": {
                "confidence": confidence,
                "knowledge_used": knowledge_used,
                "sources_count": len(sources),
                "tars_available": self.tars_service is not None and TARS_IMPORT_AVAILABLE
            }
        }
        
        # Add assistant message to history
        chat_messages[session_id].append(assistant_message)
        
        # Update session timestamp
        session["updatedAt"] = datetime.now().isoformat()
        session["messages"] = chat_messages[session_id]
        
        return {
            "userMessage": user_message,
            "assistantMessage": assistant_message,
            "session": session
        }

# Initialize service
chat_service = ChatTarsService()

@router.post("/sessions")
async def create_chat_session(
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = await chat_service.create_session(
            user_id=str(current_user.id),
            title=request.get("title"),
            repository_id=request.get("repositoryId"),
            branch=request.get("branch")
        )
        
        return {
            "success": True,
            "session": session
        }
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = await chat_service.get_session(session_id, str(current_user.id))
        return {
            "success": True,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session")

@router.put("/sessions/{session_id}")
async def update_chat_session(
    session_id: str,
    updates: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = chat_sessions[session_id]
        if session.get("userId") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update allowed fields
        allowed_fields = ["title", "selectedFiles"]
        for field in allowed_fields:
            if field in updates:
                session[field] = updates[field]
        
        session["updatedAt"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Delete a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = chat_sessions[session_id]
        if session.get("userId") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete session and messages
        del chat_sessions[session_id]
        if session_id in chat_messages:
            del chat_messages[session_id]
        
        return {
            "success": True,
            "message": "Session deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all sessions for a user"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        user_sessions = []
        for session in chat_sessions.values():
            if session.get("userId") == user_id:
                session_copy = session.copy()
                session_copy["messages"] = chat_messages.get(session["id"], [])
                user_sessions.append(session_copy)
        
        # Sort by updated time (newest first)
        user_sessions.sort(key=lambda x: x["updatedAt"], reverse=True)
        
        return {
            "success": True,
            "sessions": user_sessions
        }
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Send a message in a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        message = request.get("message", "")
        context = request.get("context", {})
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        result = await chat_service.send_message(
            session_id=session_id,
            user_id=str(current_user.id),
            message=message,
            context=context
        )
        
        return {
            "success": True,
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")

@router.get("/sessions/{session_id}/messages")
async def get_chat_history(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get chat history for a session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = await chat_service.get_session(session_id, str(current_user.id))
        messages = chat_messages.get(session_id, [])
        
        return {
            "success": True,
            "messages": messages,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat history")

@router.get("/sessions/{session_id}/context/stats")
async def get_session_context_stats(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get context stats for a session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session = await chat_service.get_session(session_id, str(current_user.id))
        selected_files = session.get("selectedFiles", [])
        
        stats = {
            "totalFiles": len(selected_files),
            "totalSources": len(selected_files),
            "totalTokens": sum(len(f.get("content", "").split()) for f in selected_files),
            "averageTokensPerFile": 0,
            "createdAt": session["createdAt"],
            "updatedAt": session["updatedAt"]
        }
        
        if stats["totalFiles"] > 0:
            stats["averageTokensPerFile"] = stats["totalTokens"] / stats["totalFiles"]
        
        return {
            "success": True,
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting context stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get context stats")

@router.put("/sessions/{session_id}/context")
async def update_session_context(
    session_id: str,
    request: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update session context (add/remove files)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = chat_sessions[session_id]
        if session.get("userId") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        action = request.get("action")
        files = request.get("files", [])
        
        if action == "add_files":
            session["selectedFiles"].extend(files)
        elif action == "remove_files":
            # Remove files by path
            file_paths = {f["path"] for f in files}
            session["selectedFiles"] = [
                f for f in session["selectedFiles"] 
                if f["path"] not in file_paths
            ]
        elif action == "clear_files":
            session["selectedFiles"] = []
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        session["updatedAt"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session context: {e}")
        raise HTTPException(status_code=500, detail="Failed to update context")
