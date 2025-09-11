"""
TARS v1 - Tactical AI Resource System
====================================

A comprehensive multi-agent system for resource acquisition, analysis, and conversation management.
Uses only ai framework classes/functions and GitIngest for repositories.
Supports Supabase PostgreSQL for normal DB and Qdrant Cloud for vector DB.
"""

from .agents import (
    # Resource acquisition agents
    WebCrawlerAgent,
    CodebaseAnalyzerAgent,
    DocumentProcessorAgent,
    DataAnalyzerAgent,
    ControlPanelMonitorAgent,
    KnowledgeOrchestratorAgent,
    
    # Analysis/intelligence agents
    CodeComparisonAgent,
    DocumentationAnalyzerAgent,
    ProjectInsightsAgent,
    ReasoningAgent,
    
    # Orchestrator agent
    ConversationOrchestratorAgent
)

from .workflows import (
    AcquisitionWorkflow,
    AnalysisWorkflow,
    ConversationWorkflow
)

from .models import (
    ComparisonResult,
    ProjectStatus,
    AcquisitionStatus,
    AnalysisResult,
    WorkflowResult,
    SystemHealth
)

from .session import TarsSession
from .main import TarsMain

# Enhanced TARS Wrapper
from .tars_wrapper import (
    TARSWrapper,
    TARSInput,
    TARSResponse,
    TARSSession,
    create_tars,
    quick_chat
)

# Configuration
from .config import (
    create_config_template,
    save_config_template,
    load_config_template,
    expand_environment_variables,
    validate_config,
    generate_config_templates
)

__version__ = "1.0.0"
__all__ = [
    # Agents
    'WebCrawlerAgent',
    'CodebaseAnalyzerAgent',
    'DocumentProcessorAgent',
    'DataAnalyzerAgent',
    'ControlPanelMonitorAgent',
    'KnowledgeOrchestratorAgent',
    'CodeComparisonAgent',
    'DocumentationAnalyzerAgent',
    'ProjectInsightsAgent',
    'ReasoningAgent',
    'ConversationOrchestratorAgent',
    
    # Workflows
    'AcquisitionWorkflow',
    'AnalysisWorkflow',
    'ConversationWorkflow',
    
    # Models
    'ComparisonResult',
    'ProjectStatus',
    'AcquisitionStatus',
    'AnalysisResult',
    'WorkflowResult',
    'SystemHealth',
    
    # Core
    'TarsSession',
    'TarsMain',
    
    # Enhanced Wrapper
    'TARSWrapper',
    'TARSInput',
    'TARSResponse',
    'create_tars',
    'quick_chat',
    
    # Configuration
    'create_config_template',
    'save_config_template',
    'load_config_template',
    'expand_environment_variables',
    'validate_config',
    'generate_config_templates'
]
