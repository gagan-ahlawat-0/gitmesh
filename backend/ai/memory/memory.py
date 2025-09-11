import os
import json
import time
from typing import Any, Dict, List, Optional, Union, Literal
import logging
from datetime import datetime

# Disable litellm telemetry before any imports
os.environ["LITELLM_TELEMETRY"] = "False"

# Set up logger with custom TRACE level
logger = logging.getLogger(__name__)

# Add custom TRACE level (below DEBUG)
TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, 'TRACE')

def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)

logging.Logger.trace = trace

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import litellm
    litellm.telemetry = False  # Disable telemetry
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

try:
    # Check for Supabase dependencies
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from supabase import create_client, Client
    from .supabase_db import SupabaseMemory
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase dependencies not available. Install with: pip install supabase psycopg2-binary")
    pass




class Memory:
    """
    A single-file memory manager covering:
    - Short-term memory (STM) for ephemeral context
    - Long-term memory (LTM) for persistent knowledge
    - Entity memory (structured data about named entities)
    - User memory (preferences/history for each user)
    - Quality score logic for deciding which data to store in LTM
    - Context building from multiple memory sources
    - Graph memory support for complex relationship storage (via Mem0)

    Config example:
    {
      "provider": "rag" or "mem0" or "supabase" or "none",
      "use_embedding": True,
      "short_db": "short_term.db",
      "long_db": "long_term.db",
      "rag_db_path": "rag_db",   # optional path for local embedding store
      "config": {
        "api_key": "...",       # if mem0 usage
        "org_id": "...",
        "project_id": "...",
        
        # Supabase configuration (recommended provider) 
        "supabase_url": "https://your-project.supabase.co",
        "supabase_anon_key": "your-anon-key",
        "supabase_service_role_key": "your-service-role-key",
        
        # Graph memory configuration (optional)
        "graph_store": {
          "provider": "neo4j" or "memgraph",
          "config": {
            "url": "neo4j+s://xxx" or "bolt://localhost:7687",
            "username": "neo4j" or "memgraph",
            "password": "xxx"
          }
        },
        
        # Optional additional configurations for graph memory
        "vector_store": {
          "provider": "qdrant",
          "config": {"host": "localhost", "port": 6333}
        },
        "llm": {
          "provider": "openai",
          "config": {"model": "gpt-5-nano", "api_key": "..."}
        },
        "embedder": {
          "provider": "openai",
          "config": {"model": "text-embedding-3-small", "api_key": "..."}
        }
      }
    }
    
    Note: Graph memory requires "mem0ai[graph]" installation and works alongside 
    vector-based memory for enhanced relationship-aware retrieval.
    """

    def __init__(self, config: Dict[str, Any], verbose: int = 0):
        self.cfg = config or {}
        self.verbose = verbose
        
        # Set logger level based on verbose
        if verbose >= 5:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)
            
        # Set client loggers to WARNING
        logging.getLogger('openai').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('utils').setLevel(logging.WARNING)
        logging.getLogger('litellm.utils').setLevel(logging.WARNING)
            
        # Always use Supabase as provider
        self.provider = "supabase"
        self.use_supabase = SUPABASE_AVAILABLE
        
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
            
        # Initialize Supabase database
        if self.use_supabase:
            self._log_verbose("Using Supabase PostgreSQL for memory storage")
            self._init_supabase()
        else:
            self._log_verbose("ERROR: Supabase dependencies are not available. Install with: pip install supabase psycopg2-binary", logging.ERROR)
            raise ImportError("Supabase dependencies are not available. Install with: pip install supabase psycopg2-binary")

    def _log_verbose(self, msg: str, level: int = logging.INFO):
        """Only log if verbose >= 5"""
        if self.verbose >= 5:
            logger.log(level, msg)

    # -------------------------------------------------------------------------
    #                          Initialization
    # -------------------------------------------------------------------------
    def _init_supabase(self):
        """Initialize Supabase PostgreSQL for memory storage."""
        try:
            # Get Supabase configuration from environment variables or config
            supabase_config = self.cfg.get("supabase_config", {})
            
            # Create the Supabase Memory instance
            self.supabase_memory = SupabaseMemory(
                config=supabase_config,
                verbose=self.verbose
            )
            
            self._log_verbose("Supabase PostgreSQL initialized successfully")
            
        except Exception as e:
            self._log_verbose(f"Failed to initialize Supabase: {e}", logging.ERROR)
            self.use_supabase = False

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using available embedding services.
        This method is used by Supabase's pgvector for vector search.
        """
        try:
            if LITELLM_AVAILABLE:
                # Use LiteLLM for consistency with the rest of the codebase
                import litellm
                
                response = litellm.embedding(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0]["embedding"]
            elif OPENAI_AVAILABLE:
                # Fallback to OpenAI client
                from openai import OpenAI
                client = OpenAI()
                
                response = client.embeddings.create(
                    input=text,
                    model=self.embedding_model
                )
                return response.data[0].embedding
            else:
                self._log_verbose("Neither litellm nor openai available for embeddings", logging.WARNING)
                return None
        except Exception as e:
            self._log_verbose(f"Error getting embedding: {e}", logging.ERROR)
            return None

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

    # -------------------------------------------------------------------------
    #                      Basic Quality Score Computation
    # -------------------------------------------------------------------------
    def compute_quality_score(
        self,
        completeness: float,
        relevance: float,
        clarity: float,
        accuracy: float,
        weights: Dict[str, float] = None
    ) -> float:
        """
        Combine multiple sub-metrics into one final score, as an example.

        Args:
            completeness (float): 0-1
            relevance (float): 0-1
            clarity (float): 0-1
            accuracy (float): 0-1
            weights (Dict[str, float]): optional weighting like {"completeness": 0.25, "relevance": 0.3, ...}

        Returns:
            float: Weighted average 0-1
        """
        if not weights:
            weights = {
                "completeness": 0.25,
                "relevance": 0.25,
                "clarity": 0.25,
                "accuracy": 0.25
            }
        total = (completeness * weights["completeness"]
                 + relevance   * weights["relevance"]
                 + clarity     * weights["clarity"]
                 + accuracy    * weights["accuracy"]
                )
        return round(total, 3)  # e.g. round to 3 decimal places

    # -------------------------------------------------------------------------
    #                           Short-Term Methods
    # -------------------------------------------------------------------------
    def store_short_term(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        completeness: float = None,
        relevance: float = None,
        clarity: float = None,
        accuracy: float = None,
        weights: Dict[str, float] = None,
        evaluator_quality: float = None
    ):
        """Store in short-term memory with optional quality metrics"""
        logger.info(f"Storing in short-term memory: {text[:100]}...")
        logger.info(f"Metadata: {metadata}")
        
        metadata = self._process_quality_metrics(
            metadata, completeness, relevance, clarity, 
            accuracy, weights, evaluator_quality
        )
        logger.info(f"Processed metadata: {metadata}")
        
        # Use Supabase for storage
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                memory_id = self.supabase_memory.store_short_term(
                    text=text,
                    metadata=metadata
                )
                logger.info(f"Successfully stored in Supabase short-term memory with ID: {memory_id}")
                return memory_id
            except Exception as e:
                logger.error(f"Failed to store in Supabase short-term memory: {e}")
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def search_short_term(
        self, 
        query: str, 
        limit: int = 5,
        min_quality: float = 0.0,
        relevance_cutoff: float = 0.0,
        rerank: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Search short-term memory with optional quality filter"""
        self._log_verbose(f"Searching short memory for: {query}")
        
        # Use Supabase for search
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                results = self.supabase_memory.search_short_term(
                    query=query,
                    limit=limit,
                    min_quality=min_quality,
                    relevance_cutoff=relevance_cutoff,
                    rerank=rerank
                )
                return results
            except Exception as e:
                self._log_verbose(f"Error searching Supabase short-term memory: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def reset_short_term(self):
        """Reset short-term memory in Supabase"""
        # Use Supabase to reset short-term memory
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                self.supabase_memory.reset_short_term()
                self._log_verbose("Successfully reset short-term memory in Supabase")
            except Exception as e:
                self._log_verbose(f"Error resetting short-term memory in Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    # -------------------------------------------------------------------------
    #                           Long-Term Methods
    # -------------------------------------------------------------------------
    def _sanitize_metadata(self, metadata: Dict) -> Dict:
        """Sanitize metadata for ChromaDB - convert to acceptable types"""
        sanitized = {}
        for k, v in metadata.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                sanitized[k] = v
            elif isinstance(v, dict):
                # Convert dict to string representation
                sanitized[k] = str(v)
            else:
                # Convert other types to string
                sanitized[k] = str(v)
        return sanitized

    def store_long_term(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        completeness: float = None,
        relevance: float = None,
        clarity: float = None,
        accuracy: float = None,
        weights: Dict[str, float] = None,
        evaluator_quality: float = None
    ):
        """Store in long-term memory with optional quality metrics"""
        logger.info(f"Storing in long-term memory: {text[:100]}...")
        logger.info(f"Initial metadata: {metadata}")
        
        # Process metadata
        metadata = metadata or {}
        metadata = self._process_quality_metrics(
            metadata, completeness, relevance, clarity,
            accuracy, weights, evaluator_quality
        )
        logger.info(f"Processed metadata: {metadata}")
        
        # Store in Supabase
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                memory_id = self.supabase_memory.store_long_term(
                    text=text,
                    metadata=metadata
                )
                logger.info(f"Successfully stored in Supabase long-term memory with ID: {memory_id}")
                return memory_id
            except Exception as e:
                logger.error(f"Failed to store in Supabase long-term memory: {e}")
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")


    def search_long_term(
        self, 
        query: str, 
        limit: int = 5, 
        relevance_cutoff: float = 0.0,
        min_quality: float = 0.0,
        rerank: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Search long-term memory with optional quality filter"""
        self._log_verbose(f"Searching long memory for: {query}")
        self._log_verbose(f"Min quality: {min_quality}")

        # Use Supabase for search
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                results = self.supabase_memory.search_long_term(
                    query=query,
                    limit=limit,
                    relevance_cutoff=relevance_cutoff,
                    min_quality=min_quality,
                    rerank=rerank
                )
                return results
            except Exception as e:
                self._log_verbose(f"Error searching Supabase long-term memory: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def reset_long_term(self):
        """Reset long-term memory in Supabase"""
        # Use Supabase to reset long-term memory
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                self.supabase_memory.reset_long_term()
                self._log_verbose("Successfully reset long-term memory in Supabase")
            except Exception as e:
                self._log_verbose(f"Error resetting long-term memory in Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    # -------------------------------------------------------------------------
    #                       Entity Memory Methods
    # -------------------------------------------------------------------------
    def store_entity(self, name: str, type_: str, desc: str, relations: str):
        """
        Save entity info in Supabase
        """
        # Use Supabase for entity storage
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                entity_id = self.supabase_memory.store_entity(
                    name=name,
                    type_=type_,
                    desc=desc,
                    relations=relations
                )
                self._log_verbose(f"Successfully stored entity in Supabase with ID: {entity_id}")
                return entity_id
            except Exception as e:
                self._log_verbose(f"Error storing entity in Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def search_entity(
        self, 
        query: str, 
        entity_type: Optional[str] = None, 
        limit: int = 5, 
        rerank: bool = False
    ) -> List[Dict[str, Any]]:
        """Search entity memory by query"""
        self._log_verbose(f"Searching entity memory for: {query}")
        
        # Use Supabase for entity search
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                results = self.supabase_memory.search_entity(
                    query=query,
                    entity_type=entity_type,
                    limit=limit,
                    rerank=rerank
                )
                return results
            except Exception as e:
                self._log_verbose(f"Error searching Supabase entity memory: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def reset_entity_only(self):
        """
        Reset only entity data in Supabase
        """
        # Use Supabase to reset entities
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                self.supabase_memory.reset_entities()
                self._log_verbose("Successfully reset entity memory in Supabase")
            except Exception as e:
                self._log_verbose(f"Error resetting entity memory in Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    # -------------------------------------------------------------------------
    #                       User Memory Methods
    # -------------------------------------------------------------------------
    def store_user_memory(self, user_id: str, text: str, extra: Dict[str, Any] = None):
        """
        Store user-specific memory in Supabase
        """
        meta = {"user_id": user_id}
        if extra:
            meta.update(extra)

        # Use Supabase for user memory storage
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                memory_id = self.supabase_memory.store_user_memory(
                    user_id=user_id,
                    text=text,
                    metadata=meta
                )
                self._log_verbose(f"Successfully stored user memory in Supabase for {user_id}")
                return memory_id
            except Exception as e:
                self._log_verbose(f"Error storing user memory in Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def search_user_memory(self, user_id: str, query: str, limit: int = 5, rerank: bool = False, **kwargs) -> List[Dict[str, Any]]:
        """
        Search user memory in Supabase
        """
        self._log_verbose(f"Searching user memory for user {user_id} with query: {query}")
        
        # Use Supabase for user memory search
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                results = self.supabase_memory.search_user_memory(
                    user_id=user_id,
                    query=query,
                    limit=limit,
                    rerank=rerank
                )
                return results
            except Exception as e:
                self._log_verbose(f"Error searching user memory in Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def search(self, query: str, user_id: Optional[str] = None, agent_id: Optional[str] = None, 
               run_id: Optional[str] = None, limit: int = 5, rerank: bool = False, **kwargs) -> List[Dict[str, Any]]:
        """
        Generic search method that delegates to appropriate specific search methods.
        Provides compatibility with other memory interfaces.
        
        Args:
            query: The search query string
            user_id: Optional user ID for user-specific search
            agent_id: Optional agent ID for agent-specific search  
            run_id: Optional run ID for run-specific search
            limit: Maximum number of results to return
            rerank: Whether to use advanced reranking
            **kwargs: Additional search parameters
            
        Returns:
            List of search results
        """
        # Use Supabase for generic search
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                # If user_id is provided, use user-specific search
                if user_id:
                    return self.search_user_memory(user_id, query, limit=limit, rerank=rerank)
                else:
                    # Default to long-term memory search
                    search_params = {
                        "query": query,
                        "limit": limit,
                        "rerank": rerank
                    }
                    
                    # Add additional filters to metadata if provided
                    metadata_filters = {}
                    if agent_id is not None:
                        metadata_filters["agent_id"] = agent_id
                    if run_id is not None:
                        metadata_filters["run_id"] = run_id
                    
                    # Pass any metadata filters to search
                    if metadata_filters:
                        search_params["metadata_filters"] = metadata_filters
                    
                    # Include any additional kwargs
                    search_params.update(kwargs)
                    
                    return self.search_long_term(**search_params)
            except Exception as e:
                self._log_verbose(f"Error in generic search with Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def reset_user_memory(self):
        """
        Reset only user memory in Supabase
        """
        # Use Supabase to reset user memory
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                self.supabase_memory.reset_user_memory()
                self._log_verbose("Successfully reset user memory in Supabase")
            except Exception as e:
                self._log_verbose(f"Error resetting user memory in Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    # -------------------------------------------------------------------------
    #                 Putting it all Together: Task Finalization
    # -------------------------------------------------------------------------
    def finalize_task_output(
        self,
        content: str,
        agent_name: str,
        quality_score: float,
        threshold: float = 0.7,
        metrics: Dict[str, Any] = None,
        task_id: str = None
    ):
        """Store task output in memory with appropriate metadata"""
        logger.info(f"Finalizing task output: {content[:100]}...")
        logger.info(f"Agent: {agent_name}, Quality: {quality_score}, Threshold: {threshold}")
        
        metadata = {
            "task_id": task_id,
            "agent": agent_name,
            "quality": quality_score,
            "metrics": metrics,
            "task_type": "output",
            "stored_at": time.time()
        }
        logger.info(f"Prepared metadata: {metadata}")
        
        # Always store in short-term memory
        try:
            logger.info("Storing in short-term memory...")
            self.store_short_term(
                text=content,
                metadata=metadata
            )
            logger.info("Successfully stored in short-term memory")
        except Exception as e:
            logger.error(f"Failed to store in short-term memory: {e}")
        
        # Store in long-term memory if quality meets threshold
        # Convert quality_score to float if it's a string to prevent type errors
        quality_score_float = float(quality_score) if isinstance(quality_score, str) else quality_score
        threshold_float = float(threshold) if isinstance(threshold, str) else threshold
        
        if quality_score_float >= threshold_float:
            try:
                logger.info(f"Quality score {quality_score_float} >= {threshold_float}, storing in long-term memory...")
                self.store_long_term(
                    text=content,
                    metadata=metadata
                )
                logger.info("Successfully stored in long-term memory")
            except Exception as e:
                logger.error(f"Failed to store in long-term memory: {e}")
        else:
            logger.info(f"Quality score {quality_score_float} < {threshold_float}, skipping long-term storage")

    # -------------------------------------------------------------------------
    #                 Building Context (Short, Long, Entities, User)
    # -------------------------------------------------------------------------
    def build_context_for_task(
        self,
        task_descr: str,
        user_id: Optional[str] = None,
        additional: str = "",
        max_items: int = 3,
        include_in_output: Optional[bool] = None
    ) -> str:
        """
        Merges relevant short-term, long-term, entity, user memories from Supabase
        into a single text block with deduplication and clean formatting.
        
        Args:
            include_in_output: If None, memory content is only included when debug logging is enabled.
                               If True, memory content is always included.
                               If False, memory content is never included (only logged for debugging).
        """
        # Ensure Supabase is available
        if not self.use_supabase or not hasattr(self, "supabase_memory"):
            self._log_verbose("ERROR: Supabase memory not available for context building", logging.ERROR)
            return ""
            
        # Determine whether to include memory content in output based on logging level
        if include_in_output is None:
            include_in_output = logging.getLogger().getEffectiveLevel() == logging.DEBUG
        
        q = (task_descr + " " + additional).strip()
        lines = []
        seen_contents = set()  # Track unique contents

        def normalize_content(content: str) -> str:
            """Normalize content for deduplication"""
            # Extract just the main content without citations for comparison
            normalized = content.split("(Memory record:")[0].strip()
            # Keep more characters to reduce false duplicates
            normalized = ''.join(c.lower() for c in normalized if not c.isspace())
            return normalized

        def format_content(content: str, max_len: int = 150) -> str:
            """Format content with clean truncation at word boundaries"""
            if not content:
                return ""
            
            # Clean up content by removing extra whitespace and newlines
            content = ' '.join(content.split())
            
            # If content contains a memory citation, preserve it
            if "(Memory record:" in content:
                return content  # Keep original citation format
            
            # Regular content truncation
            if len(content) <= max_len:
                return content
            
            truncate_at = content.rfind(' ', 0, max_len - 3)
            if truncate_at == -1:
                truncate_at = max_len - 3
            return content[:truncate_at] + "..."

        def add_section(title: str, hits: List[Any]) -> None:
            """Add a section of memory hits with deduplication"""
            if not hits:
                return
                
            formatted_hits = []
            for h in hits:
                content = h.get('text', '') if isinstance(h, dict) else str(h)
                if not content:
                    continue
                    
                # Keep original format if it has a citation
                if "(Memory record:" in content:
                    formatted = content
                else:
                    formatted = format_content(content)
                
                # Only add if we haven't seen this normalized content before
                normalized = normalize_content(formatted)
                if normalized not in seen_contents:
                    seen_contents.add(normalized)
                    formatted_hits.append(formatted)
            
            if formatted_hits:
                # Log detailed memory content for debugging including section headers
                brief_title = title.replace(" Context", "").replace("Memory ", "")
                logger.debug(f"Memory section '{brief_title}' ({len(formatted_hits)} items): {formatted_hits}")
                
                # Only include memory content in output when specified (controlled by log level or explicit parameter)
                if include_in_output:
                    # Add only the actual memory content for AI agent use (no headers)
                    if lines:
                        lines.append("")  # Space before new section
                    
                    # Include actual memory content without verbose section headers
                    for hit in formatted_hits:
                        lines.append(f"• {hit}")
                    lines.append("")  # Space after content

        try:
            # Add each section
            # First get all results from Supabase
            short_term = self.search_short_term(q, limit=max_items)
            long_term = self.search_long_term(q, limit=max_items)
            entities = self.search_entity(q, limit=max_items)
            user_mem = self.search_user_memory(user_id, q, limit=max_items) if user_id else []

            # Add sections in order of priority
            add_section("Short-term Memory Context", short_term)
            add_section("Long-term Memory Context", long_term)
            add_section("Entity Context", entities)
            if user_id:
                add_section("User Context", user_mem)

            return "\n".join(lines) if lines else ""
        except Exception as e:
            self._log_verbose(f"Error building context from Supabase: {e}", logging.ERROR)
            return ""

    # -------------------------------------------------------------------------
    #                      Master Reset (Everything)
    # -------------------------------------------------------------------------
    def reset_all(self):
        """
        Fully wipes all memory in Supabase
        """
        # Use Supabase to reset all memory
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                self.supabase_memory.reset_all()
                self._log_verbose("Successfully reset all memory in Supabase")
            except Exception as e:
                self._log_verbose(f"Error resetting all memory in Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")

    def _process_quality_metrics(
        self,
        metadata: Dict[str, Any],
        completeness: float = None,
        relevance: float = None,
        clarity: float = None, 
        accuracy: float = None,
        weights: Dict[str, float] = None,
        evaluator_quality: float = None
    ) -> Dict[str, Any]:
        """Process and store quality metrics in metadata"""
        metadata = metadata or {}
        
        # Handle sub-metrics if provided
        if None not in [completeness, relevance, clarity, accuracy]:
            metadata.update({
                "completeness": completeness,
                "relevance": relevance,
                "clarity": clarity,
                "accuracy": accuracy,
                "quality": self.compute_quality_score(
                    completeness, relevance, clarity, accuracy, weights
                )
            })
        # Handle external evaluator quality if provided
        elif evaluator_quality is not None:
            metadata["quality"] = evaluator_quality
        
        return metadata

    def calculate_quality_metrics(
        self,
        output: str,
        expected_output: str,
        llm: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate quality metrics using LLM"""
        logger.info("Calculating quality metrics for output")
        logger.info(f"Output: {output[:100]}...")
        logger.info(f"Expected: {expected_output[:100]}...")
        
        # Default evaluation prompt
        default_prompt = f"""
        Evaluate the following output against expected output.
        Score each metric from 0.0 to 1.0:
        - Completeness: Does it address all requirements?
        - Relevance: Does it match expected output?
        - Clarity: Is it clear and well-structured?
        - Accuracy: Is it factually correct?

        Expected: {expected_output}
        Actual: {output}

        Return ONLY a JSON with these keys: completeness, relevance, clarity, accuracy
        Example: {{"completeness": 0.95, "relevance": 0.8, "clarity": 0.9, "accuracy": 0.85}}
        """

        try:
            if LITELLM_AVAILABLE:
                # Use LiteLLM for consistency with the rest of the codebase
                import litellm
                
                # Convert model name if it's in litellm format
                model_name = llm or "gpt-5-nano"
                
                response = litellm.completion(
                    model=model_name,
                    messages=[{
                        "role": "user", 
                        "content": custom_prompt or default_prompt
                    }],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
            elif OPENAI_AVAILABLE:
                # Fallback to OpenAI client
                from openai import OpenAI
                client = OpenAI()
                
                response = client.chat.completions.create(
                    model=llm or "gpt-5-nano",
                    messages=[{
                        "role": "user", 
                        "content": custom_prompt or default_prompt
                    }],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
            else:
                logger.error("Neither litellm nor openai available for quality calculation")
                return {
                    "completeness": 0.0,
                    "relevance": 0.0,
                    "clarity": 0.0,
                    "accuracy": 0.0
                }
            
            metrics = json.loads(response.choices[0].message.content)
            
            # Validate metrics
            required = ["completeness", "relevance", "clarity", "accuracy"]
            if not all(k in metrics for k in required):
                raise ValueError("Missing required metrics in LLM response")
            
            logger.info(f"Calculated metrics: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                "completeness": 0.0,
                "relevance": 0.0,
                "clarity": 0.0,
                "accuracy": 0.0
            }

    def store_quality(
        self,
        text: str,
        quality_score: float,
        task_id: Optional[str] = None,
        iteration: Optional[int] = None,
        metrics: Optional[Dict[str, float]] = None,
        memory_type: Literal["short", "long"] = "long"
    ) -> None:
        """Store quality metrics in memory"""
        logger.info(f"Attempting to store in {memory_type} memory: {text[:100]}...")
        
        metadata = {
            "quality": quality_score,
            "task_id": task_id,
            "iteration": iteration
        }
        
        if metrics:
            metadata.update({
                k: v for k, v in metrics.items()  # Remove metric_ prefix
            })
            
        logger.info(f"With metadata: {metadata}")
        
        try:
            if memory_type == "short":
                self.store_short_term(text, metadata=metadata)
                logger.info("Successfully stored in short-term memory")
            else:
                self.store_long_term(text, metadata=metadata)
                logger.info("Successfully stored in long-term memory")
        except Exception as e:
            logger.error(f"Failed to store in memory: {e}")

    def search_with_quality(
        self,
        query: str,
        min_quality: float = 0.0,
        memory_type: Literal["short", "long"] = "long",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search with quality filter"""
        logger.info(f"Searching {memory_type} memory for: {query}")
        logger.info(f"Min quality: {min_quality}")
        
        search_func = (
            self.search_short_term if memory_type == "short" 
            else self.search_long_term
        )
        
        results = search_func(query, limit=limit)
        logger.info(f"Found {len(results)} initial results")
        
        filtered = [
            r for r in results 
            if r.get("metadata", {}).get("quality", 0.0) >= min_quality
        ]
        logger.info(f"After quality filter: {len(filtered)} results")
        
        return filtered

    def get_all_memories(self) -> List[Dict[str, Any]]:
        """Get all memories from Supabase storage"""
        # Use Supabase to get all memories
        if self.use_supabase and hasattr(self, "supabase_memory"):
            try:
                all_memories = self.supabase_memory.get_all_memories()
                return all_memories
            except Exception as e:
                self._log_verbose(f"Error getting all memories from Supabase: {e}", logging.ERROR)
                raise
        else:
            raise RuntimeError("Supabase memory storage is not initialized or available")
