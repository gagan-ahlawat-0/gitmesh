"""
TARS v1 Workflows
================

Orchestrated workflows for resource acquisition, analysis, and conversation management.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from ai import Agent, Task
from ai.session import Session
from ai.process import Process

from .agents import (
    WebCrawlerAgent,
    CodebaseAnalyzerAgent,
    DocumentProcessorAgent,
    DataAnalyzerAgent,
    ControlPanelMonitorAgent,
    KnowledgeOrchestratorAgent,
    CodeComparisonAgent,
    DocumentationAnalyzerAgent,
    ProjectInsightsAgent,
    ReasoningAgent,
    ConversationOrchestratorAgent
)
from .models import AcquisitionStatus, AnalysisResult, WorkflowResult

logger = logging.getLogger(__name__)


class BaseWorkflow:
    """Base class for TARS workflows."""
    
    def __init__(self, session: Optional[Session] = None, memory_config: Optional[Dict[str, Any]] = None):
        self.session = session
        self.memory_config = memory_config or {
            "provider": "supabase",
            "use_embedding": True,
            "embedding_provider": "sentence_transformers"
        }
        self.results = {}
        self.errors = []
        self.start_time = None
        self.end_time = None
    
    def log_error(self, error: str, component: str = "workflow"):
        """Log an error with timestamp."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "error": error
        }
        self.errors.append(error_entry)
        logger.error(f"[{component}] {error}")
    
    def get_execution_time(self) -> float:
        """Get workflow execution time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class AcquisitionWorkflow(BaseWorkflow):
    """Resource Acquisition Workflow for parallel data gathering."""
    
    def __init__(self, session: Optional[Session] = None, **kwargs):
        super().__init__(session, kwargs.get("memory_config"))
        
        # Initialize agents
        self.web_crawler = WebCrawlerAgent(memory=True, **kwargs)
        self.codebase_analyzer = CodebaseAnalyzerAgent(memory=True, **kwargs)
        self.document_processor = DocumentProcessorAgent(memory=True, **kwargs)
        self.data_analyzer = DataAnalyzerAgent(memory=True, **kwargs)
        self.control_panel_monitor = ControlPanelMonitorAgent(memory=True, **kwargs)
        
        # Initialize knowledge orchestrator with handoffs
        self.knowledge_orchestrator = KnowledgeOrchestratorAgent(
            handoffs=[
                self.web_crawler,
                self.codebase_analyzer,
                self.document_processor,
                self.data_analyzer,
                self.control_panel_monitor
            ],
            memory=True,
            **kwargs
        )
    
    async def execute(self, acquisition_config: Dict[str, Any]) -> WorkflowResult:
        """Execute the resource acquisition workflow."""
        self.start_time = datetime.now()
        
        try:
            logger.info("Starting Resource Acquisition Workflow")
            
            # Create acquisition tasks
            tasks = []
            
            # Web acquisition task
            if acquisition_config.get("web_sources"):
                web_task = Task(
                    name="web_acquisition",
                    description="Fetch and process web resources",
                    agent=self.web_crawler,
                    async_execution=True,
                    context=[acquisition_config["web_sources"]]
                )
                tasks.append(web_task)
            
            # Code acquisition task
            if acquisition_config.get("code_repositories"):
                code_task = Task(
                    name="codebase_acquisition",
                    description="Analyze codebase across branches",
                    agent=self.codebase_analyzer,
                    async_execution=True,
                    context=[acquisition_config["code_repositories"]]
                )
                tasks.append(code_task)
            
            # Document acquisition task
            if acquisition_config.get("document_sources"):
                doc_task = Task(
                    name="document_acquisition",
                    description="Process documentation and files",
                    agent=self.document_processor,
                    async_execution=True,
                    context=[acquisition_config["document_sources"]]
                )
                tasks.append(doc_task)
            
            # Data acquisition task
            if acquisition_config.get("data_sources"):
                data_task = Task(
                    name="data_acquisition",
                    description="Analyze structured data files",
                    agent=self.data_analyzer,
                    async_execution=True,
                    context=[acquisition_config["data_sources"]]
                )
                tasks.append(data_task)
            
            # Control panel acquisition task
            if acquisition_config.get("control_panel_sources"):
                control_task = Task(
                    name="control_panel_acquisition",
                    description="Monitor control panel data",
                    agent=self.control_panel_monitor,
                    async_execution=True,
                    context=[acquisition_config["control_panel_sources"]]
                )
                tasks.append(control_task)
            
            # Knowledge integration task (depends on all others)
            integration_task = Task(
                name="knowledge_integration",
                description="Integrate all acquired knowledge",
                agent=self.knowledge_orchestrator,
                context=tasks  # Pass all acquisition tasks as context
            )
            tasks.append(integration_task)
            
            # Execute tasks using Process
            if self.session:
                process = Process(
                    agents=[
                        self.web_crawler,
                        self.codebase_analyzer,
                        self.document_processor,
                        self.data_analyzer,
                        self.control_panel_monitor,
                        self.knowledge_orchestrator
                    ],
                    tasks=tasks,
                    process_type="workflow",
                    memory=True,
                    memory_config=self.memory_config,
                    session=self.session
                )
            else:
                # Create a temporary session
                temp_session = Session(
                    session_id="acquisition_workflow",
                    memory_config=self.memory_config
                )
                process = Process(
                    agents=[
                        self.web_crawler,
                        self.codebase_analyzer,
                        self.document_processor,
                        self.data_analyzer,
                        self.control_panel_monitor,
                        self.knowledge_orchestrator
                    ],
                    tasks=tasks,
                    process_type="workflow",
                    memory=True,
                    memory_config=self.memory_config,
                    session=temp_session
                )
            
            # Execute the workflow
            results = await process.astart()
            
            # Process results
            self.results = {
                "workflow_type": "acquisition",
                "tasks_executed": len(tasks),
                "task_results": results,
                "integration_status": "completed"
            }
            
            self.end_time = datetime.now()
            
            return WorkflowResult(
                workflow_name="AcquisitionWorkflow",
                status="success",
                tasks_completed=len(tasks),
                tasks_failed=0,
                execution_time=self.get_execution_time(),
                results=[],  # Would contain AnalysisResult objects
                error_summary=None
            )
            
        except Exception as e:
            self.end_time = datetime.now()
            error_msg = f"Acquisition workflow failed: {str(e)}"
            self.log_error(error_msg)
            
            return WorkflowResult(
                workflow_name="AcquisitionWorkflow",
                status="failed",
                tasks_completed=0,
                tasks_failed=len(tasks) if 'tasks' in locals() else 0,
                execution_time=self.get_execution_time(),
                results=[],
                error_summary=error_msg
            )
    
    def create_acquisition_config(self, 
                                web_urls: Optional[List[str]] = None,
                                repositories: Optional[List[str]] = None,
                                documents: Optional[List[str]] = None,
                                data_files: Optional[List[str]] = None,
                                github_repos: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create acquisition configuration from inputs."""
        config = {}
        
        if web_urls:
            config["web_sources"] = {"urls": web_urls}
        
        if repositories:
            config["code_repositories"] = {"repos": repositories}
        
        if documents:
            config["document_sources"] = {"files": documents}
        
        if data_files:
            config["data_sources"] = {"files": data_files}
        
        if github_repos:
            config["control_panel_sources"] = {"repos": github_repos}
        
        return config


