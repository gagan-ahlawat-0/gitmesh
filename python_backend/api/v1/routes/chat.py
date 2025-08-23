"""
Chat API routes for the RAG system with session-based context management.
Aligned with JavaScript backend session management approach.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog
import uuid
from datetime import datetime

from core.session_manager import get_session_manager
from models.api.session_models import (
    ChatSession, SessionContext, FileContext, SessionMessage,
    SessionStats, SessionContextUpdate, SessionContextResponse
)
from utils.file_utils import get_file_processor
from models.api.file_models import DocumentChunk, ChunkMetadata

logger = structlog.get_logger(__name__)
router = APIRouter()


class FileData(BaseModel):
    path: str
    branch: str
    content: str
    size: int
    is_public: bool


class SessionChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: str


class SessionChatResponse(BaseModel):
    success: bool
    response: str
    session_id: str
    message_id: str
    referenced_files: List[str] = []
    code_snippets: List[Dict[str, Any]] = []
    data: Dict[str, Any] = {}


class CreateSessionRequest(BaseModel):
    user_id: str
    title: str = "New Chat"
    repository_id: Optional[str] = None
    branch: Optional[str] = None


class CreateSessionResponse(BaseModel):
    success: bool
    session: Dict[str, Any]


class GetSessionResponse(BaseModel):
    success: bool
    session: Dict[str, Any]


class GetSessionMessagesResponse(BaseModel):
    success: bool
    messages: List[Dict[str, Any]]
    session: Dict[str, Any]


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    repository_id: Optional[str] = None
    branch: Optional[str] = None


class UpdateSessionResponse(BaseModel):
    success: bool
    session: Dict[str, Any]


class DeleteSessionResponse(BaseModel):
    success: bool
    message: str


class GetUserSessionsResponse(BaseModel):
    success: bool
    sessions: List[Dict[str, Any]]


class GetSessionStatsResponse(BaseModel):
    success: bool
    stats: Dict[str, Any]


class ProcessRepoRequest(BaseModel):
    repository: str
    repository_id: str
    branch: str
    source_type: str
    files: List[FileData]
    timestamp: str


class ProcessRepoResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]


class ImportRequest(BaseModel):
    repository_id: str
    branch: str
    source_type: str
    files: List[FileData]
    timestamp: str


class ImportResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]


class SearchRequest(BaseModel):
    query: str
    repository_id: str
    limit: int = 10


class SearchResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]]
    total: int


# Session Management Endpoints

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new chat session."""
    try:
        session_manager = get_session_manager()
        
        session = session_manager.create_session(
            user_id=request.user_id,
            title=request.title,
            repository_id=request.repository_id,
            branch=request.branch
        )
        
        return CreateSessionResponse(
            success=True,
            session=session.get_session_summary()
        )
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=GetSessionResponse)
async def get_session(session_id: str):
    """Get a chat session by ID."""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return GetSessionResponse(
            success=True,
            session=session.get_session_summary()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sessions/{session_id}", response_model=UpdateSessionResponse)
async def update_session(session_id: str, request: UpdateSessionRequest):
    """Update a chat session."""
    try:
        session_manager = get_session_manager()
        
        updates = {}
        if request.title is not None:
            updates['title'] = request.title
        if request.repository_id is not None:
            updates['repository_id'] = request.repository_id
        if request.branch is not None:
            updates['branch'] = request.branch
        
        session = session_manager.update_session(session_id, updates)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return UpdateSessionResponse(
            success=True,
            session=session.get_session_summary()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(session_id: str):
    """Delete a chat session."""
    try:
        session_manager = get_session_manager()
        success = session_manager.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return DeleteSessionResponse(
            success=True,
            message="Session deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/sessions", response_model=GetUserSessionsResponse)
async def get_user_sessions(user_id: str):
    """Get all sessions for a user."""
    try:
        session_manager = get_session_manager()
        sessions = session_manager.get_user_sessions(user_id)
        
        return GetUserSessionsResponse(
            success=True,
            sessions=[session.get_session_summary() for session in sessions]
        )
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Session Context Management Endpoints

@router.get("/sessions/{session_id}/context/stats", response_model=GetSessionStatsResponse)
async def get_session_context_stats(session_id: str):
    """Get session context statistics."""
    try:
        session_manager = get_session_manager()
        stats = session_manager.get_session_stats(session_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return GetSessionStatsResponse(
            success=True,
            stats=stats.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sessions/{session_id}/context", response_model=SessionContextResponse)
async def update_session_context(session_id: str, request: SessionContextUpdate):
    """Update session context (add/remove files)."""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if request.action == "add_files":
            if not request.files:
                raise HTTPException(status_code=400, detail="Files required for add_files action")
            
            added_count = 0
            for file_data in request.files:
                success = session_manager.add_file_to_session(session_id, file_data)
                if success:
                    added_count += 1
            
            message = f"Added {added_count} files to session context"
            
        elif request.action == "remove_files":
            if not request.files:
                raise HTTPException(status_code=400, detail="Files required for remove_files action")
            
            removed_count = 0
            for file_data in request.files:
                success = session_manager.remove_file_from_session(
                    session_id, 
                    file_data['path'], 
                    file_data.get('branch', 'main')
                )
                if success:
                    removed_count += 1
            
            message = f"Removed {removed_count} files from session context"
            
        elif request.action == "clear_files":
            session_manager.clear_session_files(session_id)
            message = "Cleared all files from session context"
        
        # Get updated session
        updated_session = session_manager.get_session(session_id)
        context_summary = session_manager.get_session_context_summary(session_id)
        
        return SessionContextResponse(
            success=True,
            message=message,
            session=updated_session.get_session_summary() if updated_session else None,
            context_summary=context_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Session Message Endpoints

@router.post("/sessions/{session_id}/messages", response_model=SessionChatResponse)
async def send_session_message(session_id: str, request: SessionChatRequest):
    """Send a message in a chat session."""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Add user message to session
        user_message = session_manager.add_message_to_session(
            session_id=session_id,
            role="user",
            content=request.message
        )
        
        if not user_message:
            raise HTTPException(status_code=500, detail="Failed to add user message")
        
        # Get the global orchestrator instance
        from app import get_global_orchestrator
        orchestrator = get_global_orchestrator()
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Prepare context from session files
        context_files = []
        for file_context in session.context.files.values():
            context_files.append({
                "path": file_context.path,
                "branch": file_context.branch,
                "content": file_context.content,
                "size": file_context.size,
                "is_public": True
            })
        
        # Process message with RAG pipeline
        enhanced_query = f"""Context from session files:

{chr(10).join([f"File: {f['path']} (Branch: {f['branch']})\nContent:\n{f['content']}\n" + "-" * 50 for f in context_files])}

User Question: {request.message}

Please provide a detailed response based on the code and files provided above. 
- Reference specific file names and line numbers where applicable
- Include relevant code snippets with proper citations
- Provide confidence scores for your responses
- If context is insufficient, clearly state what additional information would be helpful"""

        # Get conversation history for context
        conversation_history = session_manager.get_session_messages(session_id, limit=10)
        history_for_agent = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation_history
        ]
        
        # Create enhanced task for the intelligent code chat agent
        from agents.base.base_agent import AgentTask
        
        task = AgentTask(
            task_type="intelligent_code_chat",
            input_data={
                "query": request.message,
                "conversation_history": history_for_agent,
                "context_files": [f.path for f in session.context.files.values()],
                "repository_id": session.repository_id or "default"
            },
            parameters={
                "temperature": 0.7,
                "max_tokens": 2500,
                "include_code_snippets": True,
                "include_citations": True,
                "include_confidence": True
            }
        )
        
        # Get the enhanced code chat agent
        agents = orchestrator.agent_registry.get_agents_by_type("code_chat")
        if not agents:
            raise HTTPException(status_code=400, detail="Code chat agent not found")
        agent = agents[0]  # Use the first available agent
        
        # Execute the task
        result = await agent.execute(task)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {result.error_message}")
        
        # Extract response and metadata from intelligent response
        output = result.output
        response = output.get("response", "No response generated")
        classification = output.get("classification", {})
        metadata = output.get("metadata", {})
        
        # Extract code snippets from response
        import re
        code_block_pattern = r"```(\w+)?\n(.*?)```"
        code_matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        code_snippets = []
        for lang, code in code_matches:
            if code.strip():
                code_snippets.append({
                    "language": lang or "text",
                    "code": code.strip(),
                    "filePath": None,  # From response
                    "source": "response"
                })
        
        # Add assistant message to session with enhanced metadata
        assistant_message = session_manager.add_message_to_session(
            session_id=session_id,
            role="assistant",
            content=response,
            files_referenced=[f.path for f in session.context.files.values()],
            code_snippets=code_snippets,
            metadata={
                "agent_used": agent.name,
                "processing_time": result.metadata.get("processing_time", 0),
                "tokens_used": result.metadata.get("tokens_used", 0),
                "query_classification": classification.get("query_type", "unknown"),
                "response_style": classification.get("response_style", "conversational"),
                "confidence": classification.get("confidence", 0.0),
                "user_intent": classification.get("user_intent", "unknown")
            }
        )
        
        if not assistant_message:
            raise HTTPException(status_code=500, detail="Failed to add assistant message")
        
        return SessionChatResponse(
            success=True,
            response=response,
            session_id=session_id,
            message_id=assistant_message.message_id,
            referenced_files=[f.path for f in session.context.files.values()],
            code_snippets=code_snippets,
            data={
                "agent_used": agent.name,
                "processing_time": result.metadata.get("processing_time", 0),
                "tokens_used": result.metadata.get("tokens_used", 0),
                "files_processed": len(session.context.files),
                "context_length": sum(len(f.content) for f in session.context.files.values()),
                "rag_enabled": True,
                "query_classification": classification.get("query_type", "unknown"),
                "response_style": classification.get("response_style", "conversational"),
                "confidence": classification.get("confidence", 0.0),
                "user_intent": classification.get("user_intent", "unknown"),
                "intelligent_response": True
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending session message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=GetSessionMessagesResponse)
async def get_session_messages(session_id: str, limit: Optional[int] = None):
    """Get messages for a chat session."""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = session_manager.get_session_messages(session_id, limit)
        
        return GetSessionMessagesResponse(
            success=True,
            messages=[message.dict() for message in messages],
            session=session.get_session_summary()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoints for backward compatibility

@router.post("/chat", response_model=Dict[str, Any])
async def chat(request: Dict[str, Any]):
    """Legacy basic chat endpoint."""
    try:
        # Get the global orchestrator instance
        from app import get_global_orchestrator
        orchestrator = get_global_orchestrator()
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Create an intelligent task for the agent
        from agents.base.base_agent import AgentTask
        
        task = AgentTask(
            task_type="intelligent_code_chat",
            input_data={
                "query": request.get("query", ""),
                "conversation_history": request.get("conversation_history", []),
                "context_files": request.get("context_files", [])
            },
            parameters={
                "temperature": request.get("temperature", 0.7),
                "max_tokens": request.get("max_tokens", 1000)
            }
        )
        
        # Get the appropriate agent
        agents = orchestrator.agent_registry.get_agents_by_type("code_chat")
        if not agents:
            # Debug: list all available agents
            available_agents = orchestrator.agent_registry.list_registered_agents()
            logger.error(f"No code chat agent found. Available agents: {available_agents}")
            raise HTTPException(status_code=400, detail=f"Code chat agent not found. Available agents: {available_agents}")
        agent = agents[0]  # Use the first available agent
        
        # Execute the task
        result = await agent.execute(task)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {result.error_message}")
        
        # Extract response and classification
        output = result.output
        response = output.get("response", "No response generated")
        classification = output.get("classification", {})
        
        return {
            "response": response,
            "metadata": {
                "agent_used": agent.name,
                "processing_time": result.metadata.get("processing_time", 0),
                "tokens_used": result.metadata.get("tokens_used", 0),
                "query_classification": classification.get("query_type", "unknown"),
                "response_style": classification.get("response_style", "conversational"),
                "confidence": classification.get("confidence", 0.0),
                "intelligent_response": True
            }
        }
        
    except Exception as e:
        logger.error("Chat endpoint error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-with-files", response_model=Dict[str, Any])
async def chat_with_files(request: Dict[str, Any]):
    """Enhanced chat with files endpoint that implements proper RAG functionality."""
    try:
        logger.info(f"Enhanced RAG chat-with-files request with {len(request.get('files', []))} files")
        
        # Get the global orchestrator instance
        from app import get_global_orchestrator
        orchestrator = get_global_orchestrator()
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Process files and validate content
        files = request.get('files', [])
        message = request.get('message', '')
        repository_id = request.get('repository_id', 'default')
        
        # Validate file content with enhanced metadata
        validated_files = []
        content_issues = []
        
        for file_data in files:
            file_path = file_data.get('path', '')
            file_content = file_data.get('content', '')
            
            # Check if content is placeholder or empty
            if not file_content or file_content == "Imported file content will be loaded...":
                content_issues.append(f"File {file_path}: Missing or placeholder content")
                continue
            
            # Check content length (basic validation)
            if len(file_content) < 10:  # Very short content might be incomplete
                content_issues.append(f"File {file_path}: Content too short ({len(file_content)} chars)")
            
            # Enhanced file metadata
            validated_files.append({
                'path': file_path,
                'name': file_data.get('name', file_path.split('/')[-1]),
                'content': file_content,
                'url': file_data.get('url', ''),
                'raw_url': file_data.get('raw_url', ''),
                'branch': file_data.get('branch', 'main'),
                'size': len(file_content),
                'repository_id': file_data.get('repository_id', repository_id),
                'owner': file_data.get('owner', ''),
                'repo': file_data.get('repo', ''),
                'last_modified': file_data.get('last_modified', ''),
                'is_public': file_data.get('is_public', True),
                'language': file_data.get('language', 'text'),
                'file_type': file_data.get('file_type', 'text'),
                'sha': file_data.get('sha', ''),
                'error': file_data.get('error', False)
            })
        
        # Log content validation results
        if content_issues:
            logger.warning(f"File content issues detected: {content_issues}")
        
        if not validated_files:
            return {
                "success": False,
                "error": "No valid file content provided. Please ensure files are properly loaded with complete content.",
                "content_issues": content_issues,
                "data": {
                    "files_processed": 0,
                    "rag_enabled": False,
                    "content_validation_failed": True
                }
            }
        
        # STEP 1: Process and store files in vector database (RAG setup)
        logger.info("Processing files for vector storage...")
        processed_files = []
        storage_errors = []
        
        for file_data in validated_files:
            try:
                logger.info(f"Processing file for vector storage: {file_data['path']}")
                
                # Create document chunks from file content
                file_processor = get_file_processor()
                
                # Process the file content
                processed_content = await file_processor.process_file_content(
                    content=file_data['content'],
                    filename=file_data['path'],
                    file_type=file_data['file_type']
                )
                
                # Create document chunks with proper metadata
                chunks = []
                for i, element in enumerate(processed_content.get("elements", [])):
                    if element.get("text", "").strip():
                        chunk_metadata = ChunkMetadata(
                            chunk_id=str(uuid.uuid4()),  # Generate proper UUID for Qdrant
                            file_id=f"{repository_id}_{file_data['path']}",
                            chunk_index=i,
                            start_line=element.get("start_line", 0),
                            end_line=element.get("end_line", 0),
                            start_char=element.get("start_char", 0),
                            end_char=element.get("end_char", len(element.get("text", ""))),
                            chunk_type="text",
                            language=file_data['language'],
                            complexity_score=0.0,
                            filename=file_data['path'],
                            file_size=file_data['size'],
                            file_type=file_data['file_type']
                        )
                        
                        chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),  # Generate proper UUID for Qdrant
                            file_id=f"{repository_id}_{file_data['path']}",
                            content=element["text"],
                            metadata=chunk_metadata,
                            created_at=datetime.now().isoformat()
                        )
                        chunks.append(chunk)
                
                # Add chunks to vector store
                if chunks:
                    success = await orchestrator.qdrant_client.upsert_chunks_with_embeddings(
                        chunks, 
                        generate_embeddings=True,
                        orchestrator=orchestrator
                    )
                    if success:
                        processed_files.append({
                            "path": file_data['path'],
                            "chunks_added": len(chunks),
                            "size": file_data['size']
                        })
                        logger.info(f"Successfully stored {file_data['path']} - {len(chunks)} chunks added to vector store")
                    else:
                        storage_errors.append(f"Failed to add chunks for {file_data['path']}")
                else:
                    storage_errors.append(f"No content extracted from {file_data['path']}")
                    
            except Exception as e:
                error_msg = f"Error processing {file_data['path']}: {str(e)}"
                storage_errors.append(error_msg)
                logger.error(error_msg)
        
        # STEP 2: Use RAG retrieval to get relevant context
        logger.info("Performing RAG retrieval for relevant context...")
        relevant_chunks = []
        
        try:
            # Use the vector retriever to get relevant chunks
            relevant_chunks = await orchestrator.vector_retriever.retrieve_relevant_chunks(
                query=message,
                limit=10,  # Get top 10 most relevant chunks
                score_threshold=0.6,  # Lower threshold for better coverage
                filters={"repository_id": repository_id} if repository_id != "default" else None
            )
            
            logger.info(f"RAG retrieval found {len(relevant_chunks)} relevant chunks")
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            # Fallback to direct file content if RAG fails
            relevant_chunks = []
        
        # STEP 3: Create enhanced context combining RAG results and direct file content
        context_sources = []
        
        # Add RAG-retrieved chunks
        if relevant_chunks:
            rag_context = "Relevant information from knowledge base:\n\n"
            for chunk in relevant_chunks:
                rag_context += f"Source: {chunk.get('payload', {}).get('filename', 'Unknown')}\n"
                rag_context += f"Content: {chunk.get('payload', {}).get('content', '')}\n"
                rag_context += f"Relevance Score: {chunk.get('score', 0):.3f}\n"
                rag_context += "-" * 50 + "\n"
            context_sources.append(rag_context)
        
        # Add direct file content for immediate context
        file_contexts = []
        for file_data in validated_files:
            if file_data.get('error'):
                file_context = f"""File: {file_data['path']} (ERROR: {file_data['content']})
Repository: {file_data['repository_id']}
Branch: {file_data['branch']}
{'-' * 80}"""
            else:
                file_context = f"""File: {file_data['path']}
Name: {file_data['name']}
Repository: {file_data['repository_id']}
Branch: {file_data['branch']}
Language: {file_data['language']}
Type: {file_data['file_type']}
URL: {file_data['url']}
Raw URL: {file_data['raw_url']}
Size: {file_data['size']} characters
Last Modified: {file_data['last_modified']}
Owner: {file_data['owner']}
Repo: {file_data['repo']}

Content:
{file_data['content']}
{'-' * 80}"""
            file_contexts.append(file_context)
        
        if file_contexts:
            context_sources.append("Current conversation files:\n\n" + "\n".join(file_contexts))
        
        # Combine all context sources
        combined_context = "\n\n".join(context_sources)
        
        enhanced_query = f"""Context Information:

{combined_context}

User Question: {message}

Please provide a detailed response based on the context information above. 
- Reference specific file names and line numbers where applicable
- Include relevant code snippets with proper citations
- Provide confidence scores for your responses
- If context is insufficient, clearly state what additional information would be helpful
- Use both the knowledge base and current file content to provide accurate and comprehensive answers"""

        # STEP 4: Create enhanced task for the intelligent code chat agent
        from agents.base.base_agent import AgentTask
        
        task = AgentTask(
            task_type="intelligent_code_chat",
            input_data={
                "query": message,
                "conversation_history": request.get("conversation_history", []),
                "context_files": [f['path'] for f in validated_files],
                "file_contents": {f['path']: f['content'] for f in validated_files},
                "file_metadata": {f['path']: {
                    'name': f['name'],
                    'url': f['url'],
                    'raw_url': f['raw_url'],
                    'branch': f['branch'],
                    'language': f['language'],
                    'file_type': f['file_type'],
                    'size': f['size'],
                    'repository_id': f['repository_id'],
                    'owner': f['owner'],
                    'repo': f['repo'],
                    'last_modified': f['last_modified'],
                    'error': f['error']
                } for f in validated_files},
                "repository_id": repository_id,
                "rag_context": relevant_chunks,
                "rag_enabled": len(relevant_chunks) > 0
            },
            parameters={
                "temperature": 0.7,
                "max_tokens": 3000,
                "include_code_snippets": True,
                "include_citations": True,
                "include_confidence": True,
                "file_content_available": True,
                "enhanced_metadata": True,
                "rag_enabled": True
            }
        )
        
        # Get the enhanced code chat agent
        agents = orchestrator.agent_registry.get_agents_by_type("code_chat")
        if not agents:
            # Debug: list all available agents
            available_agents = orchestrator.agent_registry.list_registered_agents()
            logger.error(f"No code chat agent found. Available agents: {available_agents}")
            raise HTTPException(status_code=400, detail=f"Code chat agent not found. Available agents: {available_agents}")
        agent = agents[0]  # Use the first available agent
        
        # Execute the task with timeout
        import asyncio
        try:
            result = await asyncio.wait_for(agent.execute(task), timeout=45.0)  # 45 second timeout
        except asyncio.TimeoutError:
            # Provide a simple fallback response instead of failing
            logger.warning("Agent execution timed out, providing fallback response")
            fallback_response = f"I'm analyzing the files you've selected: {', '.join([f['path'] for f in validated_files])}. Based on the content and knowledge base, I can help you understand the code structure and answer questions about the implementation. What specific aspect would you like me to focus on?"
            
            return {
                "success": True,
                "response": fallback_response,
                "referenced_files": [f['path'] for f in validated_files],
                "code_snippets": [],
                "data": {
                    "agent_used": "fallback",
                    "processing_time": 0,
                    "tokens_used": 0,
                    "files_processed": len(validated_files),
                    "files_stored": len(processed_files),
                    "files_with_content": len([f for f in validated_files if not f.get('error')]),
                    "files_with_errors": len([f for f in validated_files if f.get('error')]),
                    "total_content_size": sum(f['size'] for f in validated_files),
                    "rag_enabled": True,
                    "rag_chunks_retrieved": len(relevant_chunks),
                    "timeout_fallback": True,
                    "file_content_available": True,
                    "vector_storage_success": len(storage_errors) == 0
                }
            }
        
        if not result.success:
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {result.error_message}")
        
        # Extract response and classification
        output = result.output
        response = output.get("response", "No response generated")
        classification = output.get("classification", {})
        
        return {
            "success": True,
            "response": response,
            "referenced_files": [f['path'] for f in validated_files],
            "code_snippets": [],
            "data": {
                "agent_used": agent.name,
                "processing_time": result.metadata.get("processing_time", 0),
                "tokens_used": result.metadata.get("tokens_used", 0),
                "files_processed": len(validated_files),
                "files_stored": len(processed_files),
                "files_with_content": len([f for f in validated_files if not f.get('error')]),
                "files_with_errors": len([f for f in validated_files if f.get('error')]),
                "total_content_size": sum(f['size'] for f in validated_files),
                "rag_enabled": True,
                "rag_chunks_retrieved": len(relevant_chunks),
                "vector_storage_success": len(storage_errors) == 0,
                "storage_errors": storage_errors if storage_errors else None,
                "query_classification": classification.get("query_type", "unknown"),
                "response_style": classification.get("response_style", "conversational"),
                "confidence": classification.get("confidence", 0.0),
                "intelligent_response": True,
                "file_content_available": True,
                "content_validation_passed": True,
                "rag_implementation": "full"
            }
        }
        
    except Exception as e:
        logger.error("Enhanced RAG chat-with-files error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector-store-status", response_model=Dict[str, Any])
async def get_vector_store_status():
    """Get vector store status and statistics."""
    try:
        # Get the global orchestrator instance
        from app import get_global_orchestrator
        orchestrator = get_global_orchestrator()
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Get vector store statistics
        try:
            # Get collection info from Qdrant
            collection_info = await orchestrator.qdrant_client.client.get_collection(
                collection_name=orchestrator.qdrant_client.collection_name
            )
            
            # Get collection statistics
            collection_stats = await orchestrator.qdrant_client.client.get_collection(
                collection_name=orchestrator.qdrant_client.collection_name
            )
            
            return {
                "success": True,
                "vector_store_status": "healthy",
                "data": {
                    "collection_name": orchestrator.qdrant_client.collection_name,
                    "vector_size": orchestrator.qdrant_client.vector_size,
                    "total_points": collection_info.points_count,
                    "segments_count": collection_info.segments_count,
                    "status": collection_info.status,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting vector store status: {e}")
            return {
                "success": False,
                "vector_store_status": "unhealthy",
                "error": str(e),
                "data": {
                    "collection_name": orchestrator.qdrant_client.collection_name,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
    except Exception as e:
        logger.error("Vector store status check error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store-files", response_model=Dict[str, Any])
async def store_files_for_rag(request: Dict[str, Any]):
    """Store files in the vector database for persistent RAG functionality."""
    try:
        logger.info(f"Storing files for RAG with {len(request.get('files', []))} files")
        
        # Get the global orchestrator instance
        from app import get_global_orchestrator
        orchestrator = get_global_orchestrator()
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Process files and validate content
        files = request.get('files', [])
        repository_id = request.get('repository_id', 'default')
        
        # Validate file content
        validated_files = []
        content_issues = []
        
        for file_data in files:
            file_path = file_data.get('path', '')
            file_content = file_data.get('content', '')
            
            # Check if content is placeholder or empty
            if not file_content or file_content == "Imported file content will be loaded...":
                content_issues.append(f"File {file_path}: Missing or placeholder content")
                continue
            
            # Check content length (basic validation)
            if len(file_content) < 10:  # Very short content might be incomplete
                content_issues.append(f"File {file_path}: Content too short ({len(file_content)} chars)")
            
            # Enhanced file metadata
            validated_files.append({
                'path': file_path,
                'name': file_data.get('name', file_path.split('/')[-1]),
                'content': file_content,
                'url': file_data.get('url', ''),
                'raw_url': file_data.get('raw_url', ''),
                'branch': file_data.get('branch', 'main'),
                'size': len(file_content),
                'repository_id': file_data.get('repository_id', repository_id),
                'owner': file_data.get('owner', ''),
                'repo': file_data.get('repo', ''),
                'last_modified': file_data.get('last_modified', ''),
                'is_public': file_data.get('is_public', True),
                'language': file_data.get('language', 'text'),
                'file_type': file_data.get('file_type', 'text'),
                'sha': file_data.get('sha', ''),
                'error': file_data.get('error', False)
            })
        
        # Log content validation results
        if content_issues:
            logger.warning(f"File content issues detected: {content_issues}")
        
        if not validated_files:
            return {
                "success": False,
                "error": "No valid file content provided. Please ensure files are properly loaded with complete content.",
                "content_issues": content_issues,
                "data": {
                    "files_processed": 0,
                    "files_stored": 0,
                    "content_validation_failed": True
                }
            }
        
        # Process and store files in vector database
        logger.info("Processing files for vector storage...")
        processed_files = []
        storage_errors = []
        total_chunks = 0
        
        for file_data in validated_files:
            try:
                logger.info(f"Processing file for vector storage: {file_data['path']}")
                
                # Create document chunks from file content
                file_processor = get_file_processor()
                
                # Process the file content
                processed_content = await file_processor.process_file_content(
                    content=file_data['content'],
                    filename=file_data['path'],
                    file_type=file_data['file_type']
                )
                
                # Create document chunks with proper metadata
                chunks = []
                for i, element in enumerate(processed_content.get("elements", [])):
                    if element.get("text", "").strip():
                        chunk_metadata = ChunkMetadata(
                            chunk_id=str(uuid.uuid4()),  # Generate proper UUID for Qdrant
                            file_id=f"{repository_id}_{file_data['path']}",
                            chunk_index=i,
                            start_line=element.get("start_line", 0),
                            end_line=element.get("end_line", 0),
                            start_char=element.get("start_char", 0),
                            end_char=element.get("end_char", len(element.get("text", ""))),
                            chunk_type="text",
                            language=file_data['language'],
                            complexity_score=0.0,
                            filename=file_data['path'],
                            file_size=file_data['size'],
                            file_type=file_data['file_type']
                        )
                        
                        chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),  # Generate proper UUID for Qdrant
                            file_id=f"{repository_id}_{file_data['path']}",
                            content=element["text"],
                            metadata=chunk_metadata,
                            created_at=datetime.now().isoformat()
                        )
                        chunks.append(chunk)
                
                # Add chunks to vector store
                if chunks:
                    success = await orchestrator.qdrant_client.upsert_chunks_with_embeddings(
                        chunks, 
                        generate_embeddings=True,
                        orchestrator=orchestrator
                    )
                    if success:
                        processed_files.append({
                            "path": file_data['path'],
                            "chunks_added": len(chunks),
                            "size": file_data['size']
                        })
                        total_chunks += len(chunks)
                        logger.info(f"Successfully stored {file_data['path']} - {len(chunks)} chunks added to vector store")
                    else:
                        storage_errors.append(f"Failed to add chunks for {file_data['path']}")
                else:
                    storage_errors.append(f"No content extracted from {file_data['path']}")
                    
            except Exception as e:
                error_msg = f"Error processing {file_data['path']}: {str(e)}"
                storage_errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            "success": len(processed_files) > 0,
            "message": f"Successfully stored {len(processed_files)} files with {total_chunks} chunks",
            "data": {
                "repository_id": repository_id,
                "files_processed": len(validated_files),
                "files_stored": len(processed_files),
                "files_failed": len(storage_errors),
                "total_chunks_added": total_chunks,
                "processed_files": processed_files,
                "storage_errors": storage_errors if storage_errors else None,
                "content_issues": content_issues if content_issues else None,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Store files for RAG error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-repo", response_model=ProcessRepoResponse)
async def process_repo(request: ProcessRepoRequest):
    """Process repository files and add them to the knowledge base."""
    try:
        logger.info(f"Processing repository: {request.repository}")
        logger.info(f"Files to process: {len(request.files)}")
        
        # Get the global orchestrator instance
        from app import get_global_orchestrator
        orchestrator = get_global_orchestrator()
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Process each file
        processed_files = []
        errors = []
        
        for file_data in request.files:
            try:
                logger.info(f"Processing file: {file_data.path}")
                
                # Create document chunks from file content
                file_processor = get_file_processor()
                
                # Process the file content
                processed_content = await file_processor.process_file_content(
                    content=file_data.content,
                    filename=file_data.path,
                    file_type="text"
                )
                
                # Create document chunks
                chunks = []
                for i, element in enumerate(processed_content.get("elements", [])):
                    if element.get("text", "").strip():
                        chunk_metadata = ChunkMetadata(
                            chunk_id=str(uuid.uuid4()),  # Generate proper UUID for Qdrant
                            file_id=f"{request.repository_id}_{file_data.path}",
                            chunk_index=i,
                            start_line=element.get("start_line", 0),
                            end_line=element.get("end_line", 0),
                            start_char=element.get("start_char", 0),
                            end_char=element.get("end_char", len(element.get("text", ""))),
                            chunk_type="text",
                            language="markdown" if file_data.path.endswith('.md') else "text",
                            complexity_score=0.0
                        )
                        
                        chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),  # Generate proper UUID for Qdrant
                            file_id=f"{request.repository_id}_{file_data.path}",
                            content=element["text"],
                            metadata=chunk_metadata,
                            created_at=request.timestamp
                        )
                        chunks.append(chunk)
                
                # Add chunks to vector store
                if chunks:
                    success = await orchestrator.qdrant_client.upsert_chunks_with_embeddings(
                        chunks, 
                        generate_embeddings=True,
                        orchestrator=orchestrator
                    )
                    if success:
                        processed_files.append({
                            "path": file_data.path,
                            "chunks_added": len(chunks),
                            "size": file_data.size
                        })
                        logger.info(f"Successfully processed {file_data.path} - {len(chunks)} chunks added")
                    else:
                        errors.append(f"Failed to add chunks for {file_data.path}")
                else:
                    errors.append(f"No content extracted from {file_data.path}")
                    
            except Exception as e:
                error_msg = f"Error processing {file_data.path}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return ProcessRepoResponse(
            success=len(processed_files) > 0,
            message=f"Processed {len(processed_files)} files successfully",
            data={
                "repository": request.repository,
                "branch": request.branch,
                "files_processed": len(processed_files),
                "files_failed": len(errors),
                "total_chunks_added": sum(f["chunks_added"] for f in processed_files),
                "processed_files": processed_files,
                "errors": errors if errors else None,
                "timestamp": request.timestamp
            }
        )
        
    except Exception as e:
        logger.error("Process repo error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=ImportResponse)
async def import_files(request: ImportRequest):
    """Import files into the knowledge base."""
    try:
        logger.info(f"Importing files for repository: {request.repository_id}")
        logger.info(f"Files to import: {len(request.files)}")
        
        # Get the global orchestrator instance
        from app import get_global_orchestrator
        orchestrator = get_global_orchestrator()
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Process each file (same logic as process-repo)
        processed_files = []
        errors = []
        
        for file_data in request.files:
            try:
                logger.info(f"Importing file: {file_data.path}")
                
                # Create document chunks from file content
                file_processor = get_file_processor()
                
                # Process the file content
                processed_content = await file_processor.process_file_content(
                    content=file_data.content,
                    filename=file_data.path,
                    file_type="text"
                )
                
                # Create document chunks
                chunks = []
                for i, element in enumerate(processed_content.get("elements", [])):
                    if element.get("text", "").strip():
                        chunk_metadata = ChunkMetadata(
                            chunk_id=str(uuid.uuid4()),  # Generate proper UUID for Qdrant
                            file_id=f"{request.repository_id}_{file_data.path}",
                            chunk_index=i,
                            start_line=element.get("start_line", 0),
                            end_line=element.get("end_line", 0),
                            start_char=element.get("start_char", 0),
                            end_char=element.get("end_char", len(element.get("text", ""))),
                            chunk_type="text",
                            language="markdown" if file_data.path.endswith('.md') else "text",
                            complexity_score=0.0
                        )
                        
                        chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),  # Generate proper UUID for Qdrant
                            file_id=f"{request.repository_id}_{file_data.path}",
                            content=element["text"],
                            metadata=chunk_metadata,
                            created_at=request.timestamp
                        )
                        chunks.append(chunk)
                
                # Add chunks to vector store
                if chunks:
                    success = await orchestrator.qdrant_client.upsert_chunks_with_embeddings(
                        chunks, 
                        generate_embeddings=True,
                        orchestrator=orchestrator
                    )
                    if success:
                        processed_files.append({
                            "path": file_data.path,
                            "chunks_added": len(chunks),
                            "size": file_data.size
                        })
                        logger.info(f"Successfully imported {file_data.path} - {len(chunks)} chunks added")
                    else:
                        errors.append(f"Failed to add chunks for {file_data.path}")
                else:
                    errors.append(f"No content extracted from {file_data.path}")
                    
            except Exception as e:
                error_msg = f"Error importing {file_data.path}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return ImportResponse(
            success=len(processed_files) > 0,
            message=f"Imported {len(processed_files)} files successfully",
            data={
                "repository_id": request.repository_id,
                "branch": request.branch,
                "source_type": request.source_type,
                "files_imported": len(processed_files),
                "files_failed": len(errors),
                "total_chunks_added": sum(f["chunks_added"] for f in processed_files),
                "processed_files": processed_files,
                "errors": errors if errors else None,
                "timestamp": request.timestamp
            }
        )
        
    except Exception as e:
        logger.error(f"Error in import: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to import files: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search documents in the knowledge base."""
    try:
        logger.info(f"Searching for: {request.query}")
        
        # Get the global orchestrator instance
        from app import get_global_orchestrator
        orchestrator = get_global_orchestrator()
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Perform search using the vector retriever
        search_results = await orchestrator.vector_retriever.search(
            query=request.query,
            limit=request.limit,
            filters={"repository_id": request.repository_id} if request.repository_id else None
        )
        
        # Format results
        results = []
        for result in search_results:
            results.append({
                "chunk_id": result.chunk_id,
                "file_id": result.file_id,
                "content": result.content,
                "score": result.score,
                "metadata": result.metadata.dict() if result.metadata else {}
            })
        
        return SearchResponse(
            success=True,
            results=results,
            total=len(results)
        )
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search documents: {str(e)}")
