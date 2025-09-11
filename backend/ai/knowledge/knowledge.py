import os
import logging
import uuid
import time
from datetime import datetime
from .chunking import Chunking
from functools import cached_property
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

logger = logging.getLogger(__name__)

class GitMeshMemory:
    """GitMesh AI hybrid memory using Supabase + Qdrant."""
    
    def __init__(self, config):
        self.config = config
        self._init_hybrid_memory()
    
    def _init_hybrid_memory(self):
        """Initialize hybrid memory with Supabase and Qdrant."""
        try:
            from ..memory.supabase_db import SupabaseMemory
            from ..memory.qdrant_db import QdrantMemory
            
            # Initialize Supabase for structured data
            supabase_config = {
                'supabase_url': os.getenv('SUPABASE_URL'),
                'supabase_key': os.getenv('SUPABASE_ANON_KEY'),
                'supabase_service_key': os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            }
            self.supabase_memory = SupabaseMemory(config=supabase_config)
            
            # Initialize Qdrant for vector search
            qdrant_config = {
                'url': os.getenv('QDRANT_URL'),
                'api_key': os.getenv('QDRANT_API_KEY'),
                'collection_name': os.getenv('QDRANT_COLLECTION_NAME', 'gitmesh-knowledge')
            }
            self.qdrant_memory = QdrantMemory(config=qdrant_config)
            
        except Exception as e:
            logger.error(f"Failed to initialize GitMesh hybrid memory: {e}")
            raise
    
    def add(self, messages, user_id=None, agent_id=None, run_id=None, metadata=None):
        """Add memory to both Supabase and Qdrant."""
        try:
            # Handle different message formats
            if isinstance(messages, list):
                content = "\n".join([msg.get("content", str(msg)) if isinstance(msg, dict) else str(msg) for msg in messages])
            else:
                content = str(messages)
            
            # Store in both systems using their respective methods
            # Store in Supabase (structured data)
            supabase_id = self.supabase_memory.store_long_term(content, metadata=metadata or {})
            
            # Store in Qdrant (vector search)
            qdrant_id = self.qdrant_memory.store_memory(
                content, 
                memory_type="knowledge", 
                metadata=metadata or {}
            )
            
            return [{
                "id": supabase_id,
                "memory": content,
                "event": "ADD",
                "qdrant_id": qdrant_id
            }]
            
        except Exception as e:
            logger.error(f"Error adding memory to GitMesh hybrid store: {e}")
            return []
    
    def search(self, query, user_id=None, agent_id=None, run_id=None, rerank=False, **kwargs):
        """Search memories using Qdrant for vector search."""
        try:
            # Use Qdrant for semantic search
            qdrant_results = self.qdrant_memory.search_memory(
                query, 
                limit=kwargs.get('limit', 10),
                memory_type="knowledge"
            )
            
            # Format results to match expected format
            formatted_results = []
            for result in qdrant_results:
                formatted_results.append({
                    "id": result.get("id", "unknown"),
                    "memory": result.get("text", result.get("content", str(result))),
                    "metadata": result.get("metadata", {}),
                    "score": result.get("score", 1.0)
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching GitMesh hybrid memory: {e}")
            return []
    
    def get_all(self, user_id=None, agent_id=None, run_id=None):
        """Get all memories from Qdrant."""
        try:
            return self.qdrant_memory.get_all_memories()
        except Exception as e:
            logger.error(f"Error getting all memories: {e}")
            return []
    
    def get(self, memory_id):
        """Get a specific memory by ID from Supabase."""
        try:
            # This would need to be implemented in SupabaseMemory
            return {"id": memory_id, "memory": "Memory retrieval by ID not implemented", "metadata": {}}
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return None
    
    def update(self, memory_id, data):
        """Update a memory in both systems."""
        # Note: This would require implementation in both memory systems
        logger.warning("Memory update not fully implemented in hybrid system")
        return False
    
    def delete(self, memory_id):
        """Delete a memory from both systems."""
        # Note: This would require implementation in both memory systems
        logger.warning("Memory deletion not fully implemented in hybrid system")
        return False
    
    def delete_all(self, user_id=None, agent_id=None, run_id=None):
        """Delete all memories from both systems."""
        try:
            # This would need proper implementation
            logger.warning("Delete all not fully implemented in hybrid system")
            return 0
        except Exception as e:
            logger.error(f"Error deleting all memories: {e}")
            return 0
    
    def reset(self):
        """Reset all memories in both systems."""
        try:
            # This would need proper implementation
            logger.warning("Reset not fully implemented in hybrid system")
            return 0
        except Exception as e:
            logger.error(f"Error resetting memories: {e}")
            return 0
    
    def history(self, memory_id):
        """Get the history of changes for a memory."""
        # Supabase can track history if implemented
        return self.get(memory_id)  # Basic implementation

logger = logging.getLogger(__name__)

class Knowledge:
    def __init__(self, config=None, verbose=None):
        self._config = config
        self._verbose = verbose or 0
        
        # Configure logging levels based on verbose setting
        if not self._verbose:
            # Suppress logs from all relevant dependencies
            for logger_name in [
                'supabase', 
                'qdrant_client',
                'openai',
                'httpx'
            ]:
                logging.getLogger(logger_name).setLevel(logging.WARNING)

    @cached_property
    def _deps(self):
        try:
            from markitdown import MarkItDown
            return {
                'markdown': MarkItDown()
            }
        except ImportError:
            raise ImportError(
                "Required packages not installed. Please install markitdown: pip install markitdown"
            )

    @cached_property
    def config(self):
        # Generate unique collection name for each instance (only if not provided in config)
        default_collection = f"test_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        persist_dir = ".gitmesh"

        # Create base config for GitMesh hybrid memory
        base_config = {
            "version": "v1.1",
            "memory_type": "hybrid",  # Use hybrid Supabase + Qdrant
            "supabase": {
                "url": os.getenv('SUPABASE_URL'),
                "key": os.getenv('SUPABASE_ANON_KEY'),
                "service_role_key": os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            },
            "qdrant": {
                "url": os.getenv('QDRANT_URL'),
                "api_key": os.getenv('QDRANT_API_KEY'),
                "collection_name": os.getenv('QDRANT_COLLECTION_NAME', 'gitmesh-knowledge')
            }
        }

        # If config is provided, merge it with base config
        if self._config:
            # Merge version if provided
            if "version" in self._config:
                base_config["version"] = self._config["version"]
            
            # Merge custom configs
            for key in ["supabase", "qdrant", "embedder", "llm"]:
                if key in self._config:
                    base_config[key] = self._config[key]

        return base_config

    @cached_property
    def memory(self):
        # Use GitMesh hybrid memory with Supabase + Qdrant
        try:
            return GitMeshMemory(self.config)
        except Exception as e:
            logger.error(f"Failed to initialize GitMesh hybrid memory: {e}")
            raise e

    @cached_property
    def markdown(self):
        return self._deps['markdown']

    @cached_property
    def chunker(self):
        return Chunking(
            chunker_type='recursive',
            chunk_size=512,
            chunk_overlap=50
        )

    def _log(self, message, level=2):
        """Internal logging helper"""
        if self._verbose and self._verbose >= level:
            logger.info(message)

    def store(self, content, user_id=None, agent_id=None, run_id=None, metadata=None):
        """Store a memory."""
        try:
            if isinstance(content, str):
                if any(content.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.txt']):
                    self._log(f"Content appears to be a file path, processing file: {content}")
                    return self.add(content, user_id=user_id, agent_id=agent_id, run_id=run_id, metadata=metadata)
                
                content = content.strip()
                if not content:
                    return []
                
            # Try new API format first, fall back to old format for backward compatibility
            try:
                # Convert content to messages format for mem0 API compatibility
                if isinstance(content, str):
                    messages = [{"role": "user", "content": content}]
                else:
                    messages = content if isinstance(content, list) else [{"role": "user", "content": str(content)}]
                
                result = self.memory.add(messages=messages, user_id=user_id, agent_id=agent_id, run_id=run_id, metadata=metadata)
            except TypeError as e:
                # Fallback to old API format if messages parameter is not supported
                if "unexpected keyword argument" in str(e) or "positional argument" in str(e):
                    self._log(f"Falling back to legacy API format due to: {e}")
                    result = self.memory.add(content, user_id=user_id, agent_id=agent_id, run_id=run_id, metadata=metadata)
                else:
                    raise
            self._log(f"Store operation result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error storing content: {str(e)}")
            return []

    def get_all(self, user_id=None, agent_id=None, run_id=None):
        """Retrieve all memories."""
        return self.memory.get_all(user_id=user_id, agent_id=agent_id, run_id=run_id)

    def get(self, memory_id):
        """Retrieve a specific memory by ID."""
        return self.memory.get(memory_id)

    def search(self, query, user_id=None, agent_id=None, run_id=None, rerank=None, **kwargs):
        """Search for memories related to a query.
        
        Args:
            query: The search query string
            user_id: Optional user ID for user-specific search
            agent_id: Optional agent ID for agent-specific search  
            run_id: Optional run ID for run-specific search
            rerank: Whether to use Mem0's advanced reranking. If None, uses config default
            **kwargs: Additional search parameters to pass to Mem0 (keyword_search, filter_memories, etc.)
        
        Returns:
            List of search results, reranked if rerank=True
        """
        # Use config default if rerank not explicitly specified
        if rerank is None:
            rerank = self.config.get("reranker", {}).get("default_rerank", False)
        
        return self.memory.search(query, user_id=user_id, agent_id=agent_id, run_id=run_id, rerank=rerank, **kwargs)

    def update(self, memory_id, data):
        """Update a memory."""
        return self.memory.update(memory_id, data)

    def history(self, memory_id):
        """Get the history of changes for a memory."""
        return self.memory.history(memory_id)

    def delete(self, memory_id):
        """Delete a memory."""
        self.memory.delete(memory_id)

    def delete_all(self, user_id=None, agent_id=None, run_id=None):
        """Delete all memories."""
        self.memory.delete_all(user_id=user_id, agent_id=agent_id, run_id=run_id)

    def reset(self):
        """Reset all memories."""
        self.memory.reset()

    def normalize_content(self, content):
        """Normalize content for consistent storage."""
        # Example normalization: strip whitespace, convert to lowercase
        return content.strip().lower()

    def add(self, file_path, user_id=None, agent_id=None, run_id=None, metadata=None):
        """Read file content and store it in memory.
        
        Args:
            file_path: Can be:
                - A string path to local file
                - A URL string
                - A list containing file paths and/or URLs
        """
        if isinstance(file_path, (list, tuple)):
            results = []
            for path in file_path:
                result = self._process_single_input(path, user_id, agent_id, run_id, metadata)
                results.extend(result.get('results', []))
            return {'results': results, 'relations': []}
        
        return self._process_single_input(file_path, user_id, agent_id, run_id, metadata)

    def _process_single_input(self, input_path, user_id=None, agent_id=None, run_id=None, metadata=None):
        """Process a single input which can be a file path or URL."""
        try:
            # Define supported file extensions
            DOCUMENT_EXTENSIONS = {
                'document': ('.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx'),
                'media': ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.mp3', '.wav', '.ogg', '.m4a'),
                'text': ('.txt', '.csv', '.json', '.xml', '.md', '.html', '.htm'),
                'archive': '.zip'
            }

            # Check if input is URL
            if isinstance(input_path, str) and (input_path.startswith('http://') or input_path.startswith('https://')):
                self._log(f"Processing URL: {input_path}")
                raise NotImplementedError("URL processing not yet implemented")

            # Check if input ends with any supported extension
            is_supported_file = any(input_path.lower().endswith(ext) 
                                  for exts in DOCUMENT_EXTENSIONS.values()
                                  for ext in (exts if isinstance(exts, tuple) else (exts,)))
            
            if is_supported_file:
                self._log(f"Processing as file path: {input_path}")
                if not os.path.exists(input_path):
                    logger.error(f"File not found: {input_path}")
                    raise FileNotFoundError(f"File not found: {input_path}")
                
                file_ext = '.' + input_path.lower().split('.')[-1]  # Get extension reliably
                
                # Process file based on type
                if file_ext in DOCUMENT_EXTENSIONS['text']:
                    with open(input_path, 'r', encoding='utf-8') as file:
                        content = file.read().strip()
                    if not content:
                        raise ValueError("Empty text file")
                    memories = [self.normalize_content(content)]
                else:
                    # Use MarkItDown for documents and media
                    result = self.markdown.convert(input_path)
                    content = result.text_content
                    if not content:
                        raise ValueError("No content could be extracted from file")
                    chunks = self.chunker.chunk(content)
                    memories = [chunk.text.strip() if hasattr(chunk, 'text') else str(chunk).strip() 
                              for chunk in chunks if chunk]

                # Set metadata for file
                if not metadata:
                    metadata = {}
                metadata['file_type'] = file_ext.lstrip('.')
                metadata['filename'] = os.path.basename(input_path)
            else:
                # Treat as raw text content only if no file extension
                memories = [self.normalize_content(input_path)]

            # Create progress display
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                transient=True
            )

            # Store memories with progress bar
            all_results = []
            with progress:
                store_task = progress.add_task(f"Adding to Knowledge from {os.path.basename(input_path)}", total=len(memories))
                for memory in memories:
                    if memory:
                        memory_result = self.store(memory, user_id=user_id, agent_id=agent_id, 
                                                 run_id=run_id, metadata=metadata)
                        if memory_result:
                            # Handle both dict and list formats for backward compatibility
                            if isinstance(memory_result, dict):
                                all_results.extend(memory_result.get('results', []))
                            elif isinstance(memory_result, list):
                                all_results.extend(memory_result)
                            else:
                                # Log warning for unexpected types but don't break
                                import logging
                                logging.warning(f"Unexpected memory_result type: {type(memory_result)}, skipping")
                        progress.advance(store_task)

            return {'results': all_results, 'relations': []}

        except Exception as e:
            logger.error(f"Error processing input {input_path}: {str(e)}", exc_info=True)
            raise