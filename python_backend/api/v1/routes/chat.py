"""
Chat API routes for the RAG system.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog

from core.orchestrator import RAGOrchestrator
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


class ChatRequest(BaseModel):
    query: str
    agent_type: str = "code_chat"


class FileChatRequest(BaseModel):
    message: str
    files: List[FileData]
    repository_id: str
    timestamp: str


class FileChatResponse(BaseModel):
    success: bool
    response: str
    referenced_files: List[str] = []
    code_snippets: List[Dict[str, Any]] = []
    data: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    response: str
    metadata: Dict[str, Any] = {}


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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Basic chat endpoint."""
    try:
        # Get the global orchestrator instance
        from app import orchestrator
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Create a simple task for the agent
        from agents.base.base_agent import AgentTask
        
        task = AgentTask(
            task_type=request.agent_type,
            input_data={"query": request.query},
            parameters={"temperature": 0.7, "max_tokens": 1000}
        )
        
        # Get the appropriate agent
        agent = orchestrator.agent_registry.get_agent_by_type(request.agent_type)
        if not agent:
            raise HTTPException(status_code=400, detail=f"Agent type '{request.agent_type}' not found")
        
        # Execute the task
        result = await agent.execute(task)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {result.error_message}")
        
        return ChatResponse(
            response=result.output_data.get("response", "No response generated"),
            metadata={
                "agent_used": agent.name,
                "processing_time": result.metadata.get("processing_time", 0),
                "tokens_used": result.metadata.get("tokens_used", 0)
            }
        )
        
    except Exception as e:
        logger.error("Chat endpoint error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-with-files", response_model=FileChatResponse)