class AnalysisWorkflow(BaseWorkflow):
    """Analysis Workflow for intelligent analysis of acquired data."""
    
    def __init__(self, session: Optional[Session] = None, **kwargs):
        super().__init__(session, kwargs.get("memory_config"))
        
        # Initialize analysis agents
        self.code_comparison = CodeComparisonAgent(memory=True, **kwargs)
        self.documentation_analyzer = DocumentationAnalyzerAgent(memory=True, **kwargs)
        self.project_insights = ProjectInsightsAgent(memory=True, **kwargs)
        self.reasoning_agent = ReasoningAgent(memory=True, **kwargs)
    
    async def execute(self, analysis_config: Dict[str, Any]) -> WorkflowResult:
        """Execute the analysis workflow."""
        self.start_time = datetime.now()
        
        try:
            logger.info("Starting Analysis Workflow")
            
            tasks = []
            
            # Code comparison analysis
            if analysis_config.get("code_comparison_needed"):
                comparison_task = Task(
                    name="code_comparison_analysis",
                    description="Perform code comparison analysis",
                    agent=self.code_comparison,
                    task_type="decision",
                    condition={"detailed_comparison": ["continue"], "skip": ["exit"]},
                    context=[analysis_config.get("code_data", {})]
                )
                tasks.append(comparison_task)
            
            # Documentation analysis
            if analysis_config.get("documentation_analysis_needed"):
                doc_task = Task(
                    name="documentation_analysis",
                    description="Analyze documentation gaps and updates needed",
                    agent=self.documentation_analyzer,
                    context=[
                        analysis_config.get("knowledge_integration", {}),
                        analysis_config.get("code_comparison_analysis", {})
                    ]
                )
                tasks.append(doc_task)
            
            # Project insights analysis
            if analysis_config.get("project_insights_needed"):
                insights_task = Task(
                    name="project_insights_analysis",
                    description="Generate project insights and recommendations",
                    agent=self.project_insights,
                    context=[analysis_config.get("knowledge_integration", {})]
                )
                tasks.append(insights_task)
            
            # Strategic reasoning (always included)
            reasoning_task = Task(
                name="strategic_reasoning",
                description="Provide strategic insights and recommendations",
                agent=self.reasoning_agent,
                context=tasks  # Context from all previous analyses
            )
            tasks.append(reasoning_task)
            
            # Execute tasks
            if self.session:
                process = Process(
                    agents=[
                        self.code_comparison,
                        self.documentation_analyzer,
                        self.project_insights,
                        self.reasoning_agent
                    ],
                    tasks=tasks,
                    process_type="workflow",
                    memory=True,
                    memory_config=self.memory_config,
                    session=self.session
                )
            else:
                temp_session = Session(
                    session_id="analysis_workflow",
                    memory_config=self.memory_config
                )
                process = Process(
                    agents=[
                        self.code_comparison,
                        self.documentation_analyzer,
                        self.project_insights,
                        self.reasoning_agent
                    ],
                    tasks=tasks,
                    process_type="workflow",
                    memory=True,
                    memory_config=self.memory_config,
                    session=temp_session
                )
            
            # Execute the workflow
            results = await process.astart()
            
            # Process results
            self.results = {
                "workflow_type": "analysis",
                "tasks_executed": len(tasks),
                "task_results": results,
                "analysis_status": "completed"
            }
            
            self.end_time = datetime.now()
            
            return WorkflowResult(
                workflow_name="AnalysisWorkflow",
                status="success",
                tasks_completed=len(tasks),
                tasks_failed=0,
                execution_time=self.get_execution_time(),
                results=[],  # Would contain AnalysisResult objects
                error_summary=None
            )
            
        except Exception as e:
            self.end_time = datetime.now()
            error_msg = f"Analysis workflow failed: {str(e)}"
            self.log_error(error_msg)
            
            return WorkflowResult(
                workflow_name="AnalysisWorkflow",
                status="failed",
                tasks_completed=0,
                tasks_failed=len(tasks) if 'tasks' in locals() else 0,
                execution_time=self.get_execution_time(),
                results=[],
                error_summary=error_msg
            )


