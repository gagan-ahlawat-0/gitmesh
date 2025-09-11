"""
TARS v1 Unified Wrapper
======================

A comprehensive wrapper that handles:
- 6 types of inputs (text, file, url, repo, image, audio)
- Multiple AI models
- Session management with context persistence
- Enhanced chunking and indexing
- Memory and retrieval
"""

import uuid
import json
import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

from ai.session import Session
from ai.llm.llm import LLM
from ai.memory.memory import Memory
from ai.knowledge.knowledge import Knowledge

from .indexing.core import CodebaseIndexer
from .indexing.chunking import EnhancedChunker, create_adaptive_chunker


@dataclass
class TARSInput:
    """Structured input for TARS processing."""
    input_type: str  # text, file, url, repo, image, audio
    content: str
    metadata: Dict[str, Any] = None
    file_path: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TARSResponse:
    """Structured response from TARS."""
    response: str
    session_id: str
    model_used: str
    input_type: str
    chunks_processed: int
    processing_time: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TARSSession:
    """TARS session with context management."""
    
    def __init__(self, session_id: str, model_name: str):
        self.session_id = session_id
        self.model_name = model_name
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.message_count = 0
        self.context_chunks = []
        self.memory_keys = []
        
    def add_context(self, chunks: List[Dict[str, Any]], memory_keys: List[str]):
        """Add context chunks and memory keys to session."""
        self.context_chunks.extend(chunks)
        self.memory_keys.extend(memory_keys)
        self.last_updated = datetime.now()
        self.message_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for persistence."""
        return {
            'session_id': self.session_id,
            'model_name': self.model_name,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'message_count': self.message_count,
            'context_chunks': self.context_chunks,
            'memory_keys': self.memory_keys
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TARSSession':
        """Create session from dictionary."""
        session = cls(data['session_id'], data['model_name'])
        session.created_at = datetime.fromisoformat(data['created_at'])
        session.last_updated = datetime.fromisoformat(data['last_updated'])
        session.message_count = data['message_count']
        session.context_chunks = data['context_chunks']
        session.memory_keys = data['memory_keys']
        return session


class TARSWrapper:
    """
    Unified TARS wrapper handling all input types and model interactions.
    
    Supported Input Types:
    - text: Plain text input
    - file: File path or file content
    - url: Web URL content
    - repo: GitHub repository
    - image: Image file for vision models
    - audio: Audio file for transcription
    """
    
    def __init__(
        self,
        default_model: str = "openai/gpt-4o-mini",
        memory_enabled: bool = True,
        knowledge_enabled: bool = True,
        session_storage_path: str = "./tars_sessions"
    ):
        """Initialize TARS wrapper with configuration."""
        self.default_model = default_model
        self.memory_enabled = memory_enabled
        self.knowledge_enabled = knowledge_enabled
        self.session_storage_path = Path(session_storage_path)
        self.session_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize core components
        self.sessions: Dict[str, TARSSession] = {}
        self.indexer = CodebaseIndexer() if knowledge_enabled else None
        
        # Initialize memory with default config
        if memory_enabled:
            memory_config = {
                "provider": "rag",
                "use_embedding": True,
                "short_db": str(self.session_storage_path / "short_term.db"),
                "long_db": str(self.session_storage_path / "long_term.db"),
                "rag_db_path": str(self.session_storage_path / "rag_db"),
            }
            self.memory = Memory(memory_config)
        else:
            self.memory = None
            
        self.knowledge = Knowledge() if knowledge_enabled else None
        
        # Load existing sessions
        self._load_sessions()
        
        print(f"🤖 TARS v1 Wrapper initialized")
        print(f"   Default model: {default_model}")
        print(f"   Memory enabled: {memory_enabled}")
        print(f"   Knowledge enabled: {knowledge_enabled}")
    
    def _load_sessions(self):
        """Load existing sessions from storage."""
        try:
            sessions_file = self.session_storage_path / "sessions.json"
            if sessions_file.exists():
                with open(sessions_file, 'r') as f:
                    sessions_data = json.load(f)
                
                for session_data in sessions_data:
                    session = TARSSession.from_dict(session_data)
                    self.sessions[session.session_id] = session
                
                print(f"📂 Loaded {len(self.sessions)} existing sessions")
        except Exception as e:
            print(f"⚠️  Failed to load sessions: {e}")
    
    def _save_sessions(self):
        """Save current sessions to storage."""
        try:
            sessions_file = self.session_storage_path / "sessions.json"
            sessions_data = [session.to_dict() for session in self.sessions.values()]
            
            with open(sessions_file, 'w') as f:
                json.dump(sessions_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️  Failed to save sessions: {e}")
    
    def create_session(self, model_name: Optional[str] = None) -> str:
        """Create a new TARS session."""
        session_id = str(uuid.uuid4())
        model_name = model_name or self.default_model
        
        session = TARSSession(session_id, model_name)
        self.sessions[session_id] = session
        
        self._save_sessions()
        print(f"🆕 Created new session: {session_id[:8]}... with model {model_name}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[TARSSession]:
        """Get existing session by ID."""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        return [
            {
                'session_id': session.session_id,
                'model_name': session.model_name,
                'created_at': session.created_at.isoformat(),
                'message_count': session.message_count
            }
            for session in self.sessions.values()
        ]
    
    def _process_input(self, tars_input: TARSInput) -> Dict[str, Any]:
        """Process input based on type and extract content."""
        start_time = time.time()
        
        if tars_input.input_type == "text":
            return self._process_text(tars_input.content)
        
        elif tars_input.input_type == "file":
            return self._process_file(tars_input.content, tars_input.file_path)
        
        elif tars_input.input_type == "url":
            return self._process_url(tars_input.content)
        
        elif tars_input.input_type == "repo":
            return self._process_repo(tars_input.content)
        
        elif tars_input.input_type == "image":
            return self._process_image(tars_input.content, tars_input.file_path)
        
        elif tars_input.input_type == "audio":
            return self._process_audio(tars_input.content, tars_input.file_path)
        
        else:
            raise ValueError(f"Unsupported input type: {tars_input.input_type}")
    
    def _process_text(self, text: str) -> Dict[str, Any]:
        """Process plain text input."""
        if not self.knowledge_enabled:
            return {'content': text, 'chunks': [], 'type': 'text'}
        
        # Use adaptive chunking for text
        chunker = create_adaptive_chunker('text', len(text))
        result = chunker.chunk(text, file_path="user_input.txt")
        
        return {
            'content': text,
            'chunks': result.chunks,
            'type': 'text',
            'quality_score': result.quality_score
        }
    
    def _process_file(self, content: str, file_path: Optional[str]) -> Dict[str, Any]:
        """Process file content."""
        if not self.knowledge_enabled:
            return {'content': content, 'chunks': [], 'type': 'file'}
        
        # Determine file type and use appropriate chunking
        if file_path:
            path_obj = Path(file_path)
            extension = path_obj.suffix.lower()
            
            # Language-specific chunking
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'cpp',
                '.md': 'markdown',
                '.txt': 'text'
            }
            
            language = language_map.get(extension, 'text')
            chunker = create_adaptive_chunker(language, len(content))
            result = chunker.chunk(content, file_path=file_path)
        else:
            # Default text chunking
            chunker = EnhancedChunker(chunker_type='sentence', chunk_size=512)
            result = chunker.chunk(content, file_path="uploaded_file.txt")
        
        return {
            'content': content,
            'chunks': result.chunks,
            'type': 'file',
            'file_path': file_path,
            'quality_score': result.quality_score
        }
    
    def _process_url(self, url: str) -> Dict[str, Any]:
        """Process URL content."""
        try:
            # Use spider tools to extract content
            from ai.tools.spider_tools import SpiderTools
            
            spider = SpiderTools()
            content = spider.scrape_url(url)
            
            if self.knowledge_enabled:
                chunker = create_adaptive_chunker('text', len(content))
                result = chunker.chunk(content, file_path=f"web_{hash(url)}.txt")
                
                return {
                    'content': content,
                    'chunks': result.chunks,
                    'type': 'url',
                    'url': url,
                    'quality_score': result.quality_score
                }
            else:
                return {'content': content, 'chunks': [], 'type': 'url', 'url': url}
                
        except Exception as e:
            print(f"⚠️  Failed to process URL {url}: {e}")
            return {'content': f"Failed to scrape URL: {url}", 'chunks': [], 'type': 'url', 'url': url}
    
    def _process_repo(self, repo_url: str) -> Dict[str, Any]:
        """Process GitHub repository."""
        try:
            if self.indexer:
                # Use TARS indexer for repository processing
                repo_data = self.indexer.index_repository(repo_url)
                
                return {
                    'content': f"Repository: {repo_url}",
                    'chunks': repo_data.get('chunks', []),
                    'type': 'repo',
                    'repo_url': repo_url,
                    'files_processed': repo_data.get('files_processed', 0),
                    'quality_score': repo_data.get('quality_score', 0.0)
                }
            else:
                return {
                    'content': f"Repository indexing disabled: {repo_url}",
                    'chunks': [],
                    'type': 'repo',
                    'repo_url': repo_url
                }
                
        except Exception as e:
            print(f"⚠️  Failed to process repository {repo_url}: {e}")
            return {
                'content': f"Failed to process repository: {repo_url}",
                'chunks': [],
                'type': 'repo',
                'repo_url': repo_url
            }
    
    def _process_image(self, content: str, file_path: Optional[str]) -> Dict[str, Any]:
        """Process image content for vision models."""
        return {
            'content': content,
            'chunks': [],  # Images don't need chunking
            'type': 'image',
            'file_path': file_path,
            'vision_ready': True
        }
    
    def _process_audio(self, content: str, file_path: Optional[str]) -> Dict[str, Any]:
        """Process audio content."""
        try:
            # Audio transcription not yet available in ai framework
            # For now, return placeholder content
            print(f"⚠️  Audio transcription not yet implemented. Using placeholder for: {file_path or 'audio content'}")
            
            placeholder_text = f"Audio content from: {file_path or 'audio input'} - transcription not yet available"
            
            if self.knowledge_enabled:
                chunker = create_adaptive_chunker('text', len(placeholder_text))
                result = chunker.chunk(placeholder_text, file_path="audio_placeholder.txt")
                
                return {
                    'content': placeholder_text,
                    'chunks': result.chunks,
                    'type': 'audio',
                    'file_path': file_path,
                    'transcription': placeholder_text,
                    'quality_score': result.quality_score
                }
            else:
                return {
                    'content': placeholder_text,
                    'chunks': [],
                    'type': 'audio',
                    'file_path': file_path,
                    'transcription': placeholder_text
                }
                
        except Exception as e:
            print(f"⚠️  Failed to process audio: {e}")
            return {
                'content': "Failed to transcribe audio",
                'chunks': [],
                'type': 'audio',
                'file_path': file_path
            }
    
    def _store_context(self, session: TARSSession, processed_data: Dict[str, Any]) -> List[str]:
        """Store context in memory and return memory keys."""
        memory_keys = []
        
        if self.memory_enabled and processed_data.get('chunks'):
            try:
                for chunk in processed_data['chunks']:
                    # Create memory entry
                    memory_entry = {
                        'content': chunk['content'],
                        'metadata': {
                            'session_id': session.session_id,
                            'input_type': processed_data['type'],
                            'chunk_id': chunk.get('metadata', {}).chunk_id,
                            'timestamp': datetime.now().isoformat(),
                            **chunk.get('metadata', {}).__dict__
                        }
                    }
                    
                    # Store in memory using store_short_term
                    memory_key = self.memory.store_short_term(
                        text=memory_entry['content'],
                        metadata=memory_entry['metadata']
                    )
                    memory_keys.append(memory_key)
                
                print(f"💾 Stored {len(memory_keys)} chunks in memory for session {session.session_id[:8]}...")
            
            except Exception as e:
                print(f"⚠️  Failed to store context in memory: {e}")
        
        return memory_keys
    
    def _retrieve_context(self, session: TARSSession, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant context for the query."""
        if not self.memory_enabled:
            return []
        
        try:
            # Search memory for relevant context
            results = self.memory.search(
                query=query,
                limit=limit,
                filters={'session_id': session.session_id}
            )
            
            context_chunks = []
            for result in results:
                context_chunks.append({
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'relevance_score': result.get('score', 0.0)
                })
            
            print(f"🔍 Retrieved {len(context_chunks)} relevant chunks for query")
            return context_chunks
            
        except Exception as e:
            print(f"⚠️  Failed to retrieve context: {e}")
            return []
    
    def chat(
        self,
        message: str,
        input_type: str = "text",
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        file_path: Optional[str] = None,
        **kwargs
    ) -> TARSResponse:
        """
        Main chat interface for TARS.
        
        Args:
            message: Input message/content
            input_type: Type of input (text, file, url, repo, image, audio)
            session_id: Optional session ID (creates new if None)
            model: Optional model override
            file_path: Optional file path for file/image/audio inputs
            **kwargs: Additional parameters
        
        Returns:
            TARSResponse with the AI response and metadata
        """
        start_time = time.time()
        
        # Create or get session
        if session_id is None:
            session_id = self.create_session(model)
        
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        
        # Use session model or override
        model_name = model or session.model_name
        
        try:
            # Process input
            tars_input = TARSInput(
                input_type=input_type,
                content=message,
                file_path=file_path,
                metadata=kwargs
            )
            
            processed_data = self._process_input(tars_input)
            print(f"📊 Processed {input_type} input: {len(processed_data.get('chunks', []))} chunks")
            
            # Store context in memory
            memory_keys = self._store_context(session, processed_data)
            
            # Retrieve relevant context
            relevant_context = self._retrieve_context(session, message)
            
            # Build context for LLM
            context_parts = []
            if relevant_context:
                context_parts.append("Relevant context from previous conversations:")
                for ctx in relevant_context:
                    context_parts.append(f"- {ctx['content'][:200]}...")
            
            if processed_data.get('chunks'):
                context_parts.append("\nCurrent input analysis:")
                for chunk in processed_data['chunks'][:3]:  # Limit to first 3 chunks
                    context_parts.append(f"- {chunk['content'][:200]}...")
            
            # Create enhanced prompt
            enhanced_prompt = f"""
Context: {' '.join(context_parts) if context_parts else 'No previous context'}

User Query: {message}

Please provide a comprehensive response based on the available context and your knowledge.
"""
            
            # Initialize LLM and get response
            llm = LLM(model=model_name)
            ai_response = llm.response(
                prompt=enhanced_prompt,
                system_prompt=None,
                temperature=0.7,
                stream=False,
                verbose=False
            )
            
            # Update session
            session.add_context(processed_data.get('chunks', []), memory_keys)
            self._save_sessions()
            
            # Create response
            processing_time = time.time() - start_time
            response = TARSResponse(
                response=ai_response,
                session_id=session_id,
                model_used=model_name,
                input_type=input_type,
                chunks_processed=len(processed_data.get('chunks', [])),
                processing_time=processing_time,
                metadata={
                    'quality_score': processed_data.get('quality_score', 0.0),
                    'context_retrieved': len(relevant_context),
                    'memory_keys_stored': len(memory_keys)
                }
            )
            
            print(f"✅ Generated response in {processing_time:.2f}s using {model_name}")
            return response
            
        except Exception as e:
            print(f"❌ Error in chat: {e}")
            error_response = TARSResponse(
                response=f"Sorry, I encountered an error: {e}",
                session_id=session_id,
                model_used=model_name,
                input_type=input_type,
                chunks_processed=0,
                processing_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
            return error_response
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its associated data."""
        if session_id in self.sessions:
            # Delete from memory if enabled
            if self.memory_enabled:
                try:
                    # Delete memory entries for this session
                    # Note: Implementation depends on memory backend
                    pass
                except Exception as e:
                    print(f"⚠️  Failed to delete session memory: {e}")
            
            # Remove session
            del self.sessions[session_id]
            self._save_sessions()
            print(f"🗑️  Deleted session: {session_id[:8]}...")
            return True
        
        return False
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            'session_id': session_id,
            'model_name': session.model_name,
            'created_at': session.created_at.isoformat(),
            'last_updated': session.last_updated.isoformat(),
            'message_count': session.message_count,
            'context_chunks': len(session.context_chunks),
            'memory_keys': len(session.memory_keys)
        }


# Convenience functions for easy usage
def create_tars(
    model: str = "openai/gpt-4o-mini",
    memory: bool = True,
    knowledge: bool = True
) -> TARSWrapper:
    """Create a TARS wrapper with specified configuration."""
    return TARSWrapper(
        default_model=model,
        memory_enabled=memory,
        knowledge_enabled=knowledge
    )


def quick_chat(
    message: str,
    input_type: str = "text",
    model: str = "openai/gpt-4o-mini"
) -> str:
    """Quick chat without session persistence."""
    tars = create_tars(model=model)
    response = tars.chat(message, input_type=input_type)
    return response.response