async def chat_with_files(request: FileChatRequest):
    """Enhanced chat with AI about specific files using RAG pipeline."""
    try:
        logger.info(f"RAG chat request with {len(request.files)} files")
        logger.info(f"Message: {request.message}")
        
        # Get the global orchestrator instance
        from app import orchestrator
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Phase 5.1: Context Preparation - Process and chunk files
        file_contexts = []
        referenced_files = []
        code_snippets = []
        file_metadata = []
        
        for file_data in request.files:
            try:
                logger.info(f"Processing file for RAG: {file_data.path}")
                
                # Add file to referenced files
                referenced_files.append(file_data.path)
                
                # Create file metadata for RAG processing
                from models.api.file_models import FileMetadata
                file_meta = FileMetadata(
                    filename=file_data.path,
                    file_id=f"{request.repository_id}_{file_data.path}",
                    content_type="text/plain",
                    size=len(file_data.content.encode('utf-8')),
                    language=detect_language_from_path(file_data.path),
                    file_type=detect_file_type_from_path(file_data.path)
                )
                file_metadata.append(file_meta)
                
                # Process file through RAG pipeline
                file_content_bytes = file_data.content.encode('utf-8')
                processing_result = await orchestrator.process_file(file_meta, file_content_bytes)
                
                if processing_result.status == "completed":
                    logger.info(f"Successfully processed {file_data.path} - {len(processing_result.chunks)} chunks")
                    
                    # Extract code snippets from chunks
                    for chunk in processing_result.chunks:
                        if chunk.metadata.chunk_type == "code":
                            code_snippets.append({
                                "language": chunk.metadata.language or "text",
                                "code": chunk.content,
                                "filePath": file_data.path,
                                "startLine": chunk.metadata.start_line,
                                "endLine": chunk.metadata.end_line
                            })
                else:
                    logger.warning(f"File processing failed for {file_data.path}: {processing_result.error}")
                
            except Exception as e:
                logger.error(f"Error processing file {file_data.path}: {str(e)}")
                continue
        
        # Phase 5.2: RAG Query Processing - Retrieve relevant context
        try:
            # Retrieve relevant chunks from vector database
            context_chunks = await orchestrator.vector_retriever.retrieve_relevant_chunks(
                query=request.message,
                limit=10,  # Increased for better coverage
                score_threshold=0.7,
                filters={
                    "file_id": [f"{request.repository_id}_{f.path}" for f in request.files]
                }
            )
            
            logger.info(f"Retrieved {len(context_chunks)} relevant chunks for query")
            
            # Create enhanced context from retrieved chunks
            enhanced_context = ""
            if context_chunks:
                enhanced_context = "\n".join([
                    f"Context from {chunk.get('metadata', {}).get('file_id', 'unknown')}:\n{chunk.get('content', '')}\n"
                    for chunk in context_chunks
                ])
            
            # Combine with direct file context for comprehensive coverage
            direct_context = "\n".join([
                f"File: {f.path} (Branch: {f.branch})\nContent:\n{f.content}\n" + "-" * 50
                for f in request.files
            ])
            
            combined_context = f"{enhanced_context}\n\nDirect File Context:\n{direct_context}"
            
        except Exception as e:
            logger.error(f"RAG retrieval failed, falling back to direct context: {str(e)}")
            # Fallback to direct file context
            combined_context = "\n".join([
                f"File: {f.path} (Branch: {f.branch})\nContent:\n{f.content}\n" + "-" * 50
                for f in request.files
            ])
        
        # Phase 5.3: Response Enhancement - Generate enhanced response
        enhanced_query = f"""Context from RAG-enhanced file analysis:

{combined_context}

User Question: {request.message}

Please provide a detailed response based on the code and files provided above. 
- Reference specific file names and line numbers where applicable
- Include relevant code snippets with proper citations
- Provide confidence scores for your responses
- If context is insufficient, clearly state what additional information would be helpful"""

        # Create enhanced task for the code chat agent
        from agents.base.base_agent import AgentTask
        
        task = AgentTask(
            task_type="code_chat",
            input_data={
                "query": enhanced_query,
                "context": combined_context,
                "files": [f.path for f in request.files],
                "context_chunks": context_chunks if 'context_chunks' in locals() else [],
                "repository_id": request.repository_id
            },
            parameters={
                "temperature": 0.7,
                "max_tokens": 2500,
                "include_code_snippets": True,
                "include_citations": True,
                "include_confidence": True
            }
        )
        
        # Get the code chat agent
        agent = orchestrator.agent_registry.get_agent_by_type("code_chat")
        if not agent:
            raise HTTPException(status_code=400, detail="Code chat agent not found")
        
        # Execute the task
        result = await agent.execute(task)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {result.error_message}")
        
        # Extract response and enhance with metadata
        response = result.output_data.get("response", "No response generated")
        
        # Extract additional code snippets from response
        import re
        code_block_pattern = r"```(\w+)?\n(.*?)```"
        code_matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        for lang, code in code_matches:
            if code.strip():
                code_snippets.append({
                    "language": lang or "text",
                    "code": code.strip(),
                    "filePath": None,  # From response
                    "source": "response"
                })
        
        # Calculate confidence score based on context coverage
        confidence_score = calculate_confidence_score(
            len(context_chunks) if 'context_chunks' in locals() else 0,
            len(request.files),
            len(response)
        )
        
        return FileChatResponse(
            success=True,
            response=response,
            referenced_files=referenced_files,
            code_snippets=code_snippets,
            data={
                "agent_used": agent.name,
                "processing_time": result.metadata.get("processing_time", 0),
                "tokens_used": result.metadata.get("tokens_used", 0),
                "files_processed": len(request.files),
                "context_length": len(combined_context),
                "chunks_retrieved": len(context_chunks) if 'context_chunks' in locals() else 0,
                "confidence_score": confidence_score,
                "rag_enabled": True,
                "context_coverage": len(context_chunks) / max(len(request.files), 1) if 'context_chunks' in locals() else 0
            }
        )
        
    except Exception as e:
        logger.error("Enhanced RAG chat error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def detect_language_from_path(file_path: str) -> str:
    """Detect programming language from file extension."""
    extension = file_path.split('.')[-1].lower()
    language_map = {
        'py': 'python', 'js': 'javascript', 'ts': 'typescript',
        'jsx': 'javascript', 'tsx': 'typescript', 'java': 'java',
        'cpp': 'cpp', 'c': 'c', 'cs': 'csharp', 'php': 'php',
        'rb': 'ruby', 'go': 'go', 'rs': 'rust', 'swift': 'swift',
        'kt': 'kotlin', 'md': 'markdown', 'json': 'json',
        'yaml': 'yaml', 'yml': 'yaml', 'xml': 'xml', 'html': 'html',
        'css': 'css', 'scss': 'scss', 'sql': 'sql'
    }
    return language_map.get(extension, 'text')


def detect_file_type_from_path(file_path: str) -> str:
    """Detect file type from path."""
    extension = file_path.split('.')[-1].lower()
    if extension in ['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'cs', 'php', 'rb', 'go', 'rs', 'swift', 'kt']:
        return 'code'
    elif extension in ['md', 'txt', 'rst']:
        return 'documentation'
    elif extension in ['json', 'yaml', 'yml', 'xml']:
        return 'configuration'
    elif extension in ['html', 'css', 'scss']:
        return 'frontend'
    else:
        return 'text'


def calculate_confidence_score(chunks_retrieved: int, files_processed: int, response_length: int) -> float:
    """Calculate confidence score based on context coverage and response quality."""
    # Base confidence on context coverage
    context_coverage = min(chunks_retrieved / max(files_processed, 1), 1.0)
    
    # Adjust based on response quality (length indicates detail)
    response_quality = min(response_length / 1000, 1.0)  # Normalize to 0-1
    
    # Weighted average
    confidence = (context_coverage * 0.7) + (response_quality * 0.3)
    
    return round(confidence, 2)


@router.post("/process-repo", response_model=ProcessRepoResponse)
async def process_repo(request: ProcessRepoRequest):
    """Process repository files and add them to the knowledge base."""
    try:
        logger.info(f"Processing repository: {request.repository}")
        logger.info(f"Files to process: {len(request.files)}")
        logger.info(f"Request data: {request.dict()}")
        
        # Get the global orchestrator instance
        from app import orchestrator
        
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
                    file_type="text"  # Default to text for now
                )
                
                # Create document chunks
                chunks = []
                for i, element in enumerate(processed_content.get("elements", [])):
                    if element.get("text", "").strip():
                        # Create ChunkMetadata object
                        chunk_metadata = ChunkMetadata(
                            chunk_id=f"{request.repository_id}_{file_data.path}_{i}",
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
                            chunk_id=f"{request.repository_id}_{file_data.path}_{i}",
                            file_id=f"{request.repository_id}_{file_data.path}",
                            content=element["text"],
                            metadata=chunk_metadata,
                            created_at=request.timestamp
                        )
                        chunks.append(chunk)
                
                # Add chunks to vector store
                if chunks:
                    success = await orchestrator.qdrant_client.upsert_chunks(chunks)
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
        
        # Return response
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
        from app import orchestrator
        
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
                            chunk_id=f"{request.repository_id}_{file_data.path}_{i}",
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
                            chunk_id=f"{request.repository_id}_{file_data.path}_{i}",
                            file_id=f"{request.repository_id}_{file_data.path}",
                            content=element["text"],
                            metadata=chunk_metadata,
                            created_at=request.timestamp
                        )
                        chunks.append(chunk)
                
                # Add chunks to vector store
                if chunks:
                    success = await orchestrator.qdrant_client.upsert_chunks(chunks)
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
        from app import orchestrator
        
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
