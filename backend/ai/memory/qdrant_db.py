"""
Qdrant Vector Database integration for Memory System.
Provides vector search capabilities for semantic retrieval.
"""

import os
import json
import uuid
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

# Check for required dependencies
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.exceptions import UnexpectedResponse
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("Qdrant dependencies not available. Install with: pip install qdrant-client")

# Try to import free embedding service first, fallback to paid services
try:
    from ..embeddings.free_embeddings import get_default_embeddings
    FREE_EMBEDDINGS_AVAILABLE = True
    logger.info("Using free GitMesh embeddings (Sentence Transformers)")
except ImportError:
    FREE_EMBEDDINGS_AVAILABLE = False
    logger.warning("Free embeddings not available, falling back to OpenAI/LiteLLM")
    
try:
    import litellm
    litellm.telemetry = False  # Disable telemetry
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("litellm not available for embeddings. Install with: pip install litellm")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    if not LITELLM_AVAILABLE and not FREE_EMBEDDINGS_AVAILABLE:
        logger.warning("No embedding service available. Install sentence-transformers for free embeddings")


class QdrantMemory:
    """
    Qdrant Vector Database handler for Memory System.
    Handles vector embeddings and semantic search.
    """

    def __init__(self, config: Dict[str, Any] = None, verbose: int = 0):
        """
        Initialize Qdrant memory with configuration.
        
        Args:
            config: Dictionary with Qdrant connection parameters
            verbose: Verbosity level (0-5)
        """
        self.config = config or {}
        self.verbose = verbose
        
        # Set logger level based on verbose
        if verbose >= 5:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)
            
        # Get configuration from environment if not provided
        self.qdrant_url = self.config.get("url", os.getenv("QDRANT_URL"))
        self.qdrant_api_key = self.config.get("api_key", os.getenv("QDRANT_API_KEY"))
        self.collection_name = self.config.get(
            "collection_name", 
            os.getenv("QDRANT_COLLECTION_NAME", "gitmesh_memory")
        )
        
        # Set embedding model - prefer free embeddings
        if FREE_EMBEDDINGS_AVAILABLE:
            self.embedding_service = get_default_embeddings()
            self.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
            self.embedding_dimensions = self.embedding_service.embedding_dimension
            self._log_verbose(f"Using free embeddings: {self.embedding_model} ({self.embedding_dimensions}D)")
        else:
            # Fallback to paid services
            self.embedding_model = self.config.get("embedding_model", "text-embedding-3-small")
            self.embedding_dimensions = self._get_embedding_dimensions(self.embedding_model)
            self.embedding_service = None
            self._log_verbose(f"Using paid embeddings: {self.embedding_model}")
        
        # Initialize collections
        self._init_qdrant()
        
    def _log_verbose(self, msg: str, level: int = logging.INFO):
        """Only log if verbose >= 5"""
        if self.verbose >= 5:
            logger.log(level, msg)

    def _init_qdrant(self):
        """Initialize Qdrant client and ensure collections exist"""
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant dependencies not available. Install with: pip install qdrant-client")
        
        try:
            # Initialize Qdrant client
            self.client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
                timeout=60  # 60 seconds timeout
            )
            
            self._log_verbose("Qdrant client initialized")
            
            # Check if collections exist, create if not
            collections = [c.name for c in self.client.get_collections().collections]
            
            if self.collection_name not in collections:
                self._log_verbose(f"Creating collection {self.collection_name}")
                
                # Create collection with vector configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.embedding_dimensions,
                        distance=models.Distance.COSINE
                    )
                )
                
                # Create payload indexes for efficient filtering
                self._create_payload_indexes()
            else:
                self._log_verbose(f"Using existing collection {self.collection_name}")
                
        except Exception as e:
            error_msg = f"Failed to initialize Qdrant: {str(e)}"
            self._log_verbose(error_msg, logging.ERROR)
            raise ConnectionError(error_msg)
    
    def _create_payload_indexes(self):
        """Create payload indexes for efficient filtering"""
        try:
            # Create index for memory type (short_term, long_term, entity, user)
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="memory_type",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            # Create index for quality score
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="quality",
                field_schema=models.PayloadSchemaType.FLOAT
            )
            
            # Create index for entity_type
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="entity_type",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            # Create index for user_id
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            # Create index for created_at for time-based queries
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="created_at",
                field_schema=models.PayloadSchemaType.FLOAT
            )
            
            self._log_verbose("Payload indexes created successfully")
            
        except Exception as e:
            self._log_verbose(f"Failed to create payload indexes: {e}", logging.ERROR)

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embeddings for text using available embedding service"""
        try:
            # Use free embeddings if available
            if FREE_EMBEDDINGS_AVAILABLE and self.embedding_service:
                embedding = self.embedding_service.embed(text)
                return embedding.tolist()  # Convert numpy array to list
            
            elif LITELLM_AVAILABLE:
                # Use LiteLLM for consistency with the rest of the codebase
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
                error_msg = "No embedding service available. Install sentence-transformers for free embeddings"
                self._log_verbose(error_msg, logging.ERROR)
                raise ImportError(error_msg)
        except Exception as e:
            self._log_verbose(f"Error getting embedding: {e}", logging.ERROR)
            raise

    def _get_embedding_dimensions(self, model_name: str) -> int:
        """Get embedding dimensions based on model name"""
        # Free embedding models
        if "all-MiniLM-L6-v2" in model_name or "sentence-transformers" in model_name:
            return 384
        elif "all-mpnet-base-v2" in model_name:
            return 768
        elif "paraphrase-MiniLM-L3-v2" in model_name:
            return 384
            
        # OpenAI embedding model dimensions
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "text-embedding-002": 1536,
        }
        
        # Check if model name contains known model identifiers
        for model_key, dimensions in model_dimensions.items():
            if model_key in model_name.lower():
                return dimensions
        
        # Default to 384 for free models, 1536 for OpenAI
        return 384 if FREE_EMBEDDINGS_AVAILABLE else 1536

    def store_memory(
        self,
        text: str,
        memory_type: str,
        metadata: Dict[str, Any] = None,
        vector_id: str = None
    ) -> str:
        """
        Store a memory in the vector database
        
        Args:
            text: The text to store
            memory_type: Type of memory (short_term, long_term, entity, user)
            metadata: Additional metadata for the memory
            vector_id: Optional ID for the vector (generated if not provided)
            
        Returns:
            The ID of the stored memory
        """
        if not text:
            raise ValueError("Text cannot be empty")
            
        metadata = metadata or {}
        memory_id = vector_id or str(uuid.uuid4())
        
        try:
            # Generate embedding
            embedding = self._get_embedding(text)
            
            # Prepare payload
            payload = {
                "text": text,
                "memory_type": memory_type,
                "created_at": time.time()
            }
            
            # Add metadata to payload
            if "quality" in metadata:
                payload["quality"] = float(metadata["quality"])
            if "entity_type" in metadata:
                payload["entity_type"] = metadata["entity_type"]
            if "user_id" in metadata:
                payload["user_id"] = metadata["user_id"]
                
            # Store any remaining metadata
            payload["metadata"] = metadata
            
            # Insert point into collection
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=memory_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            self._log_verbose(f"Stored memory {memory_id} of type {memory_type}")
            return memory_id
            
        except Exception as e:
            self._log_verbose(f"Error storing memory: {e}", logging.ERROR)
            raise

    def search_memory(
        self,
        query: str,
        memory_type: Union[str, List[str]] = None,
        filter_params: Dict[str, Any] = None,
        limit: int = 5,
        relevance_cutoff: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Search for memories using vector similarity
        
        Args:
            query: The text query
            memory_type: Type of memory to search or list of types
            filter_params: Additional filter parameters
            limit: Maximum number of results
            relevance_cutoff: Minimum relevance score (0.0-1.0)
            
        Returns:
            List of matching memories with scores
        """
        try:
            # Generate embedding for query
            query_embedding = self._get_embedding(query)
            
            # Prepare filter
            filter_conditions = []
            
            # Filter by memory type if provided
            if memory_type:
                if isinstance(memory_type, list):
                    filter_conditions.append(
                        models.FieldCondition(
                            key="memory_type",
                            match=models.MatchAny(any=memory_type)
                        )
                    )
                else:
                    filter_conditions.append(
                        models.FieldCondition(
                            key="memory_type",
                            match=models.MatchValue(value=memory_type)
                        )
                    )
            
            # Add any additional filters from filter_params
            if filter_params:
                for key, value in filter_params.items():
                    if key == "min_quality" and value > 0:
                        filter_conditions.append(
                            models.FieldCondition(
                                key="quality",
                                range=models.Range(
                                    gte=float(value)
                                )
                            )
                        )
                    elif key == "entity_type":
                        filter_conditions.append(
                            models.FieldCondition(
                                key="entity_type",
                                match=models.MatchValue(value=value)
                            )
                        )
                    elif key == "user_id":
                        filter_conditions.append(
                            models.FieldCondition(
                                key="user_id",
                                match=models.MatchValue(value=value)
                            )
                        )
            
            # Build the search filter
            search_filter = None
            if filter_conditions:
                search_filter = models.Filter(
                    must=filter_conditions
                )
            
            # Execute the search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter,  # Changed from 'filter' to 'query_filter'
                with_payload=True,
                with_vectors=False
            )
            
            # Format and filter results
            results = []
            for hit in search_results:
                # Convert score to cosine similarity (0-1 range)
                score = hit.score if hasattr(hit, "score") else 0.0
                
                # Skip if below relevance cutoff
                if relevance_cutoff > 0 and score < relevance_cutoff:
                    continue
                    
                payload = hit.payload
                text = payload.get("text", "")
                metadata = payload.get("metadata", {})
                
                # Add memory record citation if not present
                if "(Memory record:" not in text:
                    text = f"{text} (Memory record: {hit.id})"
                
                results.append({
                    "id": hit.id,
                    "text": text,
                    "metadata": metadata,
                    "score": score,
                    "memory_type": payload.get("memory_type")
                })
            
            return results
            
        except Exception as e:
            self._log_verbose(f"Error searching memory: {e}", logging.ERROR)
            raise

    def store_short_term(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Store memory in short-term memory collection"""
        return self.store_memory(text, "short_term", metadata)
        
    def store_long_term(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Store memory in long-term memory collection"""
        return self.store_memory(text, "long_term", metadata)
        
    def store_entity(self, name: str, type_: str, desc: str, relations: str) -> str:
        """Store entity in entity memory collection"""
        text = f"Entity {name}({type_}): {desc} | relationships: {relations}"
        metadata = {
            "entity_type": type_,
            "entity_name": name,
            "category": "entity"
        }
        return self.store_memory(text, "entity", metadata)
        
    def store_user_memory(self, user_id: str, text: str, metadata: Dict[str, Any] = None) -> str:
        """Store memory for a specific user"""
        metadata = metadata or {}
        metadata["user_id"] = user_id
        return self.store_memory(text, "user", metadata)

    def search_short_term(
        self,
        query: str,
        limit: int = 5,
        min_quality: float = 0.0,
        relevance_cutoff: float = 0.0,
        rerank: bool = False
    ) -> List[Dict[str, Any]]:
        """Search short-term memory"""
        filter_params = {}
        if min_quality > 0:
            filter_params["min_quality"] = min_quality
            
        return self.search_memory(
            query=query,
            memory_type="short_term",
            filter_params=filter_params,
            limit=limit,
            relevance_cutoff=relevance_cutoff
        )
        
    def search_long_term(
        self,
        query: str,
        limit: int = 5,
        min_quality: float = 0.0,
        relevance_cutoff: float = 0.0,
        rerank: bool = False
    ) -> List[Dict[str, Any]]:
        """Search long-term memory"""
        filter_params = {}
        if min_quality > 0:
            filter_params["min_quality"] = min_quality
            
        return self.search_memory(
            query=query,
            memory_type="long_term",
            filter_params=filter_params,
            limit=limit,
            relevance_cutoff=relevance_cutoff
        )

    def search_entity(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 5,
        rerank: bool = False
    ) -> List[Dict[str, Any]]:
        """Search entity memory"""
        filter_params = {"category": "entity"}
        if entity_type:
            filter_params["entity_type"] = entity_type
            
        return self.search_memory(
            query=query,
            memory_type="entity",
            filter_params=filter_params,
            limit=limit
        )

    def search_user_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        rerank: bool = False
    ) -> List[Dict[str, Any]]:
        """Search memories for a specific user"""
        filter_params = {"user_id": user_id}
            
        return self.search_memory(
            query=query,
            memory_type="user",
            filter_params=filter_params,
            limit=limit
        )

    def reset_short_term(self):
        """Remove all short-term memories"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="memory_type",
                                match=models.MatchValue(value="short_term")
                            )
                        ]
                    )
                )
            )
            self._log_verbose("Short-term memory reset successfully")
        except Exception as e:
            self._log_verbose(f"Error resetting short-term memory: {e}", logging.ERROR)
            raise

    def reset_long_term(self):
        """Remove all long-term memories"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="memory_type",
                                match=models.MatchValue(value="long_term")
                            )
                        ]
                    )
                )
            )
            self._log_verbose("Long-term memory reset successfully")
        except Exception as e:
            self._log_verbose(f"Error resetting long-term memory: {e}", logging.ERROR)
            raise

    def reset_entities(self):
        """Remove all entity memories"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="memory_type",
                                match=models.MatchValue(value="entity")
                            )
                        ]
                    )
                )
            )
            self._log_verbose("Entity memory reset successfully")
        except Exception as e:
            self._log_verbose(f"Error resetting entity memory: {e}", logging.ERROR)
            raise

    def reset_user_memory(self):
        """Remove all user memories"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="memory_type",
                                match=models.MatchValue(value="user")
                            )
                        ]
                    )
                )
            )
            self._log_verbose("User memory reset successfully")
        except Exception as e:
            self._log_verbose(f"Error resetting user memory: {e}", logging.ERROR)
            raise
            
    def reset_all(self):
        """Remove all memories"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter()
                )
            )
            self._log_verbose("All memory reset successfully")
        except Exception as e:
            self._log_verbose(f"Error resetting all memory: {e}", logging.ERROR)
            raise
            
    def get_all_memories(self) -> List[Dict[str, Any]]:
        """Get all memories with pagination"""
        try:
            # Use scroll API to get all points
            scroll_results = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            points = scroll_results[0]
            
            for point in points:
                payload = point.payload
                text = payload.get("text", "")
                memory_type = payload.get("memory_type", "unknown")
                
                results.append({
                    "id": point.id,
                    "text": text,
                    "metadata": payload.get("metadata", {}),
                    "created_at": payload.get("created_at"),
                    "type": memory_type
                })
                
            return results
            
        except Exception as e:
            self._log_verbose(f"Error getting all memories: {e}", logging.ERROR)
            raise
