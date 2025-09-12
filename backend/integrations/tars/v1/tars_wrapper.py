"""
TARS v1 GitMesh Integration Wrapper
==================================

Enhanced TARS wrapper with GitMesh infrastructure integration:
- Supabase database integration
- Qdrant vector store integration
- GitMesh session management
- Enhanced chunking and indexing
- Memory and retrieval with GitMesh backend
"""

import os
import uuid
import json
import time
import asyncio
import logging
import hashlib
import sys
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system environment variables

from ai.session import Session
from ai.llm.llm import LLM
from ai.memory.memory import Memory
from ai.knowledge.knowledge import Knowledge

from .main import TarsMain
from .session import TarsSession

logger = logging.getLogger(__name__)

# Safe imports to avoid import errors
try:
    from .indexing.core import CodebaseIndexer
    from .indexing.chunking import EnhancedChunker, create_adaptive_chunker
    INDEXER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"TARS indexing components not available: {e}")
    CodebaseIndexer = None
    EnhancedChunker = None
    create_adaptive_chunker = None
    INDEXER_AVAILABLE = False

# GitIngest import for intelligent repository analysis
try:
    from .gitingest_tool import GitIngestTool
    GITINGEST_AVAILABLE = True
except ImportError as e:
    logger.warning(f"GitIngest tool not available: {e}")
    GitIngestTool = None
    GITINGEST_AVAILABLE = False

# GitMesh imports (with safe imports)
try:
    from config.settings import get_settings
    from config.database import get_database_manager
    settings = get_settings()
    db_manager = get_database_manager()
    GITMESH_AVAILABLE = True
except ImportError:
    logger.warning("GitMesh components not available")
    settings = None
    db_manager = None
    GITMESH_AVAILABLE = False

try:
    # Use GitMesh Qdrant integration
    from ai.memory.qdrant_db import QdrantMemory
    QDRANT_AVAILABLE = True
    logger.info("GitMesh Qdrant integration available")
except (ImportError, Exception) as e:
    logger.warning(f"Qdrant integration not available: {e}")
    QdrantMemory = None
    QDRANT_AVAILABLE = False


