"""
TARS v1 Main Application
=======================

Main application class for coordinating the entire TARS system.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from ai.main import display_interaction, display_error
from ai.llm import get_openai_client

from .session import TarsSession
from .workflows import AcquisitionWorkflow, AnalysisWorkflow, ConversationWorkflow
from .models import WorkflowResult, SystemHealth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TarsMain:
    """
    Main TARS application class for coordinating the entire system.
    
    This class provides a unified interface for:
    - System initialization and configuration
    - Workflow orchestration
    - Session management
    - Error handling and monitoring
    - Performance tracking
    """
    
    def __init__(
        self,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        memory_config: Optional[Dict[str, Any]] = None,
        knowledge_config: Optional[Dict[str, Any]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        verbose: bool = True
    ):
        """
        Initialize TARS main application.
        
        Args:
            user_id: User identifier
            project_id: Project identifier (auto-generated if None)
            memory_config: Memory system configuration
            knowledge_config: Knowledge base configuration
            llm_config: LLM configuration
            verbose: Enable verbose logging and output
        """
        self.user_id = user_id
        self.project_id = project_id or f"tars_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.verbose = verbose
        self.start_time = datetime.now()
        
        # Configure logging level
        if verbose:
            logging.getLogger().setLevel(logging.INFO)
        else:
            logging.getLogger().setLevel(logging.WARNING)
        
        # System configuration
        self.memory_config = self._get_default_memory_config()
        if memory_config:
            self.memory_config.update(memory_config)
        
        self.knowledge_config = self._get_default_knowledge_config()
        if knowledge_config:
            self.knowledge_config.update(knowledge_config)
        
        self.llm_config = self._get_default_llm_config()
        if llm_config:
            self.llm_config.update(llm_config)
        
        # Initialize session
        self.session = None
        self.system_status = "initializing"
        self.performance_metrics = {
            "total_queries": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_uptime": 0.0
        }
        
        logger.info(f"TARS v1 initialized for user: {user_id}, project: {self.project_id}")
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "user_id": self.user_id,
            "project_id": self.project_id,
            "memory_config": self.memory_config,
            "knowledge_config": self.knowledge_config,
            "llm_config": self.llm_config,
            "verbose": self.verbose,
            "system_status": self.system_status
        }
    
    def _get_default_memory_config(self) -> Dict[str, Any]:
        """Get default memory configuration."""
        return {
            "provider": "supabase",  # Use GitMesh hybrid memory
            "use_embedding": True,
            "embedding_provider": "sentence_transformers",
            "quality_scoring": True,
            "advanced_memory": True,
            "short_db": f".tars/{self.project_id}/short_term.db",
            "long_db": f".tars/{self.project_id}/long_term.db",
            "entity_db": f".tars/{self.project_id}/entity.db",
            "rag_db_path": f".tars/{self.project_id}/chroma_db"
        }
    
    def _get_default_knowledge_config(self) -> Dict[str, Any]:
        """Get default knowledge base configuration."""
        return {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": f"tars_knowledge_{self.project_id}",
                    "path": f".tars/{self.project_id}/knowledge"
                }
            }
        }
    
    def _get_default_llm_config(self) -> Dict[str, Any]:
        """Get default LLM configuration using enhanced model detection."""
        # Get model from enhanced configuration system
        model_name = None
        try:
            # Dynamic import to avoid circular dependencies
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from core.context_manager import get_default_model
            model_info = get_default_model()
            model_name = model_info['model']
        except Exception as e:
            logging.warning(f"Could not get default model from context manager: {e}")
            model_name = 'gpt-4o-mini'  # final fallback
        
        return {
            "model": model_name,
            "temperature": 0.7,
            "max_tokens": 4000,
            "stream": True,
            "metrics": True
        }
    
    async def initialize(self) -> bool:
        """
        Initialize the TARS system.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing TARS system...")
            
            # Create project directory
            os.makedirs(f".tars/{self.project_id}", exist_ok=True)
            
            # Initialize session
            self.session = TarsSession(
                session_id=f"tars_session_{self.project_id}",
                user_id=self.user_id,
                project_id=self.project_id,
                memory_config=self.memory_config,
                knowledge_config=self.knowledge_config
            )
            
            # Test system components
            health_check = await self._perform_health_check()
            
            if health_check:
                self.system_status = "ready"
                logger.info("TARS system initialized successfully")
                
                if self.verbose:
                    print("\n" + "="*60)
                    print("🚀 TARS v1 - Tactical AI Resource System")
                    print("="*60)
                    print(f"📂 Project: {self.project_id}")
                    print(f"👤 User: {self.user_id}")
                    print(f"🧠 Memory: {self.memory_config['provider']}")
                    print(f"🔧 LLM: {self.llm_config['model']}")
                    print("✅ System Status: Ready")
                    print("="*60 + "\n")
                
                return True
            else:
                self.system_status = "error"
                logger.error("TARS system initialization failed")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing TARS system: {e}")
            self.system_status = "error"
            if self.verbose:
                display_error(f"System initialization failed: {str(e)}")
            return False
    
    async def _perform_health_check(self) -> bool:
        """Perform system health check."""
        try:
            # Test memory system
            if self.session:
                self.session.add_memory("TARS system health check", memory_type="short")
                
            # Test LLM connection (if using OpenAI)
            if self.llm_config.get("model", "").startswith("gpt"):
                client = get_openai_client()
                if not client:
                    logger.warning("OpenAI client not available - some features may be limited")
            
            logger.info("Health check completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def analyze_project(
        self,
        web_urls: Optional[List[str]] = None,
        repositories: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        data_files: Optional[List[str]] = None,
        github_repos: Optional[List[str]] = None,
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, WorkflowResult]:
        """
        Analyze a project comprehensively using TARS workflows.
        
        Args:
            web_urls: List of URLs to crawl and analyze
            repositories: List of Git repository URLs
            documents: List of document file paths
            data_files: List of data file paths (CSV, Excel, etc.)
            github_repos: List of GitHub repositories for issue/PR analysis
            analysis_options: Additional analysis configuration
            
        Returns:
            Dict containing workflow results
        """
        try:
            if self.system_status != "ready":
                logger.error("System not ready - please initialize first")
                return {"error": "System not initialized"}
            
            logger.info("Starting comprehensive project analysis")
            self.performance_metrics["total_queries"] += 1
            
            # Execute full pipeline
            results = await self.session.execute_full_pipeline(
                web_urls=web_urls,
                repositories=repositories,
                documents=documents,
                data_files=data_files,
                github_repos=github_repos,
                analysis_config=analysis_options
            )
            
            # Update metrics
            if "error" not in results:
                self.performance_metrics["successful_operations"] += 1
            else:
                self.performance_metrics["failed_operations"] += 1
            
            # Display results if verbose
            if self.verbose and "error" not in results:
                self._display_analysis_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in project analysis: {e}")
            self.performance_metrics["failed_operations"] += 1
            return {"error": str(e)}
    
    async def start_interactive_mode(self) -> None:
        """Start interactive conversation mode."""
        try:
            if self.system_status != "ready":
                await self.initialize()
            
            if self.system_status == "ready":
                await self.session.start_interactive_session()
            else:
                print("❌ Unable to start interactive mode - system initialization failed")
                
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            if self.verbose:
                display_error(f"Interactive mode error: {str(e)}")
    
    async def process_query(self, query: str) -> str:
        """
        Process a single query.
        
        Args:
            query: User query to process
            
        Returns:
            Response string
        """
        try:
            if self.system_status != "ready":
                return "System not initialized - please run initialize() first"
            
            self.performance_metrics["total_queries"] += 1
            response = await self.session.process_single_query(query)
            
            if response and "error" not in response.lower()[:50]:
                self.performance_metrics["successful_operations"] += 1
            else:
                self.performance_metrics["failed_operations"] += 1
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            self.performance_metrics["failed_operations"] += 1
            return f"Error processing query: {str(e)}"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            uptime = (datetime.now() - self.start_time).total_seconds()
            self.performance_metrics["total_uptime"] = uptime
            
            status = {
                "system_status": self.system_status,
                "uptime_seconds": uptime,
                "project_id": self.project_id,
                "user_id": self.user_id,
                "performance_metrics": self.performance_metrics,
                "configuration": {
                    "memory_provider": self.memory_config.get("provider"),
                    "llm_model": self.llm_config.get("model"),
                    "verbose": self.verbose
                }
            }
            
            # Add session health if available
            if self.session:
                try:
                    session_health = self.session.get_system_health()
                    status["session_health"] = session_health.dict()
                except Exception as e:
                    status["session_health"] = {"error": str(e)}
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    def _display_analysis_results(self, results: Dict[str, WorkflowResult]) -> None:
        """Display analysis results in a formatted way."""
        try:
            print("\n" + "="*60)
            print("📊 TARS Analysis Results")
            print("="*60)
            
            for workflow_name, result in results.items():
                if isinstance(result, WorkflowResult):
                    status_emoji = "✅" if result.status == "success" else "❌"
                    print(f"\n{status_emoji} {workflow_name.title()} Workflow:")
                    print(f"   Status: {result.status}")
                    print(f"   Tasks Completed: {result.tasks_completed}")
                    print(f"   Tasks Failed: {result.tasks_failed}")
                    print(f"   Execution Time: {result.execution_time:.2f}s")
                    
                    if result.error_summary:
                        print(f"   Error: {result.error_summary}")
            
            print("\n" + "="*60)
            
        except Exception as e:
            logger.error(f"Error displaying results: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the TARS system gracefully."""
        try:
            logger.info("Shutting down TARS system...")
            
            # Clean up session
            if self.session:
                self.session.cleanup_session()
            
            # Save final metrics
            final_metrics = {
                "shutdown_time": datetime.now().isoformat(),
                "total_uptime": (datetime.now() - self.start_time).total_seconds(),
                "final_metrics": self.performance_metrics,
                "project_id": self.project_id
            }
            
            # Save to file
            import json
            metrics_path = f".tars/{self.project_id}/final_metrics.json"
            os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
            
            with open(metrics_path, 'w') as f:
                json.dump(final_metrics, f, indent=2)
            
            self.system_status = "shutdown"
            logger.info("TARS system shutdown complete")
            
            if self.verbose:
                print("\n👋 TARS system shutdown complete. Goodbye!")
                
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point for TARS v1."""
    print("""
████████╗ █████╗ ██████╗ ███████╗    ██╗   ██╗ ██╗
╚══██╔══╝██╔══██╗██╔══██╗██╔════╝    ██║   ██║███║
   ██║   ███████║██████╔╝███████╗    ██║   ██║╚██║
   ██║   ██╔══██║██╔══██╗╚════██║    ╚██╗ ██╔╝ ██║
   ██║   ██║  ██║██║  ██║███████║     ╚████╔╝  ██║
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝      ╚═══╝   ╚═╝

Tactical AI Resource System - Open Source Project Assistant
""")
    
    # Initialize TARS
    tars = TarsMain(verbose=True)
    
    # Initialize system
    if not await tars.initialize():
        print("❌ Failed to initialize TARS system")
        return
    
    # Start interactive mode
    try:
        await tars.start_interactive_mode()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    finally:
        await tars.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