class ConversationWorkflow(BaseWorkflow):
    """Conversation Management Workflow for intelligent user interaction."""
    
    def __init__(self, session: Optional[Session] = None, **kwargs):
        super().__init__(session, kwargs.get("memory_config"))
        
        # Initialize all specialist agents for handoffs
        self.web_crawler = WebCrawlerAgent(memory=True, **kwargs)
        self.codebase_analyzer = CodebaseAnalyzerAgent(memory=True, **kwargs)
        self.document_processor = DocumentProcessorAgent(memory=True, **kwargs)
        self.data_analyzer = DataAnalyzerAgent(memory=True, **kwargs)
        self.control_panel_monitor = ControlPanelMonitorAgent(memory=True, **kwargs)
        self.code_comparison = CodeComparisonAgent(memory=True, **kwargs)
        self.documentation_analyzer = DocumentationAnalyzerAgent(memory=True, **kwargs)
        self.project_insights = ProjectInsightsAgent(memory=True, **kwargs)
        self.reasoning_agent = ReasoningAgent(memory=True, **kwargs)
        
        # Initialize conversation orchestrator with all agents as handoffs
        self.conversation_orchestrator = ConversationOrchestratorAgent(
            handoffs=[
                self.web_crawler,
                self.codebase_analyzer,
                self.document_processor,
                self.data_analyzer,
                self.control_panel_monitor,
                self.code_comparison,
                self.documentation_analyzer,
                self.project_insights,
                self.reasoning_agent
            ],
            memory=True,
            **kwargs
        )
        
        # Set up quality guardrail
        self.guardrail_fn = kwargs.get("guardrail", self._default_quality_guardrail)
    
    def _default_quality_guardrail(self, output) -> tuple[bool, Any]:
        """Default quality guardrail for conversation responses."""
        response = output.raw if hasattr(output, 'raw') else str(output)
        
        # Basic quality checks
        if len(response.strip()) < 10:
            return False, "Response too short"
        
        if "error" in response.lower() and len(response) < 50:
            return False, "Response appears to be an error message"
        
        # Check for helpful content
        helpful_indicators = ["recommend", "suggest", "analysis", "insight", "solution"]
        if not any(indicator in response.lower() for indicator in helpful_indicators):
            return False, "Response lacks helpful content"
        
        return True, output
    
    async def start_conversation(self) -> None:
        """Start interactive conversation loop."""
        logger.info("Starting TARS Conversation Interface")
        print("\n" + "="*60)
        print("TARS v1 - Tactical AI Resource System")
        print("="*60)
        print("I can help you analyze open source projects, repositories, and resources.")
        print("Type 'exit' or 'quit' to end the conversation.")
        print("Type 'help' for available commands.")
        print("="*60 + "\n")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\nTARS: Goodbye! Thank you for using TARS v1.")
                    break
                
                if user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                if not user_input:
                    print("TARS: Please provide a question or command.")
                    continue
                
                # Route and process the query
                response = await self.process_query(user_input)
                print(f"\nTARS: {response}")
                
            except KeyboardInterrupt:
                print("\n\nTARS: Conversation interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in conversation loop: {e}")
                print(f"\nTARS: I encountered an error: {str(e)}")
                print("Please try rephrasing your question.")
    
    async def process_query(self, query: str) -> str:
        """Process a user query with intelligent routing."""
        try:
            # Route the query
            routing_decision = self.conversation_orchestrator.route_query(query)
            
            # Get the recommended agent
            recommended_agent_name = routing_decision.get("recommended_agent")
            
            # Map agent names to actual agent instances
            agent_map = {
                "WebCrawler": self.web_crawler,
                "CodebaseAnalyzer": self.codebase_analyzer,
                "DocumentProcessor": self.document_processor,
                "DataAnalyzer": self.data_analyzer,
                "ControlPanelMonitor": self.control_panel_monitor,
                "CodeComparison": self.code_comparison,
                "DocumentationAnalyzer": self.documentation_analyzer,
                "ProjectInsights": self.project_insights,
                "ReasoningAgent": self.reasoning_agent
            }
            
            # Get the appropriate agent
            target_agent = agent_map.get(recommended_agent_name, self.reasoning_agent)
            
            # Create a task for the query
            query_task = Task(
                name="user_interaction",
                description=f"Handle user query: {query}",
                agent=target_agent,
                guardrail=self.guardrail_fn,
                max_retries=3
            )
            
            # Process with the selected agent
            response = await target_agent.achat(
                prompt=query,
                temperature=0.7,
                reasoning_steps=True if recommended_agent_name == "ReasoningAgent" else False
            )
            
            return response or "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error while processing your query: {str(e)}. Please try again."
    
    def _show_help(self) -> None:
        """Show help information."""
        help_text = """
Available Commands and Capabilities:

🌐 Web Analysis:
   - "Analyze website [URL]" - Crawl and analyze web content
   - "Search for [topic]" - Search and analyze web resources

💻 Code Analysis:
   - "Analyze repository [URL]" - Analyze Git repository
   - "Compare branches [repo] [branch1] [branch2]" - Compare code branches
   - "Review codebase [URL]" - Comprehensive code review

📄 Document Processing:
   - "Process document [file_path]" - Analyze documents (PDF, Word, etc.)
   - "Analyze documentation gaps" - Find documentation issues

📊 Data Analysis:
   - "Analyze data file [file_path]" - Process CSV, Excel files
   - "Generate insights from [data_source]" - Extract data insights

🔧 Project Management:
   - "Check project health [repo]" - Analyze GitHub issues/PRs
   - "Monitor repository [URL]" - Track project status

🧠 Strategic Analysis:
   - "Provide insights on [topic]" - Deep strategic analysis
   - "Compare [item1] vs [item2]" - Comparative analysis
   - "Recommend actions for [situation]" - Strategic recommendations

Examples:
   - "Analyze the React repository on GitHub"
   - "What are the main issues in facebook/react?"
   - "Compare the main and develop branches"
   - "Help me understand this project's documentation"

Commands:
   - 'help' - Show this help message
   - 'exit' or 'quit' - End the conversation
        """
        print(help_text)
    
    async def execute_autonomous(self, initial_query: str) -> WorkflowResult:
        """Execute autonomous workflow for a specific query."""
        self.start_time = datetime.now()
        
        try:
            # Create autonomous task
            autonomous_task = Task(
                name="autonomous_user_interaction",
                description=f"Autonomously handle query: {initial_query}",
                agent=self.conversation_orchestrator,
                guardrail=self.guardrail_fn,
                autonomous=True
            )
            
            # Execute using Process with autonomous workflow
            if self.session:
                process = Process(
                    agents=[self.conversation_orchestrator],
                    tasks=[autonomous_task],
                    process_type="autonomous_workflow",
                    memory=True,
                    memory_config=self.memory_config,
                    session=self.session
                )
            else:
                temp_session = Session(
                    session_id="autonomous_conversation",
                    memory_config=self.memory_config
                )
                process = Process(
                    agents=[self.conversation_orchestrator],
                    tasks=[autonomous_task],
                    process_type="autonomous_workflow",
                    memory=True,
                    memory_config=self.memory_config,
                    session=temp_session
                )
            
            # Execute
            results = await process.astart()
            
            self.end_time = datetime.now()
            
            return WorkflowResult(
                workflow_name="ConversationWorkflow",
                status="success",
                tasks_completed=1,
                tasks_failed=0,
                execution_time=self.get_execution_time(),
                results=[],
                error_summary=None
            )
            
        except Exception as e:
            self.end_time = datetime.now()
            error_msg = f"Autonomous conversation workflow failed: {str(e)}"
            self.log_error(error_msg)
            
            return WorkflowResult(
                workflow_name="ConversationWorkflow", 
                status="failed",
                tasks_completed=0,
                tasks_failed=1,
                execution_time=self.get_execution_time(),
                results=[],
                error_summary=error_msg
            )