class GitMeshTarsWrapper:
    """
    GitMesh integration wrapper for TARS v1.
    
    This class bridges TARS v1 with GitMesh infrastructure:
    - Database integration with Supabase
    - Vector store integration with Qdrant
    - Session management
    - Memory management
    - Error handling and logging
    """
    
    def __init__(
        self,
        user_id: str,
        project_id: str,
        repository_id: Optional[str] = None,
        branch: Optional[str] = None
    ):
        self.user_id = user_id
        self.project_id = project_id
        self.repository_id = repository_id
        self.branch = branch
        
        # Get GitMesh settings (with fallback)
        if GITMESH_AVAILABLE and settings:
            self.settings = settings
            self.db_manager = db_manager
        else:
            self.settings = None
            self.db_manager = None
            logger.warning("Running without GitMesh database integration")
        
        # Initialize Qdrant vector store
        if QDRANT_AVAILABLE and QdrantMemory:
            try:
                self.qdrant_db = QdrantMemory()
                logger.info("Qdrant vector store initialized")
            except Exception as e:
                self.qdrant_db = None
                logger.warning(f"Failed to initialize Qdrant vector store: {e}")
        else:
            self.qdrant_db = None
            logger.warning("Qdrant vector store not available")
        
        # TARS instance
        self.tars: Optional[TarsMain] = None
        self.session_id = f"gitmesh_tars_{user_id}_{project_id}_{int(datetime.now().timestamp())}"
        
        # Memory system (use Qdrant for now)
        self.memory = self.qdrant_db
        
        # Configuration
        self.memory_config = self._create_memory_config()
        self.knowledge_config = self._create_knowledge_config()
        self.llm_config = self._create_llm_config()
        
        # Repository intelligence system
        self.repo_knowledge_cache = {}
        self.repo_metadata = {}
        self.gitingest_tool = None
        self.knowledge_base_hash = None
        self.last_repo_analysis = {}
        
        # Initialize GitIngest if available
        if GITINGEST_AVAILABLE:
            self.gitingest_tool = GitIngestTool(
                github_token=os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
            )
        
        logger.info(f"GitMeshTarsWrapper initialized for user {user_id}, project {project_id}")
    
    def create_session(self) -> Dict[str, Any]:
        """Create and return session configuration for TARS"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "repository_id": self.repository_id,
            "branch": self.branch,
            "memory_config": self.memory_config,
            "knowledge_config": self.knowledge_config,
            "llm_config": self.llm_config,
            "gitmesh_integration": {
                "database_available": self.db_manager is not None,
                "vector_store_available": self.qdrant_db is not None,
                "supabase_available": GITMESH_AVAILABLE
            }
        }
    
    def _create_memory_config(self) -> Dict[str, Any]:
        """Create memory configuration using GitMesh infrastructure"""
        base_config = {
            "provider": "hybrid",  # Use GitMesh hybrid memory
            "use_embedding": True,
            "embedding_provider": "sentence_transformers",
            "quality_scoring": True,
            "advanced_memory": True,
        }
        
        if GITMESH_AVAILABLE and self.settings:
            # Add Supabase integration
            base_config.update({
                "supabase": {
                    "url": self.settings.supabase_url,
                    "anon_key": self.settings.supabase_anon_key,
                    "service_role_key": self.settings.supabase_service_role_key,
                    "table_prefix": f"tars_{self.user_id}_{self.project_id}"
                }
            })
        
        # Local fallback
        base_config.update({
            "local": {
                "short_db": f".tars/{self.project_id}/short_term.db",
                "long_db": f".tars/{self.project_id}/long_term.db", 
                "entity_db": f".tars/{self.project_id}/entity.db",
                "rag_db_path": f".tars/{self.project_id}/chroma_db"
            }
        })
        
        return base_config
    
    def _create_knowledge_config(self) -> Dict[str, Any]:
        """Create knowledge configuration using GitMesh Qdrant"""
        collection_name = f"gitmesh_tars_knowledge_{self.user_id}_{self.project_id}"
        
        base_config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": collection_name,
                    "vector_size": 384,  # BGE-small embedding dimension
                    "distance": "Cosine",
                    "on_disk_payload": True,
                    "replication_factor": 1
                }
            },
            "embedding": {
                "provider": "sentence_transformers",
                "model": "BAAI/bge-small-en-v1.5",
                "device": "cpu",
                "batch_size": 32
            },
            "chunking": {
                "strategy": "adaptive",
                "max_chunk_size": 1000,
                "overlap": 200,
                "respect_document_boundaries": True
            }
        }
        
        if GITMESH_AVAILABLE and self.settings:
            # Use GitMesh Qdrant settings
            base_config["vector_store"]["config"].update({
                "url": self.settings.qdrant_url_from_env,
                "api_key": self.settings.qdrant_connection_api_key,
            })
        else:
            # Local fallback
            base_config["vector_store"]["config"].update({
                "url": "http://localhost:6333",
                "api_key": None,
            })
        
        return base_config
    
    def _create_llm_config(self) -> Dict[str, Any]:
        """Create LLM configuration using dynamic model detection"""
        try:
            # Import here to avoid circular imports
            import sys
            sys.path.append('backend')
            from core.context_manager import get_default_model
            
            # Get dynamic model configuration
            model_info = get_default_model()
            model_name = model_info['model']
            base_url = model_info['base_url']
            api_key_env = model_info['api_key_env']
            
            # Get API key from the appropriate environment variable
            api_key = os.getenv(api_key_env) or os.getenv("MODEL_KEY")
            
        except Exception:
            # Fallback to environment variables
            model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            api_key_env = "OPENAI_API_KEY"
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("MODEL_KEY")
        
        # Create unified configuration (excluding internal parameters)
        config = {
            "model": model_name,
            "temperature": 0.7,
            "max_tokens": 4000,
            "stream": True,
            "metrics": True,
            "rate_limit": {
                "requests_per_minute": 50,
                "tokens_per_minute": 40000
            }
        }
        
        # Add API key only if available
        if api_key:
            config["api_key"] = api_key
            
        # Add base URL only if available and not None
        if base_url:
            config["base_url"] = base_url
            
        # Add OpenAI organization if available
        openai_org = os.getenv("OPENAI_ORG_ID")
        if openai_org:
            config["organization"] = openai_org
            
        return config
    
    async def initialize(self) -> bool:
        """Initialize TARS with GitMesh integration"""
        try:
            logger.info(f"Initializing GitMesh TARS wrapper for session {self.session_id}")
            
            # Ensure vector collection exists if Qdrant is available
            if QDRANT_AVAILABLE and self.qdrant_db:
                await self._ensure_vector_collection()
            
            # Create TARS instance
            self.tars = TarsMain(
                user_id=self.user_id,
                project_id=self.project_id,
                memory_config=self.memory_config,
                knowledge_config=self.knowledge_config,
                llm_config=self.llm_config,
                verbose=True
            )
            
            # Initialize TARS
            success = await self.tars.initialize()
            
            if success:
                logger.info(f"GitMesh TARS wrapper initialized successfully")
                # Store session info in database if available
                if GITMESH_AVAILABLE and self.db_manager:
                    await self._store_session_info()
                return True
            else:
                logger.error("Failed to initialize TARS")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing GitMesh TARS wrapper: {e}")
            return False
    
    async def _ensure_vector_collection(self):
        """Ensure Qdrant collection exists for this project"""
        try:
            if not (QDRANT_AVAILABLE and self.qdrant_db):
                return
                
            collection_name = self.knowledge_config["vector_store"]["config"]["collection_name"]
            
            # Check if collection exists
            if hasattr(self.qdrant_db, 'collection_exists'):
                if not await self.qdrant_db.collection_exists(collection_name):
                    await self.qdrant_db._create_enhanced_collection()
                    logger.info(f"Created Qdrant collection: {collection_name}")
            elif hasattr(self.qdrant_db, 'initialize'):
                await self.qdrant_db.initialize()
                logger.info(f"Initialized Qdrant client for collection: {collection_name}")
            
        except Exception as e:
            logger.warning(f"Could not ensure vector collection: {e}")
    
    async def _store_session_info(self):
        """Store session information in GitMesh database"""
        try:
            if not (GITMESH_AVAILABLE and self.db_manager):
                return
                
            session_data = {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "project_id": self.project_id,
                "repository_id": self.repository_id,
                "branch": self.branch,
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "configuration": {
                    "memory_config": self.memory_config,
                    "knowledge_config": self.knowledge_config,
                    "llm_config": {k: v for k, v in self.llm_config.items() if k != "api_key"}
                }
            }
            
            # Store in database if available
            if hasattr(self.db_manager, 'store_session'):
                await self.db_manager.store_session(session_data)
            
            logger.info(f"Stored session info for {self.session_id}")
            
        except Exception as e:
            logger.warning(f"Could not store session info: {e}")
    
    async def analyze_project(
        self,
        web_urls: Optional[List[str]] = None,
        repositories: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        data_files: Optional[List[str]] = None,
        github_repos: Optional[List[str]] = None,
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze project using TARS with GitMesh integration
        """
        if not self.tars:
            raise RuntimeError("TARS not initialized. Call initialize() first.")
        
        try:
            logger.info(f"Starting project analysis for {self.project_id}")
            
            # Add GitMesh context to analysis options
            enhanced_options = analysis_options or {}
            enhanced_options.update({
                "gitmesh_context": {
                    "user_id": self.user_id,
                    "project_id": self.project_id,
                    "repository_id": self.repository_id,
                    "branch": self.branch,
                    "session_id": self.session_id
                },
                "database_integration": GITMESH_AVAILABLE,
                "vector_store_integration": QDRANT_AVAILABLE,
                "quality_scoring": True
            })
            
            # Execute TARS analysis
            results = await self.tars.analyze_project(
                web_urls=web_urls,
                repositories=repositories,
                documents=documents,
                data_files=data_files,
                github_repos=github_repos,
                analysis_options=enhanced_options
            )
            
            # Post-process results for GitMesh
            enhanced_results = await self._post_process_results(results)
            
            # Store results in GitMesh database if available
            if GITMESH_AVAILABLE and self.db_manager:
                await self._store_analysis_results(enhanced_results)
            
            logger.info(f"Project analysis completed for {self.project_id}")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error in project analysis: {e}")
            raise
    
    async def _post_process_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process TARS results for GitMesh integration"""
        try:
            enhanced_results = {
                "session_id": self.session_id,
                "project_id": self.project_id,
                "user_id": self.user_id,
                "timestamp": datetime.now().isoformat(),
                "tars_results": results,
                "gitmesh_metadata": {
                    "vector_collection": self.knowledge_config["vector_store"]["config"]["collection_name"],
                    "memory_provider": self.memory_config["provider"],
                    "embedding_model": self.knowledge_config["embedding"]["model"],
                    "database_integration": GITMESH_AVAILABLE,
                    "vector_store_integration": QDRANT_AVAILABLE
                }
            }
            
            # Add workflow summaries
            workflow_summaries = []
            for workflow_name, workflow_result in results.items():
                if hasattr(workflow_result, '__dict__'):
                    summary = {
                        "workflow_name": workflow_name,
                        "status": getattr(workflow_result, 'status', 'unknown'),
                        "tasks_completed": getattr(workflow_result, 'tasks_completed', 0),
                        "tasks_failed": getattr(workflow_result, 'tasks_failed', 0),
                        "execution_time": getattr(workflow_result, 'execution_time', 0.0)
                    }
                    workflow_summaries.append(summary)
            
            enhanced_results["workflow_summaries"] = workflow_summaries
            
            # Calculate statistics
            total_tasks = sum(s.get("tasks_completed", 0) + s.get("tasks_failed", 0) for s in workflow_summaries)
            successful_tasks = sum(s.get("tasks_completed", 0) for s in workflow_summaries)
            
            enhanced_results["statistics"] = {
                "total_workflows": len(workflow_summaries),
                "successful_workflows": len([s for s in workflow_summaries if s.get("status") == "success"]),
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "success_rate": successful_tasks / max(total_tasks, 1),
                "total_execution_time": sum(s.get("execution_time", 0) for s in workflow_summaries)
            }
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error post-processing results: {e}")
            return {"error": str(e), "original_results": results}
    
    async def _store_analysis_results(self, results: Dict[str, Any]):
        """Store analysis results in GitMesh database"""
        try:
            if not (GITMESH_AVAILABLE and self.db_manager):
                return
                
            # Store in main results table
            result_record = {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "project_id": self.project_id,
                "repository_id": self.repository_id,
                "branch": self.branch,
                "results": results,
                "created_at": datetime.now().isoformat(),
                "status": "completed"
            }
            
            if hasattr(self.db_manager, 'store_analysis_results'):
                await self.db_manager.store_analysis_results(result_record)
            
            logger.info(f"Stored analysis results for session {self.session_id}")
            
        except Exception as e:
            logger.warning(f"Could not store analysis results: {e}")
    
    async def process_query(self, query: str) -> str:
        """Process a single query using TARS"""
        if not self.tars:
            raise RuntimeError("TARS not initialized. Call initialize() first.")
        
        try:
            # Add GitMesh context to query
            enhanced_query = f"""
            Context: This query is from GitMesh user {self.user_id} for project {self.project_id}.
            Repository: {self.repository_id or 'N/A'}
            Branch: {self.branch or 'N/A'}
            
            Query: {query}
            
            Please provide a comprehensive response using the available knowledge base and analysis results.
            """
            
            response = await self.tars.process_query(enhanced_query)
            
            # Log query for analytics if database is available
            if GITMESH_AVAILABLE and self.db_manager:
                await self._log_query(query, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"Sorry, I encountered an error processing your query: {str(e)}"
    
    async def _log_query(self, query: str, response: str):
        """Log query for analytics and improvement"""
        try:
            if not (GITMESH_AVAILABLE and self.db_manager):
                return
                
            query_log = {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "project_id": self.project_id,
                "query": query,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            if hasattr(self.db_manager, 'log_query'):
                await self.db_manager.log_query(query_log)
            
        except Exception as e:
            logger.warning(f"Could not log query: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get TARS system status with GitMesh integration info"""
        try:
            status = {
                "session_id": self.session_id,
                "project_id": self.project_id,
                "user_id": self.user_id,
                "initialized": self.tars is not None,
                "timestamp": datetime.now().isoformat(),
                "gitmesh_integration": {
                    "available": GITMESH_AVAILABLE,
                    "database_available": GITMESH_AVAILABLE and self.db_manager is not None,
                    "vector_store_available": QDRANT_AVAILABLE and self.qdrant_db is not None,
                    "collection_name": self.knowledge_config["vector_store"]["config"]["collection_name"],
                    "memory_provider": self.memory_config["provider"]
                }
            }
            
            if self.tars:
                tars_status = self.tars.get_system_status()
                status.update(tars_status)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e), "session_id": self.session_id}
    
    async def shutdown(self):
        """Shutdown TARS and cleanup resources"""
        try:
            logger.info(f"Shutting down GitMesh TARS wrapper for session {self.session_id}")
            
            if self.tars:
                await self.tars.shutdown()
                self.tars = None
            
            # Update session status in database if available
            if GITMESH_AVAILABLE and self.db_manager:
                await self._update_session_status("shutdown")
            
            logger.info(f"GitMesh TARS wrapper shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def _update_session_status(self, status: str):
        """Update session status in database"""
        try:
            if not (GITMESH_AVAILABLE and self.db_manager):
                return
                
            if hasattr(self.db_manager, 'update_session_status'):
                await self.db_manager.update_session_status(self.session_id, status)
            
        except Exception as e:
            logger.warning(f"Could not update session status: {e}")
    
    async def process_chat_message(self, message: str, context: Dict[str, Any] = None, session_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a chat message using TARS v1 intelligent conversation with full knowledge base integration.
        
        This method:
        1. Uses the current knowledge base built from imports
        2. Maintains session-specific context in Supabase/Qdrant
        3. Leverages all TARS workflows for intelligent responses
        4. Stores conversation for future context
        5. Processes files sent with the message context
        """
        try:
            logger.info(f"[TARS DEBUG] Processing chat message: {message[:100]}...")
            logger.info(f"[TARS DEBUG] Context received: {context}")
            if context and context.get("files"):
                logger.info(f"[TARS DEBUG] Files in context: {len(context.get('files', []))} files")
            
            # Initialize TARS if not already done
            if not self.tars:
                await self.initialize()
            
            # If TARS is still not available, use intelligent fallback
            if not self.tars:
                logger.warning("[TARS DEBUG] TARS not available, using fallback")
                return await self._fallback_chat_processing(message, context, session_history)
            
            # Process any files sent with the message context immediately
            if context and context.get("files"):
                logger.info("[TARS DEBUG] Processing context files...")
                await self._process_context_files(context["files"])
                logger.info("[TARS DEBUG] Context files processed")
            
            # Build comprehensive session context from knowledge base
            session_context = await self._build_session_context(message, context, session_history)
            
            # Check if we need to analyze the current repository
            await self._check_and_update_repository_knowledge(message)
            
            # Enhanced query with knowledge base and session context
            enhanced_query = await self._enhance_query_with_knowledge(message, session_context)
            
            # Process through TARS system with full workflow support
            response = await self.tars.process_query(enhanced_query)
            
            # Extract and structure the response
            structured_response = await self._structure_tars_response(response, session_context)
            
            # Store conversation in Supabase and update Qdrant embeddings
            await self._store_conversation_with_context(message, structured_response, session_context)
            
            return structured_response
            
        except Exception as e:
            logger.error(f"Error processing chat message through TARS: {e}")
            return await self._generate_intelligent_fallback_response(message, context, str(e))
    
    async def _process_context_files(self, files: List[Dict[str, Any]]) -> None:
        """Process files sent with the message context and add them to the knowledge base immediately."""
        try:
            logger.info(f"[TARS DEBUG] Processing {len(files)} files from message context")
            
            for i, file_data in enumerate(files):
                try:
                    # Extract file information
                    file_path = file_data.get("path", "unknown_file")
                    file_content = file_data.get("content", "")
                    file_branch = file_data.get("branch", "main")
                    repository_id = file_data.get("repository_id", self.repository_id or "unknown")
                    
                    # Ensure file_content is a string
                    if not isinstance(file_content, str):
                        logger.warning(f"[TARS DEBUG] File content is not a string, converting: {type(file_content)}")
                        file_content = str(file_content) if file_content is not None else ""
                    
                    logger.info(f"[TARS DEBUG] File {i+1}: {file_path}")
                    logger.info(f"[TARS DEBUG] Content length: {len(file_content)}")
                    logger.info(f"[TARS DEBUG] Content preview: {file_content[:200] if len(file_content) > 200 else file_content}...")
                    
                    if not file_content or file_content == "Loading...":
                        logger.warning(f"[TARS DEBUG] Skipping file {file_path} - no content available")
                        continue
                    
                    # Create metadata for the file
                    metadata = {
                        "source_type": "user_uploaded_file",
                        "file_path": file_path,
                        "branch": file_branch,
                        "repository_id": repository_id,
                        "session_id": self.session_id,
                        "user_id": self.user_id,
                        "timestamp": datetime.now().isoformat(),
                        "processing_context": "chat_message"
                    }
                    
                    # Process the file content and store in knowledge base
                    if self.qdrant_db:
                        # Store the full file content
                        memory_id = self.qdrant_db.store_memory(
                            text=file_content,
                            memory_type="knowledge",
                            metadata=metadata
                        )
                        logger.info(f"Stored file {file_path} in knowledge base with ID: {memory_id}")
                        
                        # Also create a summary entry if the file is large
                        if len(file_content) > 2000:
                            try:
                                summary_start = file_content[:500] if len(file_content) > 500 else file_content
                                summary_end = file_content[-500:] if len(file_content) > 500 else ""
                                summary = summary_start + ("\n...\n" + summary_end if summary_end else "")
                                summary_metadata = {**metadata, "content_type": "summary"}
                                self.qdrant_db.store_memory(
                                    text=f"File: {file_path}\nSummary: {summary}",
                                    memory_type="knowledge",
                                    metadata=summary_metadata
                                )
                            except Exception as summary_error:
                                logger.warning(f"Could not create summary for {file_path}: {summary_error}")
                    
                    # Also store in Supabase if available
                    if self.memory:
                        try:
                            self.memory.store(
                                text=file_content,
                                metadata=metadata,
                                memory_type="file_context"
                            )
                        except Exception as e:
                            logger.warning(f"Could not store file in Supabase memory: {e}")
                    
                    logger.info(f"Successfully processed file: {file_path} ({len(file_content)} chars)")
                    
                except Exception as file_error:
                    logger.error(f"Error processing individual file {file_data.get('path', 'unknown')}: {file_error}")
                    continue
            
            logger.info(f"Completed processing {len(files)} context files")
            
        except Exception as e:
            logger.error(f"Error in _process_context_files: {e}")
            # Don't raise here - we want chat to continue even if file processing fails
    
    async def import_and_build_knowledge(
        self, 
        source_type: str,
        content: Any,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Import content and build/update knowledge base using TARS v1 comprehensive analysis.
        
        Supports all import types:
        - Files (documents, code, data)
        - Repositories (GitHub URLs, Git repos)
        - Web content (URLs, articles)
        - Text content (direct input)
        - GitHub repositories (owner/repo format)
        """
        try:
            if not self.tars:
                await self.create_session()
            
            logger.info(f"Importing {source_type} content and building knowledge base with TARS v1")
            
            # Prepare comprehensive import configuration for TARS
            import_config = await self._prepare_comprehensive_import_config(source_type, content, metadata)
            
            # Initialize TARS if not already done
            if not self.tars:
                await self.initialize()
            
            # Use TARS analyze_project for comprehensive knowledge building
            # This leverages all 6 TARS functions: acquisition, analysis, conversation workflows
            if self.tars:
                try:
                    analysis_results = await self.tars.analyze_project(**import_config)
                except Exception as tars_error:
                    logger.warning(f"TARS analysis failed, using fallback: {tars_error}")
                    analysis_results = await self._fallback_knowledge_processing(source_type, content, metadata)
            else:
                analysis_results = await self._fallback_knowledge_processing(source_type, content, metadata)
            
            # Process and structure analysis results
            knowledge_update = await self._process_analysis_results(analysis_results)
            
            # Update unified knowledge base (Supabase + Qdrant)
            storage_results = await self._update_unified_knowledge_base(knowledge_update)
            
            # Store import metadata for tracking
            import_record = await self._store_import_metadata(source_type, content, metadata, analysis_results)
            
            # Update session context with new knowledge
            await self._update_session_knowledge_context(import_record["id"])
            
            return {
                "import_id": import_record["id"],
                "source_type": source_type,
                "knowledge_base_updated": True,
                "analysis_results": knowledge_update,
                "storage_stats": storage_results,
                "tars_workflows_executed": list(analysis_results.keys()) if analysis_results else [],
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id
            }
            
        except Exception as e:
            logger.error(f"Error importing and building knowledge with TARS: {e}")
            return {
                "error": str(e),
                "import_successful": False,
                "session_id": self.session_id
            }
    
    async def get_session_knowledge_status(self) -> Dict[str, Any]:
        """Get comprehensive knowledge base and session status using all TARS functions."""
        try:
            if not self.tars:
                return {"error": "TARS system not initialized"}
            
            # Get comprehensive TARS system status (function 5: get_system_status)
            tars_status = self.tars.get_system_status()
            
            # Get session-specific knowledge information
            session_knowledge = await self._get_session_knowledge_stats()
            
            # Get unified knowledge base statistics
            unified_kb_stats = await self._get_unified_knowledge_stats()
            
            # Get workflow execution history
            workflow_history = await self._get_workflow_execution_history()
            
            return {
                "session_id": self.session_id,
                "tars_system_status": tars_status,
                "session_knowledge": session_knowledge,
                "unified_knowledge_base": unified_kb_stats,
                "workflow_history": workflow_history,
                "available_tars_functions": [
                    "initialize", "analyze_project", "process_query",
                    "start_interactive_mode", "get_system_status", "shutdown"
                ],
                "knowledge_integration": {
                    "supabase_connected": self.memory is not None,
                    "qdrant_connected": self.qdrant_db is not None,
                    "gitmesh_integrated": GITMESH_AVAILABLE
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting session knowledge status: {e}")
            return {"error": str(e), "session_id": self.session_id}
    
    async def _build_session_context(self, current_message: str, context: Dict[str, Any] = None, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build comprehensive context from knowledge base, chat history, and session data."""
        try:
            session_context = {
                "session_id": self.session_id,
                "current_message": current_message,
                "knowledge_entries": [],
                "chat_history": history or [],
                "imported_files": [],
                "recent_analyses": [],
                "user_context": context or {},
                "project_context": {
                    "project_id": self.project_id,
                    "repository_id": self.repository_id,
                    "branch": self.branch
                },
                "current_context_files": context.get("files", []) if context else []
            }
            
            # FIRST: Add current context files directly (these were just processed)
            if context and context.get("files"):
                logger.info(f"[CONTEXT DEBUG] Adding {len(context['files'])} current context files directly")
                for file_data in context["files"]:
                    file_content = file_data.get("content", "")
                    
                    # Ensure file_content is a string
                    if not isinstance(file_content, str):
                        logger.warning(f"[CONTEXT DEBUG] File content is not a string, converting: {type(file_content)}")
                        file_content = str(file_content) if file_content is not None else ""
                    
                    if file_content and file_content != "Loading...":
                        # Add as knowledge entry with safe string slicing
                        try:
                            content_preview = file_content[:2000] if len(file_content) > 2000 else file_content
                            
                            knowledge_entry = {
                                "content": content_preview,  # Safely limited content
                                "metadata": {
                                    "source_type": "current_context_file",
                                    "file_path": file_data.get("path", "unknown"),
                                    "branch": file_data.get("branch", "main"),
                                    "source": "direct_context",
                                    "priority": "high"
                                }
                            }
                            session_context["knowledge_entries"].append(knowledge_entry)
                            logger.info(f"[CONTEXT DEBUG] Added current file to knowledge: {file_data.get('path')}")
                        except Exception as entry_error:
                            logger.error(f"[CONTEXT DEBUG] Error processing file entry {file_data.get('path')}: {entry_error}")
                            continue
            
            # THEN: Get additional relevant knowledge base entries from Qdrant using semantic search
            if self.qdrant_db:
                try:
                    relevant_knowledge = self.qdrant_db.search_memory(
                        query=current_message,
                        memory_type="knowledge",
                        limit=8,  # Reduced to make room for current files
                        filter_params={"session_id": self.session_id}
                    )
                    # Add to existing knowledge entries
                    session_context["knowledge_entries"].extend(relevant_knowledge)
                    logger.info(f"[CONTEXT DEBUG] Found {len(relevant_knowledge)} additional knowledge entries from vector search")
                except Exception as e:
                    logger.warning(f"Could not search knowledge base: {e}")
            
            total_knowledge = len(session_context["knowledge_entries"])
            logger.info(f"[CONTEXT DEBUG] Total knowledge entries for AI context: {total_knowledge}")
            
            # Get session conversation history from vector store
            if self.memory:
                try:
                    conversation_memories = self.memory.search_memory(
                        query=current_message,
                        memory_type="conversation",
                        filter_params={"session_id": self.session_id},
                        limit=5
                    )
                    session_context["stored_chat_history"] = conversation_memories[-10:]  # Last 10
                except Exception as e:
                    logger.warning(f"Could not get conversation history: {e}")
            
            # Get session's imported files and analyses
            session_context["imported_files"] = await self._get_session_imported_files()
            session_context["recent_analyses"] = await self._get_recent_session_analyses()
            
            return session_context
            
        except Exception as e:
            logger.error(f"Error building session context: {e}")
            return {
                "session_id": self.session_id,
                "current_message": current_message,
                "error": str(e)
            }
    
    async def _enhance_query_with_knowledge(self, query: str, session_context: Dict[str, Any]) -> str:
        """Enhance user query with progressive context loading for optimal AI responses."""
        try:
            # Try to use progressive context manager first
            return await self._enhance_query_progressive(query, session_context)
        except Exception as e:
            logger.warning(f"Progressive context enhancement failed: {e}")
            # Fallback to existing method
            return await self._enhance_query_optimized(query, session_context)
    
    async def _enhance_query_progressive(self, query: str, session_context: Dict[str, Any]) -> str:
        """Enhanced query with progressive context loading."""
        from .context_manager import ProgressiveContextManager
        context_manager = ProgressiveContextManager(max_context_tokens=4000)
        
        # Add repository knowledge with progressive detail
        if self.repository_id and any(keyword in query.lower() for keyword in ['code', 'repo', 'project', 'file', 'structure', 'function', 'class', 'how', 'what', 'analyze']):
            try:
                cache_key = f"https://github.com/{self.repository_id}:{self.branch or 'main'}"
                if cache_key in self.repo_knowledge_cache:
                    repo_data = self.repo_knowledge_cache[cache_key]
                    repo_content = repo_data.get("content", "")
                    if repo_content:
                        context_manager.add_repository_context(repo_content, self.repository_id)
            except Exception as e:
                logger.warning(f"Error adding repository context: {e}")
        
        # Add knowledge base entries
        knowledge_entries = session_context.get("knowledge_entries", [])
        for i, entry in enumerate(knowledge_entries[:10]):
            content = entry.get("content", "")
            metadata = entry.get("metadata", {})
            if content:
                source_type = metadata.get('source_type', 'knowledge_base')
                
                # Determine appropriate level based on content length and type
                if len(content) < 200:
                    level = "summary"
                    priority = 0.8
                elif len(content) < 800:
                    level = "details"
                    priority = 0.6
                else:
                    level = "specifics"
                    priority = 0.4
                
                context_manager.add_context_item(
                    content=f"Knowledge: {content[:800]}...",
                    context_type=source_type,
                    source=f"KB Entry {i+1}",
                    priority=priority,
                    level=level
                )
        
        # Add conversation history
        chat_history = session_context.get("stored_chat_history", [])
        for i, conv in enumerate(chat_history[-3:]):
            role = conv.get("metadata", {}).get("role", "unknown")
            content = conv.get("content", "")
            if content:
                context_manager.add_context_item(
                    content=f"Previous {role}: {content[:300]}...",
                    context_type="conversation_history",
                    source=f"Chat {i+1}",
                    priority=0.3,
                    level="details"
                )
        
        # Add imported files summary
        imported_files = session_context.get("imported_files", [])
        if imported_files:
            files_summary = f"Available Files ({len(imported_files)}): "
            files_summary += ", ".join([f"{f.get('name', 'unknown')} ({f.get('type', 'unknown')})" 
                                      for f in imported_files[:5]])
            if len(imported_files) > 5:
                files_summary += f" and {len(imported_files) - 5} more"
            
            context_manager.add_context_item(
                content=files_summary,
                context_type="file_inventory",
                source="Imported Files",
                priority=0.7,
                level="summary"
            )
        
        # Add project context summary
        project_context = session_context.get("project_context", {})
        if project_context.get("repository_id"):
            project_summary = f"Project: {project_context['repository_id']}"
            if project_context.get("branch"):
                project_summary += f" (Branch: {project_context['branch']})"
            
            context_manager.add_context_item(
                content=project_summary,
                context_type="project_info",
                source="Project Context",
                priority=0.9,
                level="summary"
            )
        
        # Build progressive context
        enhanced_query, metrics = context_manager.build_progressive_context(query)
        
        # Log context optimization metrics
        logger.info(f"Context optimization: {metrics.get('utilization_percent', 0):.1f}% utilization, "
                   f"{metrics.get('items_included', {})} items across {metrics.get('levels_used', 0)} levels")
        
        return enhanced_query
    
    async def _enhance_query_optimized(self, query: str, session_context: Dict[str, Any]) -> str:
        """Enhance user query with optimized knowledge base context for TARS processing."""
        try:
            enhanced_parts = [f"User Query: {query}\n"]
            
            # Use context optimizer if available for better context management
            context_optimizer = None
            if INDEXER_AVAILABLE:
                try:
                    from .indexing.core import ContextOptimizer, IndexingConfig
                    config = IndexingConfig(context_window=4000)  # Conservative limit for better responses
                    context_optimizer = ContextOptimizer(config)
                except ImportError:
                    pass
            
            # Collect all potential context chunks
            context_chunks = []
            
            # Add repository knowledge if available and relevant
            if self.repository_id and any(keyword in query.lower() for keyword in ['code', 'repo', 'project', 'file', 'structure', 'function', 'class', 'how', 'what', 'analyze']):
                try:
                    cache_key = f"https://github.com/{self.repository_id}:{self.branch or 'main'}"
                    if cache_key in self.repo_knowledge_cache:
                        repo_data = self.repo_knowledge_cache[cache_key]
                        repo_content = repo_data.get("content", "")
                        if repo_content:
                            # Smart chunking for repository content
                            lines = repo_content.split('\n')
                            
                            # Create high-level summary chunk
                            file_count = len([l for l in lines if l.startswith('File: ')])
                            summary_chunk = f"� Repository Overview: {file_count} files in {self.repository_id}"
                            context_chunks.append(summary_chunk)
                            
                            # Extract key code elements as chunks
                            key_elements = []
                            current_chunk = []
                            for line in lines:
                                if any(pattern in line for pattern in ['def ', 'class ', 'import ', 'from ', 'function ']):
                                    if current_chunk:
                                        context_chunks.append('\n'.join(current_chunk))
                                        current_chunk = []
                                    current_chunk.append(line.strip())
                                elif current_chunk:
                                    current_chunk.append(line.strip())
                                    if len(current_chunk) >= 5:  # Limit chunk size
                                        context_chunks.append('\n'.join(current_chunk))
                                        current_chunk = []
                                        
                                if len(context_chunks) >= 20:  # Limit total chunks
                                    break
                            
                            if current_chunk:
                                context_chunks.append('\n'.join(current_chunk))
                                
                except Exception as e:
                    logger.warning(f"Error adding repository context: {e}")
            
            # Add relevant knowledge base context as chunks
            knowledge_entries = session_context.get("knowledge_entries", [])
            for entry in knowledge_entries[:10]:  # Limit entries
                content = entry.get("content", "")
                metadata = entry.get("metadata", {})
                if content:
                    source_info = f"Source: {metadata.get('source_type', 'unknown')}"
                    chunk = f"{source_info}\n{content[:500]}..."  # Limit chunk size
                    context_chunks.append(chunk)
            
            # Add recent conversation context as chunks
            chat_history = session_context.get("stored_chat_history", [])
            for conv in chat_history[-5:]:  # Limit history
                role = conv.get("metadata", {}).get("role", "unknown")
                content = conv.get("content", "")
                if content:
                    chunk = f"Previous {role}: {content[:200]}..."
                    context_chunks.append(chunk)
            
            # Add imported files context as chunks
            imported_files = session_context.get("imported_files", [])
            for file_info in imported_files[:5]:  # Limit files
                name = file_info.get('name', 'unknown')
                file_type = file_info.get('type', 'unknown')
                chunk = f"Available file: {name} ({file_type})"
                context_chunks.append(chunk)
            
            # Add current context files (files sent with this message)
            current_files = session_context.get("current_context_files", [])
            for file_data in current_files:
                file_path = file_data.get("path", "unknown")
                file_content = file_data.get("content", "")
                file_branch = file_data.get("branch", "main")
                
                if file_content and file_content != "Loading...":
                    # Add file header info
                    file_info_chunk = f"📄 Current File: {file_path} (branch: {file_branch})"
                    context_chunks.append(file_info_chunk)
                    
                    # Add file content in manageable chunks
                    if len(file_content) > 1000:
                        # For large files, add summary and key sections
                        content_chunk = f"File Content (first 800 chars): {file_content[:800]}..."
                        context_chunks.append(content_chunk)
                        
                        # Add last part too for completeness
                        if len(file_content) > 1600:
                            end_chunk = f"File Content (last 400 chars): ...{file_content[-400:]}"
                            context_chunks.append(end_chunk)
                    else:
                        # For smaller files, include full content
                        content_chunk = f"Full File Content:\n{file_content}"
                        context_chunks.append(content_chunk)
                else:
                    # File without content
                    context_chunks.append(f"📄 File: {file_path} (content not available)")
            
            if current_files:
                logger.info(f"Added {len(current_files)} current context files to query enhancement")
            
            # Use context optimizer to select best chunks
            if context_optimizer and context_chunks:
                try:
                    optimized_chunks, context_stats = context_optimizer.calculate_optimal_context(
                        context_chunks, query
                    )
                    
                    # Add optimized context
                    if optimized_chunks:
                        enhanced_parts.append("🎯 Relevant Context (Optimized):")
                        for i, chunk in enumerate(optimized_chunks, 1):
                            enhanced_parts.append(f"{i}. {chunk}")
                            if i >= 8:  # Limit displayed chunks
                                break
                        enhanced_parts.append("")
                        
                        # Add context utilization info for debugging
                        enhanced_parts.append(f"📊 Context Usage: {context_stats.utilization_percentage:.1f}% of available tokens")
                        enhanced_parts.append("")
                        
                except Exception as e:
                    logger.warning(f"Error optimizing context: {e}")
                    # Fallback to basic context
                    if context_chunks:
                        enhanced_parts.append("📚 Available Context:")
                        for i, chunk in enumerate(context_chunks[:5], 1):
                            enhanced_parts.append(f"{i}. {chunk[:200]}...")
                        enhanced_parts.append("")
            else:
                # Fallback for when optimizer not available
                if context_chunks:
                    enhanced_parts.append("📚 Available Context:")
                    for i, chunk in enumerate(context_chunks[:5], 1):
                        enhanced_parts.append(f"{i}. {chunk[:200]}...")
                    enhanced_parts.append("")
            
            # Add project context
            project_context = session_context.get("project_context", {})
            if project_context.get("repository_id"):
                enhanced_parts.append(f"🔧 Project: {project_context['repository_id']}")
                if project_context.get("branch"):
                    enhanced_parts.append(f"🌿 Branch: {project_context['branch']}")
                enhanced_parts.append("")
            
            enhanced_parts.append("💡 Please provide a comprehensive response based on the above context, focusing on the most relevant information from the optimized knowledge base.")
            
            return "\\n".join(enhanced_parts)
            
        except Exception as e:
            logger.error(f"Error enhancing query with knowledge: {e}")
            return query  # Fallback to original query
    
    async def _structure_tars_response(self, response: Any, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """Structure TARS response with metadata and confidence scoring."""
        try:
            content = ""
            
            if isinstance(response, dict):
                content = response.get("content", str(response))
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            # Check for and clean up any JSON tool calls or function formats
            if (content.strip().startswith('{') and '"name"' in content) or '"function"' in content or '"type": "function"' in content:
                # Generate a dynamic response based on session context instead of hardcoded text
                if session_context.get("imported_files"):
                    file_count = len(session_context["imported_files"])
                    content = f"I see you have {file_count} files available for analysis. What would you like me to help you with regarding your project?"
                elif session_context.get("repository_id"):
                    repo_id = session_context["repository_id"]
                    content = f"I'm ready to help with your {repo_id} repository. What specific aspect would you like me to analyze or discuss?"
                elif session_context.get("current_context_files"):
                    file_count = len(session_context["current_context_files"])
                    if file_count == 1:
                        content = f"I can see you've shared a file with me. What would you like me to help you with regarding this code?"
                    else:
                        content = f"I can see you've shared {file_count} files with me. What would you like me to help you analyze or discuss?"
                else:
                    content = "Hello! I'm here to help with code analysis, project questions, and development tasks. What can I assist you with?"
            
            # Clean and format the response
            content = content.strip()
            if not content:
                content = "I'm here to help! Could you please rephrase your question?"
            
            return {
                "content": content,
                "sources": response.get("sources", []) if isinstance(response, dict) else [],
                "confidence": response.get("confidence", 0.8) if isinstance(response, dict) else 0.7,
                "workflow_used": response.get("workflow", "conversation") if isinstance(response, dict) else "direct_query",
                "knowledge_entries_used": len(session_context.get("knowledge_entries", [])),
                "session_id": self.session_id
            }
        except Exception as e:
            logger.error(f"Error structuring TARS response: {e}")
            return {
                "content": "TARS: I encountered an issue while processing your request. Please try rephrasing your question and I'll do my best to help you.",
                "sources": [],
                "confidence": 0.1,
                "error": str(e),
                "session_id": self.session_id
            }
    
    async def _store_conversation_with_context(self, message: str, response: Dict[str, Any], session_context: Dict[str, Any]):
        """Store conversation in Supabase and update Qdrant embeddings with full context."""
        try:
            timestamp = datetime.now().isoformat()
            
            # Store in vector database via memory system
            if self.memory:
                # Store user message
                self.memory.store_memory(
                    text=message,
                    memory_type="conversation",
                    metadata={
                        "session_id": self.session_id,
                        "role": "user",
                        "timestamp": timestamp,
                        "project_id": self.project_id,
                        "knowledge_entries_available": len(session_context.get("knowledge_entries", []))
                    }
                )
                
                # Store assistant response
                self.memory.store_memory(
                    text=response["content"],
                    memory_type="conversation", 
                    metadata={
                        "session_id": self.session_id,
                        "role": "assistant",
                        "timestamp": timestamp,
                        "project_id": self.project_id,
                        "workflow_used": response.get("workflow_used"),
                        "quality": response.get("confidence", 0.7),
                        "knowledge_entries_used": response.get("knowledge_entries_used", 0),
                        "sources_count": len(response.get("sources", []))
                    }
                )
            
            # Update Qdrant with conversation embeddings
            if self.qdrant_db:
                conversation_text = f"User: {message}\\nAssistant: {response['content']}"
                self.qdrant_db.store_memory(
                    text=conversation_text,
                    memory_type="session_context",
                    metadata={
                        "session_id": self.session_id,
                        "timestamp": timestamp,
                        "confidence": response.get("confidence", 0.7)
                    }
                )
                
        except Exception as e:
            logger.error(f"Error storing conversation with context: {e}")
    
    async def _prepare_comprehensive_import_config(self, source_type: str, content: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comprehensive configuration for TARS analyze_project based on import type."""
        config = {
            "web_urls": None,
            "repositories": None,
            "documents": None,
            "data_files": None,
            "github_repos": None,
            "analysis_options": {
                "comprehensive_analysis": True,
                "build_knowledge_base": True,
                "session_id": self.session_id,
                "project_id": self.project_id,
                **(metadata or {})
            }
        }
        
        if source_type in ["repository", "repo"]:
            if isinstance(content, str):
                if content.startswith(("http://", "https://")):
                    config["repositories"] = [content]
                elif "/" in content and not content.startswith("/"):
                    config["github_repos"] = [content]  # owner/repo format
                else:
                    config["repositories"] = [content]
        
        elif source_type in ["web_url", "url", "web"]:
            urls = [content] if isinstance(content, str) else content
            config["web_urls"] = urls
        
        elif source_type in ["file", "files", "document", "documents"]:
            files = [content] if isinstance(content, str) else content
            # Determine if it's data files or documents
            if any(f.endswith(('.csv', '.xlsx', '.json', '.xml')) for f in files):
                config["data_files"] = files
            else:
                config["documents"] = files
        
        elif source_type == "text":
            # Create temporary file for text content
            import tempfile
            import os
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            temp_file.write(str(content))
            temp_file.close()
            config["documents"] = [temp_file.name]
            config["analysis_options"]["temp_file"] = temp_file.name  # Track for cleanup
        
        elif source_type == "github":
            config["github_repos"] = [content] if isinstance(content, str) else content
        
        return config
    
    async def _process_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and structure TARS analysis results for knowledge base storage."""
        try:
            processed_results = {
                "workflows_executed": [],
                "knowledge_extracted": [],
                "analysis_summary": {},
                "total_insights": 0
            }
            
            for workflow_name, result in analysis_results.items():
                workflow_data = {
                    "workflow": workflow_name,
                    "status": getattr(result, "status", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id
                }
                
                if hasattr(result, "data") and result.data:
                    workflow_data["data"] = result.data
                    workflow_data["insights_count"] = len(result.data) if isinstance(result.data, (list, dict)) else 1
                    processed_results["total_insights"] += workflow_data["insights_count"]
                    
                    # Extract knowledge for storage
                    knowledge_entry = {
                        "content": json.dumps(result.data),
                        "source_workflow": workflow_name,
                        "session_id": self.session_id,
                        "timestamp": workflow_data["timestamp"]
                    }
                    processed_results["knowledge_extracted"].append(knowledge_entry)
                
                processed_results["workflows_executed"].append(workflow_data)
            
            processed_results["analysis_summary"] = {
                "total_workflows": len(analysis_results),
                "successful_workflows": len([r for r in processed_results["workflows_executed"] if r.get("status") == "success"]),
                "total_knowledge_entries": len(processed_results["knowledge_extracted"]),
                "session_id": self.session_id
            }
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Error processing analysis results: {e}")
            return {"error": str(e), "workflows_executed": [], "knowledge_extracted": []}
    
    async def _update_unified_knowledge_base(self, knowledge_update: Dict[str, Any]) -> Dict[str, Any]:
        """Update unified Supabase + Qdrant knowledge base with processed analysis results."""
        try:
            storage_stats = {
                "supabase_entries_added": 0,
                "qdrant_embeddings_added": 0,
                "total_entries": 0,
                "errors": []
            }
            
            knowledge_entries = knowledge_update.get("knowledge_extracted", [])
            
            for entry in knowledge_entries:
                try:
                    # Store in Supabase via memory system
                    if self.memory:
                        await self.memory.save_memory(
                            content=entry["content"],
                            memory_type="knowledge",
                            quality=0.85,
                            metadata={
                                "source_workflow": entry["source_workflow"],
                                "session_id": entry["session_id"],
                                "timestamp": entry["timestamp"],
                                "project_id": self.project_id,
                                "repository_id": self.repository_id
                            }
                        )
                        storage_stats["supabase_entries_added"] += 1
                    
                    # Store embeddings in Qdrant
                    if self.qdrant_db:
                        await self.qdrant_db.save_memory(
                            content=entry["content"],
                            memory_type="knowledge",
                            metadata={
                                "source_workflow": entry["source_workflow"],
                                "session_id": entry["session_id"],
                                "timestamp": entry["timestamp"]
                            }
                        )
                        storage_stats["qdrant_embeddings_added"] += 1
                
                except Exception as e:
                    error_msg = f"Error storing knowledge entry: {e}"
                    logger.error(error_msg)
                    storage_stats["errors"].append(error_msg)
            
            # Get updated total count
            if self.memory:
                try:
                    memory_stats = await self.memory.get_memory_stats()
                    storage_stats["total_entries"] = memory_stats.get("total_memories", 0)
                except:
                    pass
            
            return storage_stats
            
        except Exception as e:
            logger.error(f"Error updating unified knowledge base: {e}")
            return {"error": str(e), "supabase_entries_added": 0, "qdrant_embeddings_added": 0}
    
    async def _store_import_metadata(self, source_type: str, content: Any, metadata: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Store comprehensive import metadata in Supabase for tracking and session management."""
        try:
            import_id = str(uuid.uuid4())
            
            import_record = {
                "id": import_id,
                "session_id": self.session_id,
                "user_id": self.user_id,
                "project_id": self.project_id,
                "repository_id": self.repository_id,
                "source_type": source_type,
                "content_summary": str(content)[:1000],  # First 1000 chars
                "metadata": metadata or {},
                "analysis_results_summary": {
                    workflow: str(result)[:300] for workflow, result in results.items()
                } if results else {},
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "workflows_executed": list(results.keys()) if results else []
            }
            
            # Store in memory system
            if self.memory:
                await self.memory.save_memory(
                    content=json.dumps(import_record),
                    memory_type="import_record",
                    quality=0.9,
                    metadata=import_record
                )
            
            return import_record
            
        except Exception as e:
            logger.error(f"Error storing import metadata: {e}")
            return {
                "id": "error", 
                "error": str(e),
                "session_id": self.session_id
            }
    
    async def _generate_intelligent_fallback_response(self, message: str, context: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Generate intelligent fallback response when TARS processing fails."""
        try:
            message_lower = message.lower().strip()
            
            # Analyze message intent
            if any(word in message_lower for word in ['import', 'analyze', 'load', 'add']):
                content = f"I understand you want to import or analyze something. Due to a technical issue ({error[:100]}...), I can't process this through TARS right now, but I can help you prepare the import. What type of content are you trying to import?"
            
            elif any(word in message_lower for word in ['knowledge', 'base', 'learn', 'remember']):
                content = f"You're asking about the knowledge base. While I'm experiencing some technical difficulties ({error[:50]}...), I can tell you that I maintain context from our conversations and any files you've imported. What specific information are you looking for?"
            
            elif any(word in message_lower for word in ['status', 'health', 'working', 'system']):
                content = f"You're checking system status. I'm currently experiencing some issues ({error[:100]}...), but I'm still here to help. The knowledge base and conversation history are maintained. Would you like me to try a different approach?"
            
            else:
                content = f"I'm experiencing some technical difficulties with TARS processing right now ({error[:50]}...), but I'm still here to help. Could you rephrase your question or let me know what specific task you're trying to accomplish?"
            
            return {
                "content": content,
                "sources": [],
                "confidence": 0.3,
                "error": error,
                "fallback_used": True,
                "session_id": self.session_id
            }
            
        except Exception as e:
            logger.error(f"Error generating fallback response: {e}")
            return {
                "content": "I'm experiencing technical difficulties. Please try again.",
                "sources": [],
                "confidence": 0.1,
                "error": str(e),
                "session_id": self.session_id
            }
    
    # Helper methods for session knowledge management
    async def _fallback_knowledge_processing(self, source_type: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback knowledge processing when TARS is not available"""
        try:
            # Extract key information from content
            analysis_results = {
                "knowledge_extraction": {
                    "source_type": source_type,
                    "content_length": len(content),
                    "content_summary": content[:200] + "..." if len(content) > 200 else content,
                    "key_topics": self._extract_key_topics(content),
                    "metadata": metadata
                },
                "processing_method": "fallback",
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in vector database if available
            if self.qdrant_db:
                memory_id = self.qdrant_db.store_memory(
                    text=content,
                    memory_type="knowledge",
                    metadata={
                        **metadata,
                        "source_type": source_type,
                        "session_id": self.session_id,
                        "processing_method": "fallback"
                    }
                )
                analysis_results["vector_storage"] = {
                    "memory_id": memory_id,
                    "stored": True
                }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in fallback knowledge processing: {e}")
            return {"error": str(e), "processing_method": "fallback_failed"}
    
    def _extract_key_topics(self, content: str) -> List[str]:
        """Extract key topics from content using simple keyword extraction"""
        # Simple keyword extraction - in production, this could use NLP
        words = content.lower().split()
        
        # Common technical terms and concepts
        key_terms = [
            "api", "database", "authentication", "security", "performance",
            "integration", "configuration", "deployment", "testing", "documentation",
            "git", "github", "repository", "branch", "commit", "merge",
            "python", "javascript", "java", "react", "node", "fastapi",
            "supabase", "qdrant", "vector", "embedding", "ai", "machine learning",
            "tars", "gitmesh", "chat", "knowledge", "session", "user"
        ]
        
        found_topics = []
        for term in key_terms:
            if term in words:
                found_topics.append(term)
        
        # Also look for capitalized words (potential proper nouns/technologies)
        for word in content.split():
            if word[0].isupper() and len(word) > 3 and word not in found_topics:
                found_topics.append(word.lower())
        
        return found_topics[:10]  # Return top 10 topics
    
    async def _fallback_chat_processing(self, message: str, context: Dict[str, Any], session_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Intelligent fallback chat processing when TARS is not available"""
        try:
            # Process any files in the context first
            if context and context.get("files"):
                await self._process_context_files(context["files"])
            
            # Search existing knowledge base for relevant information
            relevant_knowledge = []
            knowledge_entries_used = 0
            
            if self.qdrant_db:
                search_results = self.qdrant_db.search_memory(
                    query=message,
                    memory_type=["knowledge", "user"],
                    limit=5,
                    relevance_cutoff=0.3
                )
                
                for result in search_results:
                    relevant_knowledge.append({
                        "content": result["text"],
                        "score": result["score"],
                        "metadata": result.get("metadata", {})
                    })
                    knowledge_entries_used += 1
            
            # Generate intelligent response based on knowledge and context
            response_content = self._generate_intelligent_response_with_knowledge(
                message, relevant_knowledge, session_history
            )
            
            # Calculate confidence based on knowledge relevance
            confidence = min(0.8, max(0.4, sum(k["score"] for k in relevant_knowledge) / max(1, len(relevant_knowledge))))
            
            # Extract sources
            sources = [k["metadata"].get("source", "knowledge_base") for k in relevant_knowledge]
            
            # Store this conversation for future context
            if self.qdrant_db:
                conversation_text = f"User: {message}\nAssistant: {response_content}"
                self.qdrant_db.store_memory(
                    text=conversation_text,
                    memory_type="user",
                    metadata={
                        "session_id": self.session_id,
                        "user_id": self.user_id,
                        "conversation": True,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            return {
                "content": response_content,
                "sources": list(set(sources)),
                "confidence": confidence,
                "knowledge_entries_used": knowledge_entries_used,
                "processing_method": "fallback_with_knowledge",
                "session_id": self.session_id
            }
            
        except Exception as e:
            logger.error(f"Error in fallback chat processing: {e}")
            return {
                "content": f"I encountered an error processing your message: {str(e)[:100]}..., but I'm still here to help. Could you rephrase your question?",
                "sources": [],
                "confidence": 0.2,
                "error": str(e),
                "processing_method": "error_fallback"
            }
    
    def _generate_intelligent_response_with_knowledge(self, message: str, knowledge: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> str:
        """Generate an intelligent response using available knowledge"""
        message_lower = message.lower()
        
        # If we have relevant knowledge, create a comprehensive response
        if knowledge:
            # Process knowledge into organized content
            knowledge_content = []
            file_sources = []
            
            for item in knowledge[:5]:  # Use top 5 most relevant items
                content = item.get("content", "")
                metadata = item.get("metadata", {})
                source = metadata.get("source", "knowledge_base")
                
                # Track file sources
                if "file_path" in metadata:
                    file_sources.append(metadata["file_path"])
                
                # Add content with proper formatting
                if len(content) > 300:
                    content = content[:300] + "..."
                knowledge_content.append(content)
            
            # Build contextual response
            response_parts = []
            
            # Add file context if available
            if file_sources:
                unique_files = list(set(file_sources))
                if len(unique_files) == 1:
                    response_parts.append(f"Based on the file `{unique_files[0]}` you've provided:")
                else:
                    response_parts.append(f"Based on the {len(unique_files)} files you've provided:")
            else:
                response_parts.append("Based on the available context:")
            
            # Add knowledge content
            response_parts.append("\n".join(knowledge_content))
            
            # Add helpful follow-up
            if "analysis" in message_lower or "analyze" in message_lower:
                response_parts.append("\nWould you like me to provide a deeper analysis of any specific section?")
            elif "explain" in message_lower or "how" in message_lower:
                response_parts.append("\nLet me know if you need clarification on any of these points.")
            else:
                response_parts.append("\nWhat specific aspect would you like me to explore further?")
            
            return "\n\n".join(response_parts)
        
        # Fallback to intelligent responses based on message content
        if any(word in message_lower for word in ['tars', 'integration', 'gitmesh']):
            return f"I can help you with GitMesh and TARS integration. The system supports knowledge base building, intelligent chat, and unified storage with Supabase and Qdrant. What specific aspect of '{message}' would you like to explore?"
        
        elif any(word in message_lower for word in ['how', 'what', 'explain']):
            return f"I'd be happy to help explain that. To give you the most relevant answer about '{message}', could you provide a bit more context about what you're trying to accomplish?"
        
        elif any(word in message_lower for word in ['code', 'function', 'api', 'implementation']):
            return f"I can help with code analysis and implementation details. For your question about '{message}', could you share the specific code or component you're working with?"
        
        else:
            return f"I understand you're asking about '{message}'. To provide the most helpful response, could you share more details about what you're trying to achieve or any relevant files/code?"
    
    async def _get_session_knowledge_stats(self) -> Dict[str, Any]:
        """Get knowledge statistics for current session."""
        try:
            stats = {
                "conversation_count": 0,
                "knowledge_entries": 0,
                "imports_count": 0,
                "last_activity": None
            }
            
            if self.memory:
                # Get session conversations
                conversations = await self.memory.get_memories(
                    memory_type="conversation",
                    metadata_filter={"session_id": self.session_id}
                )
                stats["conversation_count"] = len(conversations)
                
                # Get session knowledge entries
                knowledge = await self.memory.get_memories(
                    memory_type="knowledge", 
                    metadata_filter={"session_id": self.session_id}
                )
                stats["knowledge_entries"] = len(knowledge)
                
                # Get session imports
                imports = await self.memory.get_memories(
                    memory_type="import_record",
                    metadata_filter={"session_id": self.session_id}
                )
                stats["imports_count"] = len(imports)
                
                if conversations:
                    stats["last_activity"] = conversations[-1].get("metadata", {}).get("timestamp")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting session knowledge stats: {e}")
            return {"error": str(e)}
    
    async def _get_unified_knowledge_stats(self) -> Dict[str, Any]:
        """Get unified knowledge base statistics across all sessions."""
        try:
            if self.memory:
                return await self.memory.get_memory_stats()
            return {"total_memories": 0, "error": "Memory system not available"}
        except Exception as e:
            logger.error(f"Error getting unified knowledge stats: {e}")
            return {"error": str(e)}
    
    async def _get_workflow_execution_history(self) -> List[Dict[str, Any]]:
        """Get recent workflow execution history for this session."""
        try:
            if self.memory:
                imports = await self.memory.get_memories(
                    memory_type="import_record",
                    metadata_filter={"session_id": self.session_id}
                )
                
                history = []
                for import_record in imports[-10:]:  # Last 10 imports
                    metadata = import_record.get("metadata", {})
                    history.append({
                        "import_id": metadata.get("id"),
                        "source_type": metadata.get("source_type"),
                        "workflows_executed": metadata.get("workflows_executed", []),
                        "timestamp": metadata.get("timestamp"),
                        "status": metadata.get("status")
                    })
                
                return history
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting workflow execution history: {e}")
            return []
    
    async def _get_session_imported_files(self) -> List[Dict[str, Any]]:
        """Get files imported in current session."""
        try:
            if self.memory:
                imports = await self.memory.get_memories(
                    memory_type="import_record",
                    metadata_filter={"session_id": self.session_id}
                )
                
                files = []
                for import_record in imports:
                    metadata = import_record.get("metadata", {})
                    files.append({
                        "name": metadata.get("source_type", "unknown"),
                        "type": metadata.get("source_type"),
                        "timestamp": metadata.get("timestamp"),
                        "id": metadata.get("id")
                    })
                
                return files
            return []
        except:
            return []
    
    async def _get_recent_session_analyses(self) -> List[Dict[str, Any]]:
        """Get recent analysis results for current session."""
        try:
            if self.memory:
                knowledge_entries = await self.memory.get_memories(
                    memory_type="knowledge",
                    metadata_filter={"session_id": self.session_id}
                )
                
                analyses = []
                for entry in knowledge_entries[-5:]:  # Last 5 analyses
                    metadata = entry.get("metadata", {})
                    analyses.append({
                        "workflow": metadata.get("source_workflow", "unknown"),
                        "timestamp": metadata.get("timestamp"),
                        "summary": entry.get("content", "")[:200] + "..."
                    })
                
                return analyses
            return []
        except:
            return []
    
    async def _update_session_knowledge_context(self, import_id: str):
        """Update session context with new import for future reference."""
        try:
            if self.memory:
                context_update = {
                    "session_id": self.session_id,
                    "new_import_id": import_id,
                    "timestamp": datetime.now().isoformat(),
                    "action": "knowledge_updated"
                }
                
                await self.memory.save_memory(
                    content=json.dumps(context_update),
                    memory_type="session_context",
                    quality=0.7,
                    metadata=context_update
                )
        except Exception as e:
            logger.warning(f"Could not update session knowledge context: {e}")
    
    # Repository Intelligence Methods
    
    async def _get_repository_hash(self, repo_url: str, branch: str = "main") -> Optional[str]:
        """Get a hash representing the current state of the repository."""
        try:
            if not self.gitingest_tool:
                return None
            
            # Get repository metadata to check for updates
            metadata = self.gitingest_tool.get_repository_metadata(repo_url)
            if not metadata.get("accessible"):
                return None
            
            # Create hash from relevant metadata
            hash_data = {
                "repo": repo_url,
                "branch": branch,
                "updated_at": metadata.get("info", {}).get("updated_at"),
                "size": metadata.get("info", {}).get("size")
            }
            
            hash_string = json.dumps(hash_data, sort_keys=True)
            return hashlib.md5(hash_string.encode()).hexdigest()
            
        except Exception as e:
            logger.warning(f"Failed to get repository hash: {e}")
            return None
    
    async def _should_rebuild_knowledge_base(self, repo_url: str, branch: str = "main") -> bool:
        """Determine if the knowledge base should be rebuilt."""
        try:
            current_hash = await self._get_repository_hash(repo_url, branch)
            if not current_hash:
                return True  # Rebuild if we can't determine state
            
            # Check if we have cached knowledge for this repository
            cache_key = f"{repo_url}:{branch}"
            if cache_key not in self.repo_knowledge_cache:
                return True  # First-time analysis
            
            # Check if the hash has changed
            cached_hash = self.last_repo_analysis.get(cache_key, {}).get("hash")
            if current_hash != cached_hash:
                logger.info(f"Repository {repo_url} has been updated - rebuilding knowledge base")
                return True
            
            # Check if the cached knowledge is too old (e.g., > 24 hours)
            last_analysis_time = self.last_repo_analysis.get(cache_key, {}).get("timestamp")
            if last_analysis_time:
                time_diff = datetime.now().timestamp() - last_analysis_time
                if time_diff > 86400:  # 24 hours
                    logger.info(f"Repository knowledge for {repo_url} is stale - rebuilding")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if knowledge base should be rebuilt: {e}")
            return True  # Rebuild on error to be safe
    
    async def _analyze_repository_with_gitingest(self, repo_url: str, branch: str = "main") -> Dict[str, Any]:
        """Analyze repository using GitIngest and cache the results."""
        try:
            if not self.gitingest_tool:
                raise Exception("GitIngest tool not available")
            
            logger.info(f"🔍 Analyzing repository {repo_url} with GitIngest...")
            
            # Run GitIngest analysis
            analysis_result = self.gitingest_tool.analyze_repository(repo_url)
            
            if not analysis_result.get("success"):
                raise Exception(f"GitIngest analysis failed: {analysis_result.get('error', 'Unknown error')}")
            
            # Cache the results
            cache_key = f"{repo_url}:{branch}"
            self.repo_knowledge_cache[cache_key] = {
                "content": analysis_result["content"],
                "metadata": analysis_result["metadata"],
                "timestamp": datetime.now().timestamp()
            }
            
            # Update analysis tracking
            current_hash = await self._get_repository_hash(repo_url, branch)
            self.last_repo_analysis[cache_key] = {
                "hash": current_hash,
                "timestamp": datetime.now().timestamp(),
                "success": True
            }
            
            # Store in vector database for future retrieval
            await self._store_repository_knowledge(repo_url, branch, analysis_result["content"])
            
            logger.info(f"✅ Repository analysis completed successfully for {repo_url}")
            
            return {
                "success": True,
                "content": analysis_result["content"],
                "metadata": analysis_result["metadata"],
                "cached": False
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze repository {repo_url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "cached": False
            }
    
    async def _get_repository_knowledge(self, repo_url: str, branch: str = "main") -> Dict[str, Any]:
        """Get repository knowledge, using cache or rebuilding if necessary."""
        try:
            cache_key = f"{repo_url}:{branch}"
            
            # Check if we should rebuild the knowledge base
            should_rebuild = await self._should_rebuild_knowledge_base(repo_url, branch)
            
            if not should_rebuild and cache_key in self.repo_knowledge_cache:
                logger.info(f"📚 Using cached repository knowledge for {repo_url}")
                cached_data = self.repo_knowledge_cache[cache_key]
                return {
                    "success": True,
                    "content": cached_data["content"],
                    "metadata": cached_data["metadata"],
                    "cached": True
                }
            
            # Rebuild knowledge base
            return await self._analyze_repository_with_gitingest(repo_url, branch)
            
        except Exception as e:
            logger.error(f"Error getting repository knowledge: {e}")
            return {
                "success": False,
                "error": str(e),
                "cached": False
            }
    
    async def _store_repository_knowledge(self, repo_url: str, branch: str, content: str):
        """Store repository knowledge in vector database for retrieval."""
        try:
            if not self.qdrant_db:
                logger.warning("Vector database not available - skipping knowledge storage")
                return
            
            # Create chunks of the repository content for better retrieval
            chunks = self._chunk_repository_content(content)
            
            # Store each chunk in the vector database
            collection_name = self.knowledge_config["vector_store"]["config"]["collection_name"]
            
            for i, chunk in enumerate(chunks):
                document_id = f"repo_{hashlib.md5(repo_url.encode()).hexdigest()}_{branch}_{i}"
                metadata = {
                    "source": "repository",
                    "repo_url": repo_url,
                    "branch": branch,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Store using the existing knowledge system
                if hasattr(self.qdrant_db, 'add_document'):
                    await self.qdrant_db.add_document(
                        collection_name=collection_name,
                        document=chunk,
                        metadata=metadata,
                        document_id=document_id
                    )
            
            logger.info(f"📚 Stored {len(chunks)} knowledge chunks for repository {repo_url}")
            
        except Exception as e:
            logger.error(f"Failed to store repository knowledge: {e}")
    
    def _chunk_repository_content(self, content: str, chunk_size: int = 2000) -> List[str]:
        """Intelligently chunk repository content for vector storage."""
        try:
            # Split by common code boundaries
            sections = []
            
            # Split by file boundaries first (assuming GitIngest format)
            if "File: " in content:
                file_sections = content.split("File: ")
                for section in file_sections[1:]:  # Skip first empty section
                    if len(section.strip()) > 0:
                        sections.append(f"File: {section}")
            else:
                # Fallback to simple chunking
                lines = content.split('\n')
                current_chunk = []
                current_size = 0
                
                for line in lines:
                    if current_size + len(line) > chunk_size and current_chunk:
                        sections.append('\n'.join(current_chunk))
                        current_chunk = [line]
                        current_size = len(line)
                    else:
                        current_chunk.append(line)
                        current_size += len(line)
                
                if current_chunk:
                    sections.append('\n'.join(current_chunk))
            
            # Further split large sections
            final_chunks = []
            for section in sections:
                if len(section) <= chunk_size:
                    final_chunks.append(section)
                else:
                    # Split large sections into smaller chunks
                    words = section.split()
                    current_chunk = []
                    current_length = 0
                    
                    for word in words:
                        if current_length + len(word) > chunk_size and current_chunk:
                            final_chunks.append(' '.join(current_chunk))
                            current_chunk = [word]
                            current_length = len(word)
                        else:
                            current_chunk.append(word)
                            current_length += len(word) + 1  # +1 for space
                    
                    if current_chunk:
                        final_chunks.append(' '.join(current_chunk))
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"Error chunking repository content: {e}")
            # Fallback to simple chunking
            return [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    async def analyze_current_repository(self) -> Dict[str, Any]:
        """Analyze the current repository for this session."""
        if not self.repository_id:
            return {"success": False, "error": "No repository ID configured"}
        
        # Construct repository URL (assume GitHub format)
        repo_url = f"https://github.com/{self.repository_id}"
        branch = self.branch or "main"
        
        return await self._get_repository_knowledge(repo_url, branch)
    
    async def _check_and_update_repository_knowledge(self, message: str):
        """Check if the message requires repository analysis and update knowledge if needed."""
        try:
            message_lower = message.lower()
            
            # Keywords that trigger repository analysis
            repo_keywords = [
                'repository', 'repo', 'code', 'codebase', 'project', 'files', 
                'structure', 'analyze', 'understand', 'explain', 'how does',
                'what is', 'show me', 'documentation', 'readme', 'functions',
                'classes', 'modules'
            ]
            
            # Check if the message mentions repository-related topics
            if any(keyword in message_lower for keyword in repo_keywords):
                if self.repository_id:
                    logger.info(f"🔍 Message mentions repository topics, checking knowledge base...")
                    
                    # Attempt to analyze current repository
                    repo_analysis = await self.analyze_current_repository()
                    
                    if repo_analysis.get("success"):
                        if repo_analysis.get("cached"):
                            logger.info("📚 Using existing repository knowledge")
                        else:
                            logger.info("🆕 Updated repository knowledge base")
                    else:
                        logger.warning(f"⚠️ Repository analysis failed: {repo_analysis.get('error', 'Unknown error')}")
                        
        except Exception as e:
            logger.error(f"Error checking repository knowledge: {e}")

    def chat(
        self,
        message: str,
        input_type: str = "text",
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        file_path: Optional[str] = None,
        **kwargs
    ) -> "TARSResponse":
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
            llm = LLM(**self.llm_config)
            ai_response = llm.get_response(
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

    def __del__(self):
        """Cleanup on deletion"""
        if self.tars:
            # Attempt graceful shutdown if possible
            try:
                asyncio.create_task(self.shutdown())
            except Exception:
                pass


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
        default_model: Optional[str] = None,
        memory_enabled: bool = True,
        knowledge_enabled: bool = True,
        session_storage_path: str = "./tars_sessions"
    ):
        """Initialize TARS wrapper with configuration."""
        # Use dynamic model detection if no model specified
        if not default_model:
            try:
                # Dynamic import to avoid circular dependencies
                sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                from core.context_manager import get_default_model
                model_info = get_default_model()
                default_model = model_info['model']
            except Exception as e:
                logging.warning(f"Could not get default model: {e}")
                default_model = "gpt-4o-mini"  # final fallback if all else fails
        
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


# Convenience functions for easy usage
def create_tars(
    model: Optional[str] = None,
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
    model: Optional[str] = None
) -> str:
    """Quick chat without session persistence."""
    tars = create_tars(model=model)
    response = tars.chat(message, input_type=input_type)
    return response.response
