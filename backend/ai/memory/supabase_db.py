"""
Supabase PostgreSQL database handler for memory storage
"""
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from supabase import create_client, Client

# Set up logger
logger = logging.getLogger(__name__)

class SupabaseMemory:
    """
    Handles memory storage using Supabase PostgreSQL.
    This class provides functionality for storing and retrieving memories.
    """
    
    def __init__(self, config: Dict[str, Any], verbose: int = 0):
        """
        Initialize Supabase PostgreSQL connection and tables.
        
        Args:
            config: Configuration dictionary with Supabase and PostgreSQL settings
            verbose: Verbosity level
        """
        self.cfg = config or {}
        self.verbose = verbose
        
        # Set logger level based on verbose
        if verbose >= 5:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)
        
        # Get credentials
        self.supabase_url = self.cfg.get("supabase_url", os.getenv("SUPABASE_URL"))
        self.supabase_key = self.cfg.get("supabase_key", os.getenv("SUPABASE_ANON_KEY"))
        self.supabase_service_key = self.cfg.get("supabase_service_key", os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
        
        # Get direct PostgreSQL connection info (for faster operations)
        self.pg_host = self.cfg.get("pg_host", os.getenv("POSTGRES_HOST"))
        self.pg_port = self.cfg.get("pg_port", os.getenv("POSTGRES_PORT", "5432"))
        self.pg_db = self.cfg.get("pg_db", os.getenv("POSTGRES_DB", "postgres"))
        self.pg_user = self.cfg.get("pg_user", os.getenv("POSTGRES_USER"))
        self.pg_password = self.cfg.get("pg_password", os.getenv("POSTGRES_PASSWORD"))
        self.pg_ssl = self.cfg.get("pg_ssl", os.getenv("POSTGRES_SSL", "require"))
        
        # Extract embedding model from config
        self.embedder_config = self.cfg.get("embedder", {})
        if isinstance(self.embedder_config, dict):
            embedder_model_config = self.embedder_config.get("config", {})
            self.embedding_model = embedder_model_config.get("model", "text-embedding-3-small")
        else:
            self.embedding_model = "text-embedding-3-small"
        
        self._log_verbose(f"Using embedding model: {self.embedding_model}")
        
        # Determine embedding dimensions based on model
        self.embedding_dimensions = self._get_embedding_dimensions(self.embedding_model)
        self._log_verbose(f"Using embedding dimensions: {self.embedding_dimensions}")
        
        # Initialize Supabase client
        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            self._log_verbose("Supabase client initialized")
        except Exception as e:
            self._log_verbose(f"Error initializing Supabase client: {e}", logging.ERROR)
            self.supabase = None
        
        # Initialize direct PostgreSQL connection
        try:
            self.conn = self._get_pg_connection()
            self._log_verbose("PostgreSQL connection established")
        except Exception as e:
            self._log_verbose(f"Error connecting to PostgreSQL: {e}", logging.ERROR)
            self.conn = None
            
        # Initialize tables
        self._init_tables()
        
        # Check if we have pgvector installed
        self.has_pgvector = self._check_pgvector()
        if self.has_pgvector:
            self._log_verbose("pgvector extension available")
            self._setup_vector_search()
        else:
            self._log_verbose("pgvector extension not available, vector search will be disabled", logging.WARNING)
    
    def _log_verbose(self, msg: str, level: int = logging.INFO):
        """Only log if verbose >= 5"""
        if self.verbose >= 5:
            logger.log(level, msg)
    
    def _get_pg_connection(self):
        """Create a PostgreSQL connection"""
        conn = psycopg2.connect(
            host=self.pg_host,
            port=self.pg_port,
            dbname=self.pg_db,
            user=self.pg_user,
            password=self.pg_password,
            sslmode=self.pg_ssl
        )
        return conn
    
    def _init_tables(self):
        """Create tables if they don't exist"""
        try:
            with self.conn.cursor() as cursor:
                # Create short_term_memory table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS short_term_memory (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    content TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
                
                # Create long_term_memory table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    content TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
                
                # Create entity_memory table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_memory (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    relationships TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
                
                # Create user_memory table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_short_term_content ON short_term_memory USING GIN (to_tsvector('english', content));")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_long_term_content ON long_term_memory USING GIN (to_tsvector('english', content));")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_name ON entity_memory(entity_name);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON entity_memory(entity_type);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON user_memory(user_id);")
                
                self.conn.commit()
                self._log_verbose("Tables initialized successfully")
        except Exception as e:
            self._log_verbose(f"Error initializing tables: {e}", logging.ERROR)
            self.conn.rollback()
    
    def _check_pgvector(self) -> bool:
        """Check if pgvector extension is available"""
        try:
            with self.conn.cursor() as cursor:
                # Check if the pgvector extension is already installed
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
                if cursor.fetchone() is None:
                    # Try to create the extension
                    try:
                        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                        self.conn.commit()
                        self._log_verbose("Vector extension created successfully")
                    except Exception as e:
                        self._log_verbose(f"Could not create vector extension: {e}", logging.WARNING)
                        self.conn.rollback()
                        return False
                
                # Verify that the extension is working
                try:
                    cursor.execute("SELECT '[1,2,3]'::vector;")
                    cursor.fetchone()
                    return True
                except Exception:
                    return False
                    
        except Exception as e:
            self._log_verbose(f"Error checking pgvector extension: {e}", logging.WARNING)
            return False
    
    def _setup_vector_search(self):
        """Setup vector columns and indexes for search"""
        try:
            with self.conn.cursor() as cursor:
                # Add vector columns if they don't exist
                cursor.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'short_term_memory' AND column_name = 'embedding'
                    ) THEN
                        ALTER TABLE short_term_memory ADD COLUMN embedding vector({self.embedding_dimensions});
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'long_term_memory' AND column_name = 'embedding'
                    ) THEN
                        ALTER TABLE long_term_memory ADD COLUMN embedding vector({self.embedding_dimensions});
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'entity_memory' AND column_name = 'embedding'
                    ) THEN
                        ALTER TABLE entity_memory ADD COLUMN embedding vector({self.embedding_dimensions});
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'user_memory' AND column_name = 'embedding'
                    ) THEN
                        ALTER TABLE user_memory ADD COLUMN embedding vector({self.embedding_dimensions});
                    END IF;
                END $$;
                """)
                
                # Create vector indexes
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_short_term_embedding ON short_term_memory USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
                """)
                
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_long_term_embedding ON long_term_memory USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
                """)
                
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entity_embedding ON entity_memory USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
                """)
                
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_memory_embedding ON user_memory USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
                """)
                
                self.conn.commit()
                self._log_verbose("Vector search indexes created successfully")
        except Exception as e:
            self._log_verbose(f"Error setting up vector search: {e}", logging.WARNING)
            self.conn.rollback()
    
    def _get_embedding_dimensions(self, model_name: str) -> int:
        """Get embedding dimensions based on model name."""
        # Common embedding model dimensions
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "text-embedding-002": 1536,
            # Add more models as needed
        }
        
        # Check if model name contains known model identifiers
        for model_key, dimensions in model_dimensions.items():
            if model_key in model_name.lower():
                return dimensions
        
        # Default to 1536 for unknown models (OpenAI standard)
        return 1536

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using available embedding services."""
        try:
            try:
                import litellm
                # Use LiteLLM for consistency with the rest of the codebase
                response = litellm.embedding(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0]["embedding"]
            except ImportError:
                # Fallback to OpenAI client
                try:
                    from openai import OpenAI
                    client = OpenAI()
                    
                    response = client.embeddings.create(
                        input=text,
                        model=self.embedding_model
                    )
                    return response.data[0].embedding
                except ImportError:
                    self._log_verbose("Neither litellm nor openai available for embeddings", logging.WARNING)
                    return None
        except Exception as e:
            self._log_verbose(f"Error getting embedding: {e}", logging.ERROR)
            return None
    
    def store_short_term(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Store in short-term memory with optional metadata"""
        try:
            # Generate a unique UUID
            memory_id = str(uuid.uuid4())
            
            # Get embedding if pgvector is available
            embedding = self._get_embedding(text) if self.has_pgvector else None
            
            with self.conn.cursor() as cursor:
                if embedding:
                    cursor.execute(
                        """
                        INSERT INTO short_term_memory (id, content, metadata, embedding)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (memory_id, text, json.dumps(metadata) if metadata else None, embedding)
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO short_term_memory (id, content, metadata)
                        VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (memory_id, text, json.dumps(metadata) if metadata else None)
                    )
                
                inserted_id = cursor.fetchone()[0]
                self.conn.commit()
                self._log_verbose(f"Successfully stored in short-term memory with ID: {inserted_id}")
                return inserted_id
                
        except Exception as e:
            self._log_verbose(f"Failed to store in short-term memory: {e}", logging.ERROR)
            self.conn.rollback()
            raise
    
    def search_short_term(
        self, 
        query: str, 
        limit: int = 5,
        min_quality: float = 0.0,
        relevance_cutoff: float = 0.0,
        rerank: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search short-term memory with optional quality filter"""
        self._log_verbose(f"Searching short memory for: {query}")
        
        results = []
        
        try:
            # Try vector search if available
            if self.has_pgvector:
                embedding = self._get_embedding(query)
                if embedding:
                    with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(
                            """
                            SELECT 
                                id, 
                                content, 
                                metadata,
                                created_at,
                                1 - (embedding <=> %s) as score
                            FROM short_term_memory
                            WHERE 
                                (metadata->>'quality')::float >= %s
                                AND 1 - (embedding <=> %s) >= %s
                            ORDER BY embedding <=> %s
                            LIMIT %s
                            """,
                            (embedding, min_quality, embedding, relevance_cutoff, embedding, limit)
                        )
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            results.append({
                                "id": str(row['id']),
                                "text": row['content'],
                                "metadata": row['metadata'],
                                "score": row['score']
                            })
            
            # Fallback to text search if no vector results
            if not results:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            id, 
                            content, 
                            metadata,
                            created_at
                        FROM short_term_memory
                        WHERE 
                            to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                            AND (metadata->>'quality')::float >= %s
                        LIMIT %s
                        """,
                        (query, min_quality, limit)
                    )
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        results.append({
                            "id": str(row['id']),
                            "text": row['content'],
                            "metadata": row['metadata'],
                            "score": 1.0  # Default score for text search
                        })
            
            return results
                
        except Exception as e:
            self._log_verbose(f"Error searching short-term memory: {e}", logging.ERROR)
            return []
    
    def store_long_term(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Store in long-term memory with optional metadata"""
        try:
            # Generate a unique UUID
            memory_id = str(uuid.uuid4())
            
            # Get embedding if pgvector is available
            embedding = self._get_embedding(text) if self.has_pgvector else None
            
            with self.conn.cursor() as cursor:
                if embedding:
                    cursor.execute(
                        """
                        INSERT INTO long_term_memory (id, content, metadata, embedding)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (memory_id, text, json.dumps(metadata) if metadata else None, embedding)
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO long_term_memory (id, content, metadata)
                        VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (memory_id, text, json.dumps(metadata) if metadata else None)
                    )
                
                inserted_id = cursor.fetchone()[0]
                self.conn.commit()
                self._log_verbose(f"Successfully stored in long-term memory with ID: {inserted_id}")
                return inserted_id
                
        except Exception as e:
            self._log_verbose(f"Failed to store in long-term memory: {e}", logging.ERROR)
            self.conn.rollback()
            raise
    
    def search_long_term(
        self, 
        query: str, 
        limit: int = 5,
        relevance_cutoff: float = 0.0,
        min_quality: float = 0.0,
        rerank: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search long-term memory with optional quality filter"""
        self._log_verbose(f"Searching long memory for: {query}")
        
        results = []
        
        try:
            # Try vector search if available
            if self.has_pgvector:
                embedding = self._get_embedding(query)
                if embedding:
                    with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(
                            """
                            SELECT 
                                id, 
                                content, 
                                metadata,
                                created_at,
                                1 - (embedding <=> %s) as score
                            FROM long_term_memory
                            WHERE 
                                (metadata->>'quality')::float >= %s
                                AND 1 - (embedding <=> %s) >= %s
                            ORDER BY embedding <=> %s
                            LIMIT %s
                            """,
                            (embedding, min_quality, embedding, relevance_cutoff, embedding, limit)
                        )
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            text = row['content']
                            # Add memory record citation
                            if "(Memory record:" not in text:
                                text = f"{text} (Memory record: {str(row['id'])})"
                            results.append({
                                "id": str(row['id']),
                                "text": text,
                                "metadata": row['metadata'],
                                "score": row['score']
                            })
            
            # Fallback to text search if no vector results
            if not results:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            id, 
                            content, 
                            metadata,
                            created_at
                        FROM long_term_memory
                        WHERE 
                            to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                            AND (metadata->>'quality')::float >= %s
                        LIMIT %s
                        """,
                        (query, min_quality, limit)
                    )
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        text = row['content']
                        # Add memory record citation
                        if "(Memory record:" not in text:
                            text = f"{text} (Memory record: {str(row['id'])})"
                        results.append({
                            "id": str(row['id']),
                            "text": text,
                            "metadata": row['metadata'],
                            "score": 1.0  # Default score for text search
                        })
            
            return results
                
        except Exception as e:
            self._log_verbose(f"Error searching long-term memory: {e}", logging.ERROR)
            return []

    def store_entity(self, name: str, type_: str, desc: str, relations: str) -> str:
        """Store entity in entity memory"""
        try:
            # Generate a unique UUID
            entity_id = str(uuid.uuid4())
            
            # Create combined text for embedding
            combined_text = f"Entity {name}({type_}): {desc} | relationships: {relations}"
            
            # Get embedding if pgvector is available
            embedding = self._get_embedding(combined_text) if self.has_pgvector else None
            
            with self.conn.cursor() as cursor:
                if embedding:
                    cursor.execute(
                        """
                        INSERT INTO entity_memory (id, entity_name, entity_type, description, relationships, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (entity_id, name, type_, desc, relations, embedding)
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO entity_memory (id, entity_name, entity_type, description, relationships)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (entity_id, name, type_, desc, relations)
                    )
                
                inserted_id = cursor.fetchone()[0]
                self.conn.commit()
                self._log_verbose(f"Successfully stored entity with ID: {inserted_id}")
                return inserted_id
                
        except Exception as e:
            self._log_verbose(f"Failed to store entity: {e}", logging.ERROR)
            self.conn.rollback()
            raise
    
    def search_entity(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search entity memory"""
        self._log_verbose(f"Searching entities for: {query}")
        
        results = []
        
        try:
            # Try vector search if available
            if self.has_pgvector:
                embedding = self._get_embedding(query)
                if embedding:
                    with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(
                            """
                            SELECT 
                                id, 
                                entity_name,
                                entity_type,
                                description,
                                relationships,
                                created_at,
                                1 - (embedding <=> %s) as score
                            FROM entity_memory
                            ORDER BY embedding <=> %s
                            LIMIT %s
                            """,
                            (embedding, embedding, limit)
                        )
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            text = f"Entity {row['entity_name']}({row['entity_type']}): {row['description']} | relationships: {row['relationships']}"
                            results.append({
                                "id": str(row['id']),
                                "text": text,
                                "metadata": {
                                    "entity_name": row['entity_name'],
                                    "entity_type": row['entity_type'],
                                    "category": "entity"
                                },
                                "score": row['score']
                            })
            
            # Fallback to text search if no vector results
            if not results:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            id, 
                            entity_name,
                            entity_type,
                            description,
                            relationships,
                            created_at
                        FROM entity_memory
                        WHERE 
                            entity_name ILIKE %s OR 
                            entity_type ILIKE %s OR 
                            description ILIKE %s OR
                            relationships ILIKE %s
                        LIMIT %s
                        """,
                        (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit)
                    )
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        text = f"Entity {row['entity_name']}({row['entity_type']}): {row['description']} | relationships: {row['relationships']}"
                        results.append({
                            "id": str(row['id']),
                            "text": text,
                            "metadata": {
                                "entity_name": row['entity_name'],
                                "entity_type": row['entity_type'],
                                "category": "entity"
                            },
                            "score": 1.0  # Default score for text search
                        })
            
            return results
                
        except Exception as e:
            self._log_verbose(f"Error searching entity memory: {e}", logging.ERROR)
            return []

    def store_user_memory(self, user_id: str, text: str, extra: Dict[str, Any] = None) -> str:
        """Store user memory"""
        try:
            # Generate a unique UUID
            memory_id = str(uuid.uuid4())
            
            # Prepare metadata
            metadata = {"user_id": user_id}
            if extra:
                metadata.update(extra)
            
            # Get embedding if pgvector is available
            embedding = self._get_embedding(text) if self.has_pgvector else None
            
            with self.conn.cursor() as cursor:
                if embedding:
                    cursor.execute(
                        """
                        INSERT INTO user_memory (id, user_id, content, metadata, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (memory_id, user_id, text, json.dumps(metadata), embedding)
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO user_memory (id, user_id, content, metadata)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (memory_id, user_id, text, json.dumps(metadata))
                    )
                
                inserted_id = cursor.fetchone()[0]
                self.conn.commit()
                self._log_verbose(f"Successfully stored user memory with ID: {inserted_id}")
                return inserted_id
                
        except Exception as e:
            self._log_verbose(f"Failed to store user memory: {e}", logging.ERROR)
            self.conn.rollback()
            raise
    
    def search_user_memory(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 5, 
        rerank: bool = False
    ) -> List[Dict[str, Any]]:
        """Search user memory"""
        self._log_verbose(f"Searching user memory for user {user_id} with query: {query}")
        
        results = []
        
        try:
            # Try vector search if available
            if self.has_pgvector:
                embedding = self._get_embedding(query)
                if embedding:
                    with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(
                            """
                            SELECT 
                                id, 
                                content,
                                metadata,
                                created_at,
                                1 - (embedding <=> %s) as score
                            FROM user_memory
                            WHERE user_id = %s
                            ORDER BY embedding <=> %s
                            LIMIT %s
                            """,
                            (embedding, user_id, embedding, limit)
                        )
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            results.append({
                                "id": str(row['id']),
                                "text": row['content'],
                                "metadata": row['metadata'],
                                "score": row['score']
                            })
            
            # Fallback to text search if no vector results
            if not results:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            id, 
                            content,
                            metadata,
                            created_at
                        FROM user_memory
                        WHERE 
                            user_id = %s AND
                            to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                        LIMIT %s
                        """,
                        (user_id, query, limit)
                    )
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        results.append({
                            "id": str(row['id']),
                            "text": row['content'],
                            "metadata": row['metadata'],
                            "score": 1.0  # Default score for text search
                        })
            
            return results
                
        except Exception as e:
            self._log_verbose(f"Error searching user memory: {e}", logging.ERROR)
            return []

    def reset_short_term(self):
        """Clear short-term memory"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM short_term_memory")
                self.conn.commit()
                self._log_verbose("Short-term memory cleared")
        except Exception as e:
            self._log_verbose(f"Error clearing short-term memory: {e}", logging.ERROR)
            self.conn.rollback()
    
    def reset_long_term(self):
        """Clear long-term memory"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM long_term_memory")
                self.conn.commit()
                self._log_verbose("Long-term memory cleared")
        except Exception as e:
            self._log_verbose(f"Error clearing long-term memory: {e}", logging.ERROR)
            self.conn.rollback()
    
    def reset_entity_only(self):
        """Clear entity memory"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM entity_memory")
                self.conn.commit()
                self._log_verbose("Entity memory cleared")
        except Exception as e:
            self._log_verbose(f"Error clearing entity memory: {e}", logging.ERROR)
            self.conn.rollback()
    
    def reset_user_memory(self):
        """Clear user memory"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_memory")
                self.conn.commit()
                self._log_verbose("User memory cleared")
        except Exception as e:
            self._log_verbose(f"Error clearing user memory: {e}", logging.ERROR)
            self.conn.rollback()
    
    def reset_all(self):
        """Clear all memory tables"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM short_term_memory")
                cursor.execute("DELETE FROM long_term_memory")
                cursor.execute("DELETE FROM entity_memory")
                cursor.execute("DELETE FROM user_memory")
                self.conn.commit()
                self._log_verbose("All memory cleared")
        except Exception as e:
            self._log_verbose(f"Error clearing all memory: {e}", logging.ERROR)
            self.conn.rollback()
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self._log_verbose("PostgreSQL connection closed")
