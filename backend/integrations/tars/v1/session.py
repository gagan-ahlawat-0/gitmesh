"""
TARS v1 Session Management
=========================

Enhanced session management with persistent state and multi-workflow coordination.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from ai.session import Session
from ai.knowledge import Knowledge
from ai.memory import Memory

from .workflows import AcquisitionWorkflow, AnalysisWorkflow, ConversationWorkflow
from .models import SystemHealth, WorkflowResult

logger = logging.getLogger(__name__)


class TarsSession(Session):
    """Enhanced session management for TARS v1 with workflow coordination."""
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        memory_config: Optional[Dict[str, Any]] = None,
        knowledge_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        # Enhanced memory configuration with GitMesh hybrid
        default_memory_config = {
            "provider": "supabase",  # Use Supabase + Qdrant hybrid
            "use_embedding": True,
            "embedding_provider": "sentence_transformers",  # Free embeddings
            "quality_scoring": True,
            "advanced_memory": True,
            "short_db": ".tars/short_term.db",
            "long_db": ".tars/long_term.db",
            "entity_db": ".tars/entity.db",
            "rag_db_path": ".tars/chroma_db"
        }
        
        if memory_config:
            default_memory_config.update(memory_config)
        
        # Enhanced knowledge configuration
        default_knowledge_config = {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "tars_knowledge",
                    "path": ".tars/knowledge"
                }
            }
        }
        
        if knowledge_config:
            default_knowledge_config.update(knowledge_config)
        
        # Initialize base session
        super().__init__(
            session_id=session_id,
            user_id=user_id,
            memory_config=default_memory_config,
            knowledge_config=default_knowledge_config,
            **kwargs
        )
        
        # TARS-specific attributes
        self.project_id = project_id or f"project_{uuid.uuid4().hex[:8]}"
        self.workflows = {}
        self.workflow_history = []
        self.system_health = None
        self.active_agents = {}
        
        # Performance tracking
        self.metrics = {
            "queries_processed": 0,
            "workflows_executed": 0,
            "successful_analyses": 0,
            "failed_operations": 0,
            "total_execution_time": 0.0
        }
    
    def create_acquisition_workflow(self, **kwargs) -> AcquisitionWorkflow:
        """Create a resource acquisition workflow."""
        workflow = AcquisitionWorkflow(session=self, **kwargs)
        self.workflows["acquisition"] = workflow
        return workflow
    
    def create_analysis_workflow(self, **kwargs) -> AnalysisWorkflow:
        """Create an analysis workflow."""
        workflow = AnalysisWorkflow(session=self, **kwargs)
        self.workflows["analysis"] = workflow
        return workflow
    
    def create_conversation_workflow(self, **kwargs) -> ConversationWorkflow:
        """Create a conversation workflow."""
        workflow = ConversationWorkflow(session=self, **kwargs)
        self.workflows["conversation"] = workflow
        return workflow
    
    async def execute_full_pipeline(
        self,
        web_urls: Optional[List[str]] = None,
        repositories: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        data_files: Optional[List[str]] = None,
        github_repos: Optional[List[str]] = None,
        analysis_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, WorkflowResult]:
        """Execute the full TARS pipeline: acquisition -> analysis."""
        try:
            logger.info("Starting TARS full pipeline execution")
            pipeline_results = {}
            
            # Phase 1: Resource Acquisition
            acquisition_workflow = self.create_acquisition_workflow()
            acquisition_config = acquisition_workflow.create_acquisition_config(
                web_urls=web_urls,
                repositories=repositories,
                documents=documents,
                data_files=data_files,
                github_repos=github_repos
            )
            
            acquisition_result = await acquisition_workflow.execute(acquisition_config)
            pipeline_results["acquisition"] = acquisition_result
            self.metrics["workflows_executed"] += 1
            
            if acquisition_result.status == "success":
                self.metrics["successful_analyses"] += 1
                
                # Phase 2: Analysis Workflow
                analysis_workflow = self.create_analysis_workflow()
                
                # Prepare analysis configuration
                default_analysis_config = {
                    "code_comparison_needed": bool(repositories),
                    "documentation_analysis_needed": bool(documents),
                    "project_insights_needed": bool(github_repos),
                    "knowledge_integration": acquisition_workflow.results
                }
                
                if analysis_config:
                    default_analysis_config.update(analysis_config)
                
                analysis_result = await analysis_workflow.execute(default_analysis_config)
                pipeline_results["analysis"] = analysis_result
                self.metrics["workflows_executed"] += 1
                
                if analysis_result.status == "success":
                    self.metrics["successful_analyses"] += 1
            else:
                self.metrics["failed_operations"] += 1
            
            # Update execution time metrics
            total_time = sum(r.execution_time for r in pipeline_results.values())
            self.metrics["total_execution_time"] += total_time
            
            # Store workflow history
            self.workflow_history.append({
                "timestamp": datetime.now().isoformat(),
                "pipeline_type": "full_pipeline",
                "results": pipeline_results,
                "execution_time": total_time
            })
            
            # Save session state
            self.save_pipeline_state(pipeline_results)
            
            return pipeline_results
            
        except Exception as e:
            logger.error(f"Error in full pipeline execution: {e}")
            self.metrics["failed_operations"] += 1
            return {"error": str(e)}
    
    async def start_interactive_session(self) -> None:
        """Start an interactive conversation session."""
        try:
            conversation_workflow = self.create_conversation_workflow()
            await conversation_workflow.start_conversation()
            
        except Exception as e:
            logger.error(f"Error in interactive session: {e}")
            print(f"TARS: Session error: {str(e)}")
    
    async def process_single_query(self, query: str) -> str:
        """Process a single query using the conversation workflow."""
        try:
            conversation_workflow = self.create_conversation_workflow()
            response = await conversation_workflow.process_query(query)
            self.metrics["queries_processed"] += 1
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            self.metrics["failed_operations"] += 1
            return f"Error processing query: {str(e)}"
    
    def save_pipeline_state(self, pipeline_results: Dict[str, WorkflowResult]) -> None:
        """Save pipeline results to session state."""
        try:
            pipeline_state = {
                "pipeline_results": {
                    name: {
                        "status": result.status,
                        "execution_time": result.execution_time,
                        "tasks_completed": result.tasks_completed,
                        "tasks_failed": result.tasks_failed
                    }
                    for name, result in pipeline_results.items()
                },
                "metrics": self.metrics,
                "timestamp": datetime.now().isoformat()
            }
            
            self.save_state(pipeline_state)
            logger.info("Pipeline state saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving pipeline state: {e}")
    
    def restore_pipeline_state(self) -> Dict[str, Any]:
        """Restore pipeline state from session."""
        try:
            state = self.restore_state()
            return state.get("pipeline_results", {})
        except Exception as e:
            logger.error(f"Error restoring pipeline state: {e}")
            return {}
    
    def get_system_health(self) -> SystemHealth:
        """Get current system health status."""
        try:
            # Calculate overall status
            error_rate = self.metrics["failed_operations"] / max(1, 
                self.metrics["queries_processed"] + self.metrics["workflows_executed"])
            
            if error_rate > 0.3:
                overall_status = "critical"
            elif error_rate > 0.1:
                overall_status = "warning"
            else:
                overall_status = "healthy"
            
            # Get agent statuses
            agent_statuses = {}
            for workflow_name, workflow in self.workflows.items():
                if hasattr(workflow, 'errors') and workflow.errors:
                    agent_statuses[workflow_name] = "error"
                else:
                    agent_statuses[workflow_name] = "healthy"
            
            # Memory usage (simplified)
            memory_usage = {
                "session_memory": len(self.get_state("chat_history", [])),
                "workflow_cache": len(self.workflows),
                "error_log": len(self.workflow_history)
            }
            
            # Performance metrics
            performance_metrics = {
                "avg_query_time": self.metrics["total_execution_time"] / max(1, self.metrics["queries_processed"]),
                "success_rate": (self.metrics["successful_analyses"] / max(1, self.metrics["workflows_executed"])) * 100,
                "total_operations": self.metrics["queries_processed"] + self.metrics["workflows_executed"]
            }
            
            self.system_health = SystemHealth(
                overall_status=overall_status,
                agent_statuses=agent_statuses,
                memory_usage=memory_usage,
                performance_metrics=performance_metrics,
                error_count=self.metrics["failed_operations"],
                warning_count=len([w for w in self.workflow_history if "error" in str(w)]),
                last_check=datetime.now()
            )
            
            return self.system_health
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return SystemHealth(
                overall_status="critical",
                agent_statuses={"system": f"health_check_error: {str(e)}"},
                memory_usage={},
                performance_metrics={},
                error_count=1,
                warning_count=0,
                last_check=datetime.now()
            )
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a comprehensive session summary."""
        try:
            health = self.get_system_health()
            
            summary = {
                "session_info": {
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "project_id": self.project_id,
                    "created": datetime.now().isoformat()  # Would be actual creation time
                },
                "metrics": self.metrics,
                "system_health": health.dict(),
                "workflows": {
                    "available": list(self.workflows.keys()),
                    "history_count": len(self.workflow_history)
                },
                "capabilities": {
                    "web_analysis": True,
                    "code_analysis": True,
                    "document_processing": True,
                    "data_analysis": True,
                    "project_monitoring": True,
                    "strategic_reasoning": True
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating session summary: {e}")
            return {"error": str(e)}
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.metrics = {
            "queries_processed": 0,
            "workflows_executed": 0,
            "successful_analyses": 0,
            "failed_operations": 0,
            "total_execution_time": 0.0
        }
        logger.info("Session metrics reset")
    
    def cleanup_session(self) -> None:
        """Clean up session resources."""
        try:
            # Clear workflow caches
            for workflow in self.workflows.values():
                if hasattr(workflow, 'cleanup'):
                    workflow.cleanup()
            
            self.workflows.clear()
            
            # Save final state
            final_state = {
                "session_ended": datetime.now().isoformat(),
                "final_metrics": self.metrics,
                "workflows_executed": len(self.workflow_history)
            }
            self.save_state(final_state)
            
            logger.info(f"Session {self.session_id} cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
    
    def __str__(self) -> str:
        return f"TarsSession(id='{self.session_id}', user='{self.user_id}', project='{self.project_id}')"
    
    def __repr__(self) -> str:
        return self.__str__()
