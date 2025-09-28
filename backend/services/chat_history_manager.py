"""
Chat History Manager for Supabase integration.
Handles chat session and message storage with proper metadata.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncpg
import uuid

from config.settings import get_settings
from models.api.session_models import (
    ChatSession, SessionMessage, SessionContext, FileContext, 
    SessionStatus, SessionStats
)

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ChatMetrics:
    """Chat performance metrics."""
    session_id: str
    message_id: str
    tokens_used: int
    latency_ms: float
    cache_hit: bool
    timestamp: datetime


class ChatHistoryManager:
    """Manages chat history storage and retrieval in Supabase."""
    
    def __init__(self):
        self.database_url = settings.SUPABASE_URL
        self.connection_pool = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the chat history manager with database connection."""
        if self._initialized:
            return
        
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=30
            )
            
            await self._create_chat_tables()
            self._initialized = True
            logger.info("ChatHistoryManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatHistoryManager: {e}")
            raise
    
    async def _create_chat_tables(self):
        """Create chat-related tables in Supabase."""
        async with self.connection_pool.acquire() as conn:
            # Chat sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    repository_url VARCHAR(1000),
                    repository_id VARCHAR(255),
                    branch VARCHAR(255) DEFAULT 'main',
                    status VARCHAR(20) DEFAULT 'active',
                    message_count INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    context_data JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Chat messages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    message_id VARCHAR(255) UNIQUE NOT NULL,
                    session_id VARCHAR(255) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    tokens_used INTEGER DEFAULT 0,
                    latency_ms FLOAT DEFAULT 0,
                    files_referenced JSONB DEFAULT '[]',
                    code_snippets JSONB DEFAULT '[]',
                    metadata JSONB DEFAULT '{}'
                );
            """)
            
            # Chat metrics table for performance tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_metrics (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    message_id VARCHAR(255) NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    latency_ms FLOAT NOT NULL,
                    cache_hit BOOLEAN DEFAULT FALSE,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # File contexts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS file_contexts (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                    file_path TEXT NOT NULL,
                    branch VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    language VARCHAR(100),
                    file_type VARCHAR(100),
                    chunk_count INTEGER DEFAULT 0,
                    token_count INTEGER DEFAULT 0,
                    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Create indexes for better performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id 
                ON chat_sessions(user_id);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_repository 
                ON chat_sessions(repository_id, user_id);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session 
                ON chat_messages(session_id, timestamp);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_metrics_session 
                ON chat_metrics(session_id, timestamp);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_contexts_session 
                ON file_contexts(session_id);
            """)
    
    async def close(self):
        """Close the database connection pool."""
        if self.connection_pool:
            await self.connection_pool.close()
            self._initialized = False
    
    # Session Management Methods
    
    async def create_session(
        self, 
        user_id: str, 
        title: str, 
        repository_url: Optional[str] = None,
        repository_id: Optional[str] = None,
        branch: str = "main"
    ) -> ChatSession:
        """Create a new chat session."""
        if not self._initialized:
            await self.initialize()
        
        session_id = str(uuid.uuid4())
        context = SessionContext(session_id=session_id)
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_sessions 
                (session_id, user_id, title, repository_url, repository_id, branch, context_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7);
            """, 
            session_id, user_id, title, repository_url, repository_id, branch,
            json.dumps(context.dict())
            )
        
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            title=title,
            repository_id=repository_id,
            branch=branch,
            context=context
        )
        
        logger.info(f"Created chat session {session_id} for user {user_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT * FROM chat_sessions WHERE session_id = $1;
            """, session_id)
            
            if not result:
                return None
            
            # Parse context data
            context_data = json.loads(result['context_data']) if result['context_data'] else {}
            context = SessionContext(**context_data)
            
            return ChatSession(
                session_id=result['session_id'],
                user_id=result['user_id'],
                title=result['title'],
                repository_id=result['repository_id'],
                branch=result['branch'],
                status=SessionStatus(result['status']),
                context=context,
                message_count=result['message_count'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                last_activity=result['last_activity']
            )
    
    async def update_session(self, session: ChatSession) -> ChatSession:
        """Update an existing chat session."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                UPDATE chat_sessions 
                SET title = $2, status = $3, message_count = $4, total_tokens = $5,
                    context_data = $6, updated_at = NOW(), last_activity = NOW()
                WHERE session_id = $1;
            """, 
            session.session_id, session.title, session.status.value, 
            session.message_count, session.context.total_tokens,
            json.dumps(session.context.dict())
            )
        
        session.updated_at = datetime.now()
        session.last_activity = datetime.now()
        return session
    
    async def get_user_sessions(
        self, 
        user_id: str, 
        limit: int = 50,
        repository_id: Optional[str] = None
    ) -> List[ChatSession]:
        """Get chat sessions for a user."""
        if not self._initialized:
            await self.initialize()
        
        query = """
            SELECT * FROM chat_sessions 
            WHERE user_id = $1
        """
        params = [user_id]
        
        if repository_id:
            query += " AND repository_id = $2"
            params.append(repository_id)
        
        query += " ORDER BY last_activity DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        async with self.connection_pool.acquire() as conn:
            results = await conn.fetch(query, *params)
            
            sessions = []
            for result in results:
                context_data = json.loads(result['context_data']) if result['context_data'] else {}
                context = SessionContext(**context_data)
                
                session = ChatSession(
                    session_id=result['session_id'],
                    user_id=result['user_id'],
                    title=result['title'],
                    repository_id=result['repository_id'],
                    branch=result['branch'],
                    status=SessionStatus(result['status']),
                    context=context,
                    message_count=result['message_count'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at'],
                    last_activity=result['last_activity']
                )
                sessions.append(session)
            
            return sessions
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session and all related data."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.fetchval("""
                DELETE FROM chat_sessions WHERE session_id = $1 RETURNING id;
            """, session_id)
            
            if result:
                logger.info(f"Deleted chat session {session_id}")
                return True
            return False
    
    # Message Management Methods
    
    async def store_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        tokens_used: int = 0,
        latency_ms: float = 0,
        files_referenced: List[str] = None,
        code_snippets: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> SessionMessage:
        """Store a chat message."""
        if not self._initialized:
            await self.initialize()
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_messages 
                (message_id, session_id, role, content, timestamp, tokens_used, latency_ms,
                 files_referenced, code_snippets, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10);
            """, 
            message_id, session_id, role, content, timestamp, tokens_used, latency_ms,
            json.dumps(files_referenced or []),
            json.dumps(code_snippets or []),
            json.dumps(metadata or {})
            )
            
            # Update session message count and activity
            await conn.execute("""
                UPDATE chat_sessions 
                SET message_count = message_count + 1, 
                    total_tokens = total_tokens + $2,
                    last_activity = NOW(), 
                    updated_at = NOW()
                WHERE session_id = $1;
            """, session_id, tokens_used)
        
        message = SessionMessage(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=timestamp,
            files_referenced=files_referenced or [],
            code_snippets=code_snippets or [],
            metadata=metadata
        )
        
        logger.debug(f"Stored message {message_id} for session {session_id}")
        return message
    
    async def get_chat_history(
        self, 
        session_id: str, 
        limit: int = 50,
        before_timestamp: Optional[datetime] = None
    ) -> List[SessionMessage]:
        """Get chat history for a session."""
        if not self._initialized:
            await self.initialize()
        
        query = """
            SELECT * FROM chat_messages 
            WHERE session_id = $1
        """
        params = [session_id]
        
        if before_timestamp:
            query += " AND timestamp < $2"
            params.append(before_timestamp)
        
        query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        async with self.connection_pool.acquire() as conn:
            results = await conn.fetch(query, *params)
            
            messages = []
            for result in results:
                message = SessionMessage(
                    message_id=result['message_id'],
                    session_id=result['session_id'],
                    role=result['role'],
                    content=result['content'],
                    timestamp=result['timestamp'],
                    files_referenced=json.loads(result['files_referenced']) if result['files_referenced'] else [],
                    code_snippets=json.loads(result['code_snippets']) if result['code_snippets'] else [],
                    metadata=json.loads(result['metadata']) if result['metadata'] else None
                )
                messages.append(message)
            
            # Return in chronological order
            return list(reversed(messages))
    
    async def get_message(self, message_id: str) -> Optional[SessionMessage]:
        """Get a specific message by ID."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT * FROM chat_messages WHERE message_id = $1;
            """, message_id)
            
            if not result:
                return None
            
            return SessionMessage(
                message_id=result['message_id'],
                session_id=result['session_id'],
                role=result['role'],
                content=result['content'],
                timestamp=result['timestamp'],
                files_referenced=json.loads(result['files_referenced']) if result['files_referenced'] else [],
                code_snippets=json.loads(result['code_snippets']) if result['code_snippets'] else [],
                metadata=json.loads(result['metadata']) if result['metadata'] else None
            )
    
    # Performance Metrics Methods
    
    async def record_chat_metrics(
        self, 
        session_id: str, 
        message_id: str,
        tokens_used: int,
        latency_ms: float,
        cache_hit: bool = False
    ):
        """Record chat performance metrics."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_metrics 
                (session_id, message_id, tokens_used, latency_ms, cache_hit)
                VALUES ($1, $2, $3, $4, $5);
            """, session_id, message_id, tokens_used, latency_ms, cache_hit)
    
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get performance metrics for a session."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_messages,
                    SUM(tokens_used) as total_tokens,
                    AVG(latency_ms) as avg_latency,
                    AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) as cache_hit_rate,
                    MIN(timestamp) as first_message,
                    MAX(timestamp) as last_message
                FROM chat_metrics 
                WHERE session_id = $1;
            """, session_id)
            
            if result and result['total_messages']:
                duration = (result['last_message'] - result['first_message']).total_seconds()
                return {
                    'total_messages': result['total_messages'],
                    'total_tokens': result['total_tokens'] or 0,
                    'average_latency_ms': float(result['avg_latency']) if result['avg_latency'] else 0,
                    'cache_hit_rate': float(result['cache_hit_rate']) if result['cache_hit_rate'] else 0,
                    'session_duration_seconds': duration,
                    'first_message': result['first_message'],
                    'last_message': result['last_message']
                }
            
            return {
                'total_messages': 0,
                'total_tokens': 0,
                'average_latency_ms': 0,
                'cache_hit_rate': 0,
                'session_duration_seconds': 0,
                'first_message': None,
                'last_message': None
            }
    
    # File Context Management Methods
    
    async def add_file_context(
        self, 
        session_id: str, 
        file_context: FileContext
    ) -> bool:
        """Add file context to a session."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            # Check if file already exists in context
            existing = await conn.fetchval("""
                SELECT id FROM file_contexts 
                WHERE session_id = $1 AND file_path = $2 AND branch = $3;
            """, session_id, file_context.path, file_context.branch)
            
            if existing:
                # Update existing file context
                await conn.execute("""
                    UPDATE file_contexts 
                    SET content = $4, file_size = $5, language = $6, file_type = $7,
                        chunk_count = $8, token_count = $9, last_accessed = NOW()
                    WHERE session_id = $1 AND file_path = $2 AND branch = $3;
                """, 
                session_id, file_context.path, file_context.branch,
                file_context.content, file_context.size, file_context.language,
                file_context.file_type, file_context.chunk_count, file_context.token_count
                )
            else:
                # Insert new file context
                await conn.execute("""
                    INSERT INTO file_contexts 
                    (session_id, file_path, branch, content, file_size, language, 
                     file_type, chunk_count, token_count)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
                """, 
                session_id, file_context.path, file_context.branch,
                file_context.content, file_context.size, file_context.language,
                file_context.file_type, file_context.chunk_count, file_context.token_count
                )
            
            return True
    
    async def get_session_file_contexts(self, session_id: str) -> List[FileContext]:
        """Get all file contexts for a session."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT * FROM file_contexts 
                WHERE session_id = $1 
                ORDER BY last_accessed DESC;
            """, session_id)
            
            contexts = []
            for result in results:
                context = FileContext(
                    path=result['file_path'],
                    branch=result['branch'],
                    content=result['content'],
                    size=result['file_size'],
                    language=result['language'],
                    file_type=result['file_type'],
                    added_at=result['added_at'],
                    last_accessed=result['last_accessed'],
                    chunk_count=result['chunk_count'],
                    token_count=result['token_count']
                )
                contexts.append(context)
            
            return contexts
    
    async def remove_file_context(
        self, 
        session_id: str, 
        file_path: str, 
        branch: str = "main"
    ) -> bool:
        """Remove file context from a session."""
        if not self._initialized:
            await self.initialize()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.fetchval("""
                DELETE FROM file_contexts 
                WHERE session_id = $1 AND file_path = $2 AND branch = $3
                RETURNING id;
            """, session_id, file_path, branch)
            
            return result is not None
    
    # Cleanup Methods
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old inactive sessions."""
        if not self._initialized:
            await self.initialize()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        async with self.connection_pool.acquire() as conn:
            deleted_count = await conn.fetchval("""
                DELETE FROM chat_sessions 
                WHERE last_activity < $1 AND status != 'active'
                RETURNING COUNT(*);
            """, cutoff_date)
            
            logger.info(f"Cleaned up {deleted_count or 0} old chat sessions")
            return deleted_count or 0
    
    async def get_session_stats(self, session_id: str) -> SessionStats:
        """Get comprehensive session statistics."""
        if not self._initialized:
            await self.initialize()
        
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        metrics = await self.get_session_metrics(session_id)
        file_contexts = await self.get_session_file_contexts(session_id)
        
        total_files = len(file_contexts)
        total_tokens = sum(fc.token_count for fc in file_contexts)
        avg_tokens_per_file = total_tokens / total_files if total_files > 0 else 0
        
        return SessionStats(
            session_id=session_id,
            total_files=total_files,
            total_tokens=total_tokens,
            average_tokens_per_file=avg_tokens_per_file,
            message_count=session.message_count,
            session_duration=metrics['session_duration_seconds'],
            created_at=session.created_at,
            updated_at=session.updated_at
        )


# Global instance
chat_history_manager = ChatHistoryManager()